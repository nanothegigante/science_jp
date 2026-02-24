# """
# Sudachi tokenisation for year-level whitepaper texts

# Input:
#   ./txt_clean/[year].clean.txt   (or .norm.txt if you made them)
# Output:
#   ./tokens/[year].tokens.txt     (space-separated tokens, one line)

# Two modes:
#   (A) No stopwords (default)  -> best for quick Word2Vec experiments
#   (B) With light stopwording  -> optional, conservative (keeps content words)

# Install:
#   pip install sudachipy sudachidict_core

# Run:
#   python tokenize_sudachi.py

# Notes:
# - This script does NOT require you to normalise line breaks first.
# - It tokenises the entire document as one stream (fine for Word2Vec).
# """

# from __future__ import annotations

# import re
# from pathlib import Path
# from typing import Iterable, List, Set, Optional

# from sudachipy import dictionary


# # -------------------------
# # Config
# # -------------------------
# IN_DIR = Path("txt_clean")     # contains 2017.clean.txt ... etc
# OUT_DIR = Path("tokens")
# OUT_DIR.mkdir(parents=True, exist_ok=True)

# # Choose Sudachi split mode:
# #   A: coarse, B: medium, C: fine-grained
# SPLIT_MODE = "C"

# # Stopword options
# USE_STOPWORDS = False          # set True to enable conservative filtering

# # If USE_STOPWORDS=True, these POS categories will be removed (conservative).
# # We KEEP nouns/verbs/adjectives by default.
# DROP_POS_PREFIXES = {
#     "助詞", "助動詞", "記号", "補助記号", "連体詞", "接続詞", "感動詞"
# }

# # Optional: drop very short tokens (e.g., single-character symbols)
# MIN_TOKEN_LEN = 1              # set 2 if you want to drop 1-char tokens

# # Optional: normalise ASCII spaces
# NORMALISE_WHITESPACE = True


# # -------------------------
# # Helpers
# # -------------------------
# def get_split_mode(tokenizer):
#     if SPLIT_MODE.upper() == "A":
#         return tokenizer.SplitMode.A
#     if SPLIT_MODE.upper() == "B":
#         return tokenizer.SplitMode.B
#     return tokenizer.SplitMode.C


# def is_noise_token(token: str) -> bool:
#     if len(token) < MIN_TOKEN_LEN:
#         return True
#     # Drop pure whitespace
#     if not token.strip():
#         return True
#     return False


# def should_drop_by_pos(pos: List[str]) -> bool:
#     """
#     Sudachi POS example: ['名詞', '普通名詞', '一般', '*', '*', '*']
#     We drop if pos[0] starts with any of DROP_POS_PREFIXES
#     """
#     if not pos:
#         return False
#     return pos[0] in DROP_POS_PREFIXES


# def normalise_text(t: str) -> str:
#     if not NORMALISE_WHITESPACE:
#         return t
#     # Replace various whitespace with a single space (keep newlines; Sudachi can handle either)
#     t = re.sub(r"[ \t]+", " ", t)
#     return t


# def tokenise(text: str, tokenizer) -> List[str]:
#     mode = get_split_mode(tokenizer)
#     ms = tokenizer.tokenize(text, mode)

#     out: List[str] = []
#     for m in ms:
#         s = m.surface()
#         if is_noise_token(s):
#             continue

#         if USE_STOPWORDS:
#             pos = m.part_of_speech()
#             if should_drop_by_pos(list(pos)):
#                 continue

#         out.append(s)
#     return out


# def year_from_filename(p: Path) -> str:
#     # Expect: 2017.clean.txt  or 2017.norm.txt
#     m = re.search(r"(20\d{2})", p.name)
#     return m.group(1) if m else p.stem.split(".")[0]


# # -------------------------
# # Main
# # -------------------------
# def main() -> None:
#     tokenizer = dictionary.Dictionary().create()

#     files = sorted(IN_DIR.glob("*.txt"))
#     if not files:
#         raise SystemExit(f"No .txt files found in {IN_DIR.resolve()}")

#     print("Input files:", len(files))
#     print("Split mode:", SPLIT_MODE, "Stopwords:", USE_STOPWORDS)

#     for p in files:
#         year = year_from_filename(p)
#         text = p.read_text(encoding="utf-8", errors="ignore")
#         text = normalise_text(text)

#         tokens = tokenise(text, tokenizer)

#         out_path = OUT_DIR / f"{year}.tokens.txt"
#         out_path.write_text(" ".join(tokens), encoding="utf-8")

#         print(f"wrote {out_path}  tokens={len(tokens)}")

#     print("Done.")


# if __name__ == "__main__":
#     main()

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, List, Optional

from sudachipy import dictionary


# -------------------------
# Config
# -------------------------
IN_DIR = Path("txt_clean")   # 2017.clean.txt ... 2025.clean.txt
OUT_DIR = Path("tokens")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SPLIT_MODE = "C"  # A/B/C

# SudachiPy input limit is ~49149 bytes; keep a safe margin
MAX_BYTES = 45000

# Optional stopwording (off by default)
USE_STOPWORDS = False
DROP_POS_PREFIXES = {"助詞", "助動詞", "記号", "補助記号", "連体詞", "接続詞", "感動詞"}

MIN_TOKEN_LEN = 1


# -------------------------
# Helpers
# -------------------------
def get_split_mode(tokenizer):
    if SPLIT_MODE.upper() == "A":
        return tokenizer.SplitMode.A
    if SPLIT_MODE.upper() == "B":
        return tokenizer.SplitMode.B
    return tokenizer.SplitMode.C


def should_drop_by_pos(pos: List[str]) -> bool:
    return bool(pos) and (pos[0] in DROP_POS_PREFIXES)


def year_from_filename(p: Path) -> str:
    m = re.search(r"(20\d{2})", p.name)
    return m.group(1) if m else p.stem.split(".")[0]


def iter_chunks_by_paragraph(text: str, max_bytes: int = MAX_BYTES) -> Iterator[str]:
    """
    Yield chunks <= max_bytes (UTF-8), trying to keep paragraph boundaries.
    Falls back to line boundaries if a single paragraph is too large.
    """
    paragraphs = re.split(r"\n{2,}", text)
    buf: List[str] = []
    buf_bytes = 0

    def flush():
        nonlocal buf, buf_bytes
        if buf:
            yield "\n\n".join(buf)
            buf = []
            buf_bytes = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        b = len(para.encode("utf-8"))

        # If one paragraph is too large, split further by lines
        if b > max_bytes:
            # flush current buffer first
            yield from flush()

            lines = para.splitlines()
            line_buf: List[str] = []
            line_bytes = 0

            def flush_lines():
                nonlocal line_buf, line_bytes
                if line_buf:
                    yield "\n".join(line_buf)
                    line_buf = []
                    line_bytes = 0

            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                lb = len(ln.encode("utf-8"))
                if lb > max_bytes:
                    # Worst case: a single line too long -> split by characters (rare)
                    yield from flush_lines()
                    tmp = ""
                    for ch in ln:
                        if len((tmp + ch).encode("utf-8")) > max_bytes:
                            yield tmp
                            tmp = ch
                        else:
                            tmp += ch
                    if tmp:
                        yield tmp
                    continue

                if line_bytes + lb + 1 <= max_bytes:
                    line_buf.append(ln)
                    line_bytes += lb + 1
                else:
                    yield from flush_lines()
                    line_buf.append(ln)
                    line_bytes = lb + 1

            yield from flush_lines()
            continue

        # Normal paragraph accumulation
        if buf_bytes + b + 2 <= max_bytes:
            buf.append(para)
            buf_bytes += b + 2
        else:
            yield from flush()
            buf.append(para)
            buf_bytes = b + 2

    yield from flush()


def tokenise_to_file(text: str, out_path: Path, tokenizer) -> int:
    """
    Tokenise a large text by chunks, streaming output to file.
    Returns token count.
    """
    mode = get_split_mode(tokenizer)
    token_count = 0

    with out_path.open("w", encoding="utf-8") as out:
        first = True
        for chunk in iter_chunks_by_paragraph(text, MAX_BYTES):
            ms = tokenizer.tokenize(chunk, mode)
            for m in ms:
                s = m.surface()
                if not s or len(s) < MIN_TOKEN_LEN:
                    continue

                if USE_STOPWORDS:
                    pos = list(m.part_of_speech())
                    if should_drop_by_pos(pos):
                        continue

                if first:
                    out.write(s)
                    first = False
                else:
                    out.write(" " + s)
                token_count += 1

    return token_count


# -------------------------
# Main
# -------------------------
def main() -> None:
    tokenizer = dictionary.Dictionary().create()

    files = sorted(IN_DIR.glob("*.txt"))
    if not files:
        raise SystemExit(f"No .txt files found in {IN_DIR.resolve()}")

    print("Input files:", len(files))
    print("Split mode:", SPLIT_MODE, "Stopwords:", USE_STOPWORDS, "MAX_BYTES:", MAX_BYTES)

    for p in files:
        year = year_from_filename(p)
        text = p.read_text(encoding="utf-8", errors="ignore")

        out_path = OUT_DIR / f"{year}.tokens.txt"
        n = tokenise_to_file(text, out_path, tokenizer)
        print(f"wrote {out_path} tokens={n}")

    print("Done.")


if __name__ == "__main__":
    main()