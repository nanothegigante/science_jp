from pathlib import Path
from playwright.sync_api import sync_playwright

INDEX_URL = "https://warp.ndl.go.jp/web/20190601103017/http://www.mext.go.jp/b_menu/hakusho/html/hpaa195801/index.html"

Path("warp_dump").mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(INDEX_URL, wait_until="domcontentloaded")

    # 画面に同意が出る場合に備えて、よくあるボタン候補を広めに探す
    candidates = [
        "必要最小限"
    ]
    for txt in candidates:
        loc = page.get_by_text(txt, exact=False)
        if loc.count() > 0:
            loc.first.click()
            page.wait_for_timeout(1500)
            break

    # 同意後のHTMLを保存
    html = page.content()
    Path("warp_dump/index_after_consent.html").write_text(html, encoding="utf-8")

    print("saved: warp_dump/index_after_consent.html")
    print("current url:", page.url)

    browser.close()