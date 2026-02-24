# import requests
# from pathlib import Path

# INDEX_URL = "https://warp.ndl.go.jp/web/20190601103017/http://www.mext.go.jp/b_menu/hakusho/html/hpaa195801/index.html"

# session = requests.Session()
# session.headers.update({
#     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
#     "Accept-Language": "ja,en;q=0.8",
#     "Referer": INDEX_URL,
# })

# r = session.get(INDEX_URL, timeout=30)
# print("status:", r.status_code)
# print("final url:", r.url)
# print("content-type:", r.headers.get("content-type"))

# r.encoding = r.apparent_encoding
# html = r.text

# Path("index_saved.html").write_text(html, encoding="utf-8")
# print("saved index_saved.html, length:", len(html))
# print("head:\n", html[:500])

from pathlib import Path
from bs4 import BeautifulSoup
import re

html = Path("warp_dump/index_after_consent.html").read_text(encoding="utf-8")
soup = BeautifulSoup(html, "lxml")

title = soup.title.get_text(strip=True) if soup.title else "(no title)"
print("TITLE:", title)

# hpaa195801_2_***.html が含まれるか（aタグ・文字列どちらでも）
hits = re.findall(r"hpaa195801_2_\d{3}\.html", html)
print("pattern hits:", len(hits))
print("sample:", hits[:5])

# aタグのhrefを数える（参考）
hrefs = [a["href"] for a in soup.find_all("a", href=True)]
print("total <a href>:", len(hrefs))
print("sample href:", hrefs[:10])