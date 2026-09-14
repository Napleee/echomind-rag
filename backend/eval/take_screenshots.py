"""用 Playwright 驱动系统 Edge 截取产品截图（README 素材）。

免浏览器下载: channel="msedge" 直接用 Windows 自带 Edge。
用法（项目根目录）: python backend/eval/take_screenshots.py [--base http://localhost:5173]
产物: docs/screenshot-chat.png / docs/screenshot-documents.png
"""
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent.parent / "docs"
DOCS.mkdir(exist_ok=True)

# 截图用问题: 命中知识库（samples/EchoMind-技术方案.md），答案带多来源引用
QUESTION = "EchoMind 的检索方案是什么？为什么同时要向量和关键词两路？"


def main() -> None:
    base = "http://localhost:8080"
    if len(sys.argv) > 1 and sys.argv[1] == "--base" and len(sys.argv) > 2:
        base = sys.argv[2]

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "/", wait_until="domcontentloaded")
        # 等 React 挂载出输入框（字体等资源不阻塞截图）
        page.wait_for_selector("textarea", timeout=20000)

        # --- 聊天页: 真实提问一次，等待流式回答与来源渲染完 ---
        page.fill("textarea", QUESTION)
        page.keyboard.press("Enter")
        # 等「停止」按钮出现（流式开始）后消失（流式结束），上限 90s
        try:
            page.wait_for_selector("text=停止", timeout=10000)
        except Exception:
            pass
        try:
            page.wait_for_function(
                """() => {
                    const btns = [...document.querySelectorAll('button')];
                    return !btns.some(b => b.textContent?.includes('停止'));
                }""",
                timeout=90000,
            )
        except Exception:
            pass  # 超时也照截，保底拿到过程画面
        page.wait_for_timeout(1000)  # 等来源卡片收尾
        page.screenshot(path=str(DOCS / "screenshot-chat.png"))
        print(f"saved {DOCS / 'screenshot-chat.png'}")

        # --- 文档页 ---
        page.goto(base + "/documents", wait_until="domcontentloaded")
        page.wait_for_selector("text=文档", timeout=10000)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(DOCS / "screenshot-documents.png"))
        print(f"saved {DOCS / 'screenshot-documents.png'}")

        browser.close()


if __name__ == "__main__":
    main()
