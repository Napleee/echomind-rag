"""三主题截图验证：切换器各点一遍，截聊天页空状态（看板娘/背景/挂件/花瓣全在）。

用法（项目根目录）: python backend/eval/take_theme_shots.py [--base http://localhost:5173]
产物: docs/theme-{sakura,paper,miku}.png
"""
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent.parent / "docs"
DOCS.mkdir(exist_ok=True)


def main() -> None:
    base = sys.argv[2] if len(sys.argv) > 1 and sys.argv[1] == "--base" else "http://localhost:5173"

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "/", wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=20000)

        for theme in ("sakura", "paper", "miku"):
            page.click(f"button:has-text('{ {'sakura': '樱花', 'paper': '素笺', 'miku': '未来'}[theme] }')")
            page.wait_for_timeout(2500)  # 等过渡动画 + 背景图加载
            page.screenshot(path=str(DOCS / f"theme-{theme}.png"))
            print(f"saved docs/theme-{theme}.png")

        browser.close()


if __name__ == "__main__":
    main()
