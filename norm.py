import re
from pathlib import Path

IN_DIR = Path("txt_clean")
OUT_DIR = Path("txt_clean_norm")
OUT_DIR.mkdir(exist_ok=True)

# 文末として扱う記号（ここで終わっていれば文が閉じている可能性が高い）
SENT_END = "。！？）」』】］〉》）"

# 見出し/区切りっぽい行（この行は連結しない）
HEADLIKE = re.compile(
    r"^(###\s*SOURCE:|##\s*PAGE\b|第\s*[0-9０-９一二三四五六七八九十百]+\s*[章節項]|"
    r"[0-9０-９]+[．\.\-−－][0-9０-９]+|"
    r"[0-9０-９]+[．\.\)]|"
    r"目次|参考文献|索引|付録)"
)

def is_headlike(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    # 短くて句点がない行は見出しの可能性が高い（保守的に保持）
    if len(line) <= 30 and ("。" not in line) and ("、" not in line):
        # ただし数字だけ等のゴミもあるので、少しだけ条件追加
        if re.fullmatch(r"[0-9０-９\s]+", line):
            return False
        return True
    return bool(HEADLIKE.search(line))

def normalize_breaks(text: str) -> str:
    out = []
    buf = ""

    for raw in text.splitlines():
        line = raw.strip()

        # 空行：段落境界として保持
        if not line:
            if buf:
                out.append(buf)
                buf = ""
            out.append("")
            continue

        # マーカーや見出しは単独行として確定
        if is_headlike(line):
            if buf:
                out.append(buf)
                buf = ""
            out.append(line)
            continue

        # ここから本文候補
        if not buf:
            buf = line
            continue

        # 直前が文末記号で終わるなら、文が終わった可能性が高い → 改行確定
        if buf[-1] in SENT_END:
            out.append(buf)
            buf = line
        else:
            # 文途中改行っぽい → 連結（スペースは入れない。日本語は基本不要）
            buf += line

    if buf:
        out.append(buf)

    # 連続空行を最大2つに圧縮
    joined = "\n".join(out)
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip() + "\n"

for p in sorted(IN_DIR.glob("*.clean.txt")):
    t = p.read_text(encoding="utf-8", errors="ignore")
    norm = normalize_breaks(t)
    out = OUT_DIR / p.name.replace(".clean.txt", ".norm.txt")
    out.write_text(norm, encoding="utf-8")
    print("wrote", out)