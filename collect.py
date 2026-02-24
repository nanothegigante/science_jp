# import requests
# from bs4 import BeautifulSoup

# # 今とりあえず昭和33年分の白書を集める
# index_url = "https://warp.ndl.go.jp/web/20190601103017/http://www.mext.go.jp/b_menu/hakusho/html/hpaa195801/index.html"

# res = requests.get(index_url)
# res.encoding = res.apparent_encoding

# soup = BeautifulSoup(res.text, "html.parser")

# links = []

# for a in soup.find_all("a", href=True):
#     href = a["href"]
#     links.append(href)

# print(len(links))
# for l in links[:20]:
#     print(l)
"""
import time
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ★ここをあなたの実際のディレクトリURLに置き換え
BASE_URL = "https://warp.ndl.go.jp/web/20190601103017/http://www.mext.go.jp/b_menu/hakusho/html/hpaa195801/"

START = 3
END = 268

OUT_DIR = Path("data/hpaa195801")
OUT_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; academic-text-mining/1.0; +https://example.org)"
})

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # スクリプト/スタイル等を除去
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # まずはページ全体をテキスト化（後で本文抽出に改良可能）
    text = soup.get_text("\n", strip=True)

    # ありがちなノイズを軽く整形
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"

ok, ng = 0, 0

for i in range(START, END + 1):
    filename = f"hpaa195801_2_{i:03d}.html"
    url = urljoin(BASE_URL, filename)

    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()

        # 文字化け回避：apparent_encoding を優先
        r.encoding = r.apparent_encoding
        text = html_to_text(r.text)

        out_path = OUT_DIR / f"{i:03d}.txt"
        out_path.write_text(text, encoding="utf-8")

        ok += 1
        print(f"[OK] {i:03d} -> {out_path}")
        time.sleep(0.6)  # サーバーに優しく（重要）
    except Exception as e:
        ng += 1
        print(f"[NG] {i:03d} {url} :: {e}")
        time.sleep(1.0)

print(f"Done. OK={ok}, NG={ng}")

--- second ---
import time
import re
import csv
import hashlib
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://warp.ndl.go.jp/web/20190601103017/http://www.mext.go.jp/b_menu/hakusho/html/hpaa195801/index.html"
BASE_URL = INDEX_URL.rsplit("/", 1)[0] + "/"  # .../hpaa195801/

START = 3
END = 268

OUT_ROOT = Path("data/hpaa195801")
HTML_DIR = OUT_ROOT / "html"
TXT_DIR = OUT_ROOT / "txt"
HTML_DIR.mkdir(parents=True, exist_ok=True)
TXT_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST = OUT_ROOT / "manifest.csv"

session = requests.Session()
# WARPがUAで弾くことがあるので、ブラウザっぽいUAに寄せます
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.8",
    "Referer": INDEX_URL,
})

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # 不要タグ削除
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # まずは全体テキスト化（後で「本文のみ抽出」に改善可能）
    text = soup.get_text("\n", strip=True)

    # ありがちなノイズを軽く整形
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"

# 既にmanifestがあれば読み込み、再実行時にスキップできるようにする
done = set()
if MANIFEST.exists():
    with MANIFEST.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "OK":
                done.add(row["page"])

need_header = not MANIFEST.exists()
with MANIFEST.open("a", encoding="utf-8", newline="") as f:
    fieldnames = ["page", "url", "status", "http_status", "bytes", "sha256", "note"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if need_header:
        writer.writeheader()

    ok = ng = 0
    for i in range(START, END + 1):
        page = f"{i:03d}"
        if page in done:
            print(f"[SKIP] {page} (already OK)")
            continue

        filename = f"hpaa195801_2_{page}.html"
        url = urljoin(BASE_URL, filename)

        html_path = HTML_DIR / f"{page}.html"
        txt_path = TXT_DIR / f"{page}.txt"

        try:
            r = session.get(url, timeout=30)
            http_status = r.status_code

            if http_status != 200:
                writer.writerow({
                    "page": page, "url": url, "status": "NG",
                    "http_status": http_status, "bytes": 0, "sha256": "",
                    "note": "non-200"
                })
                print(f"[NG] {page} HTTP {http_status}")
                ng += 1
                time.sleep(1.2)
                continue

            raw = r.content
            html_path.write_bytes(raw)

            # 文字化け対策：requestsに推定させる（Shift_JIS等に対応しやすい）
            r.encoding = r.apparent_encoding
            text = html_to_text(r.text)

            # ページ境界マーカー（最小限）
            text = f"### PAGE {page} ###\n\n" + text
            txt_path.write_text(text, encoding="utf-8")

            writer.writerow({
                "page": page, "url": url, "status": "OK",
                "http_status": http_status, "bytes": len(raw),
                "sha256": sha256_bytes(raw), "note": ""
            })
            print(f"[OK] {page}")
            ok += 1
            time.sleep(0.8)  # サーバーに優しく
        except Exception as e:
            writer.writerow({
                "page": page, "url": url, "status": "NG",
                "http_status": "", "bytes": 0, "sha256": "",
                "note": repr(e)[:200]
            })
            print(f"[ERR] {page} {e}")
            ng += 1
            time.sleep(1.5)

print(f"Done. OK={ok}, NG={ng}")
"""

import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://warp.ndl.go.jp/web/20190601103017/http://www.mext.go.jp/b_menu/hakusho/html/hpaa195801/index.html"

OUT_DIR = Path("data/hpaa195801")
OUT_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Referer": INDEX_URL,
})

# -----------------------
# STEP 1: index取得
# -----------------------

res = session.get(INDEX_URL)
res.encoding = res.apparent_encoding

soup = BeautifulSoup(res.text, "lxml")

# -----------------------
# STEP 2: リンク抽出
# -----------------------

page_links = []

for a in soup.find_all("a", href=True):
    href = a["href"]

    if "hpaa195801_2_" in href and href.endswith(".html"):
        page_links.append(urljoin(INDEX_URL, href))

print("found:", len(page_links))

# -----------------------
# STEP 3: 各ページ取得
# -----------------------

for i, url in enumerate(page_links):

    print("getting:", url)

    r = session.get(url)
    r.encoding = r.apparent_encoding

    text = BeautifulSoup(r.text, "lxml").get_text("\n", strip=True)

    out = OUT_DIR / f"{i:03d}.txt"
    out.write_text(text, encoding="utf-8")

    time.sleep(1)