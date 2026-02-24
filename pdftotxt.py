# import re
# from pathlib import Path
# import fitz  # PyMuPDF

# PDF_ROOT = Path("pdf")          # 例: pdf/2017/*.pdf, pdf/2018/*.pdf ...
# OUT_RAW = Path("txt_raw")       # 年ごとの生テキスト（まだ図表多め）
# OUT_RAW.mkdir(parents=True, exist_ok=True)

# def blocks_to_lines(blocks, page_width):
#     """
#     blocks: page.get_text("blocks") の返り値
#     ざっくり2カラムに対応：左→右の順に読む
#     """
#     # blocks: (x0, y0, x1, y1, "text", block_no, block_type)
#     text_blocks = [b for b in blocks if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()]

#     # まずYで段落順に並べたいが、2カラムがあるのでXも考慮
#     # カラム境界を雑に推定（ページ中央で分ける）
#     mid = page_width / 2

#     left = []
#     right = []
#     for b in text_blocks:
#         x0, y0, x1, y1, t = b[0], b[1], b[2], b[3], b[4]
#         # ブロックの中心xで振り分け
#         cx = (x0 + x1) / 2
#         if cx <= mid:
#             left.append((y0, x0, t))
#         else:
#             right.append((y0, x0, t))

#     left.sort(key=lambda z: (z[0], z[1]))
#     right.sort(key=lambda z: (z[0], z[1]))

#     # 左カラム→右カラムの順で連結（典型的な2カラム読み順）
#     ordered = left + right

#     # ブロックテキストを行として返す（後でクリーニング）
#     lines = []
#     for _, __, t in ordered:
#         # ブロック内改行は残す
#         for line in t.splitlines():
#             line = line.strip()
#             if line:
#                 lines.append(line)
#     return lines

# def extract_pdf(pdf_path: Path) -> str:
#     doc = fitz.open(pdf_path)
#     out_lines = []
#     for page in doc:
#         blocks = page.get_text("blocks")
#         lines = blocks_to_lines(blocks, page.rect.width)
#         out_lines.extend(lines)
#         out_lines.append("")  # ページ区切り（空行）
#     return "\n".join(out_lines).strip() + "\n"

# def year_from_path(p: Path) -> str:
#     # pdf/2017/xxx.pdf なら "2017"
#     for part in p.parts:
#         if re.fullmatch(r"\d{4}", part):
#             return part
#     # ファイル名に年がある場合
#     m = re.search(r"(20\d{2})", p.name)
#     return m.group(1) if m else "unknown"

# # 年ごとに全PDFを結合してテキスト化
# by_year = {}
# for pdf in sorted(PDF_ROOT.rglob("*.pdf")):
#     y = year_from_path(pdf)
#     by_year.setdefault(y, []).append(pdf)

# for y, pdfs in sorted(by_year.items()):
#     texts = []
#     for pdf in pdfs:
#         print("extracting", y, pdf)
#         texts.append(f"### SOURCE: {pdf.name} ###\n")
#         texts.append(extract_pdf(pdf))
#         texts.append("\n")
#     out = OUT_RAW / f"{y}.txt"
#     out.write_text("".join(texts), encoding="utf-8")
#     print("wrote", out)

"""
Science/Innovation Whitepaper PDF -> year-level corpus text extractor (JP)
- Handles 1-column and 2-column layouts (auto-detect per page)
- Extracts text blocks with coordinates using PyMuPDF (fitz)
- Orders blocks to reduce 2-column jumbling
- Writes:
  - txt_raw/YYYY.txt   (includes SOURCE markers per input PDF)
  - txt_clean/YYYY.clean.txt (optional light noise reduction, esp. captions/table-ish lines)

Assumptions:
- PDFs are text-selectable (no OCR needed)
- PDFs are organised under pdf/<YEAR>/*.pdf  (recommended)
  If not, year is inferred from folder name or filename (20XX).

Run:
  pip install pymupdf
  python extract_whitepaper.py
"""

import re
import time
from pathlib import Path
from typing import List, Tuple, Dict

import fitz  # PyMuPDF


# -------------------------
# Config
# -------------------------
PDF_ROOT = Path("./corpus/pdf")          # e.g., pdf/2017/*.pdf ... pdf/2025/*.pdf
OUT_RAW = Path("txt_raw")       # year-level raw text
OUT_CLEAN = Path("txt_clean")   # year-level cleaned text
SLEEP_BETWEEN_PDFS = 0.0        # adjust if you want to be gentle on IO


# -------------------------
# Helpers: year inference
# -------------------------
def year_from_path(p: Path) -> str:
    """
    Infer year (20XX) from path parts or filename.
    """
    for part in p.parts:
        m = re.match(r"(20\d{2})", part)
        if m:
            return m.group(1)
        
    m = re.search(r"(20\d{2})", p.name)
    if m:
        return m.group(1)
    
    return "unknown"


# -------------------------
# Layout handling
# -------------------------
def detect_columns(text_blocks: List[Tuple], page_width: float) -> int:
    """
    Decide if a page is 1-column or 2-column using x-center distribution.
    - If there are enough blocks on both sides of the midline -> 2 columns
    - Otherwise -> 1 column

    text_blocks: list of blocks from page.get_text("blocks")
                Each block typically: (x0, y0, x1, y1, "text", block_no, block_type)
    """
    centers = []
    for b in text_blocks:
        if len(b) >= 5 and isinstance(b[4], str) and b[4].strip():
            x0, _, x1, _, _ = b[0], b[1], b[2], b[3], b[4]
            centers.append((x0 + x1) / 2)

    if not centers:
        return 1

    mid = page_width / 2
    left = sum(c < mid for c in centers)
    right = sum(c >= mid for c in centers)

    # Heuristic threshold: if both sides have "enough" blocks, treat as 2-col
    # You can tune these numbers depending on your PDFs.
    if left > 3 and right > 3:
        return 2
    return 1


def blocks_to_lines(blocks: List[Tuple], page_width: float) -> List[str]:
    """
    Convert blocks to ordered lines.
    - If 1-column: order by (y0, x0)
    - If 2-column: split by midline, order left then right, each by (y0, x0)
    """
    text_blocks = [
        b for b in blocks
        if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()
    ]

    col_count = detect_columns(text_blocks, page_width)

    if col_count == 1:
        ordered = sorted(text_blocks, key=lambda b: (b[1], b[0]))  # (y0, x0)
    else:
        mid = page_width / 2
        left, right = [], []
        for b in text_blocks:
            cx = (b[0] + b[2]) / 2
            (left if cx < mid else right).append(b)

        left.sort(key=lambda b: (b[1], b[0]))
        right.sort(key=lambda b: (b[1], b[0]))
        ordered = left + right

    lines: List[str] = []
    for b in ordered:
        t = b[4]
        for line in t.splitlines():
            line = line.strip()
            if line:
                lines.append(line)

    return lines


def extract_pdf_to_text(pdf_path: Path) -> str:
    """
    Extract a single PDF into text with page breaks.
    """
    doc = fitz.open(pdf_path)
    out_lines: List[str] = []
    for page_idx, page in enumerate(doc, start=1):
        blocks = page.get_text("blocks")
        lines = blocks_to_lines(blocks, page.rect.width)

        out_lines.append(f"## PAGE {page_idx} ##")
        out_lines.extend(lines)
        out_lines.append("")  # page separator
    return "\n".join(out_lines).strip() + "\n"


# -------------------------
# Optional cleaning (light)
# -------------------------
CAPTION_PAT = re.compile(r"^(図|表|出典|注|資料|（注）|※|出所)")

def is_tableish(line: str) -> bool:
    """
    Heuristic to drop table/caption-ish short noisy lines.
    Conservative: removes likely non-sentential fragments; keep longer text.
    Tune thresholds as needed.
    """
    if len(line) < 3:
        return True
    if CAPTION_PAT.search(line):
        return True

    # digit ratio
    digits = sum(ch.isdigit() for ch in line)
    if digits / max(1, len(line)) > 0.35 and len(line) < 80:
        return True

    # symbol ratio
    symbols = sum(ch in "•·●○▲△■□◆◇※-–—….,:;()[]{}％%／/|=+*" for ch in line)
    if symbols / max(1, len(line)) > 0.30 and len(line) < 80:
        return True

    return False


def clean_text(text: str) -> str:
    """
    Light cleanup:
    - remove table-ish lines
    - compress excessive spaces / blank lines
    - keep SOURCE/PAGE markers (useful for debugging)
    """
    cleaned_lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()

        # Keep markers as-is
        if line.startswith("### SOURCE:") or line.startswith("## PAGE"):
            cleaned_lines.append(line)
            continue

        if not line:
            cleaned_lines.append("")
            continue

        if is_tableish(line):
            continue

        # collapse multiple spaces/tabs
        line = re.sub(r"[ \t]{2,}", " ", line)
        cleaned_lines.append(line)

    out = "\n".join(cleaned_lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


# -------------------------
# Main: process all PDFs and write year corpora
# -------------------------
def main() -> None:
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    OUT_CLEAN.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(PDF_ROOT.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found under: {PDF_ROOT.resolve()}")

    # group by year
    by_year: Dict[str, List[Path]] = {}
    for pdf in pdfs:
        y = year_from_path(pdf)
        by_year.setdefault(y, []).append(pdf)

    for y, year_pdfs in sorted(by_year.items()):
        print(f"\n=== YEAR {y} ({len(year_pdfs)} PDFs) ===")
        parts: List[str] = []

        for pdf in sorted(year_pdfs):
            print("extracting:", pdf)
            parts.append(f"### SOURCE: {pdf.name} ###\n")
            parts.append(extract_pdf_to_text(pdf))
            parts.append("\n")
            if SLEEP_BETWEEN_PDFS:
                time.sleep(SLEEP_BETWEEN_PDFS)

        raw_text = "".join(parts)
        raw_out = OUT_RAW / f"{y}.txt"
        raw_out.write_text(raw_text, encoding="utf-8")
        print("wrote:", raw_out)

        cleaned = clean_text(raw_text)
        clean_out = OUT_CLEAN / f"{y}.clean.txt"
        clean_out.write_text(cleaned, encoding="utf-8")
        print("wrote:", clean_out)

    print("\nDone.")


if __name__ == "__main__":
    main()