from playwright.sync_api import sync_playwright

# 替换为你的目标网页URL
TARGET_URL = "https://你的网页地址.com"


def click_erlang_then_deploy():
    with sync_playwright() as p:
        # 1. 启动浏览器（headless=False 显示浏览器窗口，方便调试）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # 2. 打开目标网页（等待页面加载完成）
        page.goto(TARGET_URL, wait_until="load")  # load：等待页面所有资源加载完成

        try:
            # 3. 定位并点击“erlang服务”按钮（核心：文本定位，自动等待按钮可交互）
            # text="erlang服务"：匹配按钮文本；exact=True：精准匹配（避免模糊匹配到相似文本）
            erlang_btn = page.locator("text=erlang服务", exact=True)
            # 等待按钮可见且可点击，超时时间30秒（可根据网页速度调整）
            erlang_btn.click(timeout=30000)
            print("已点击「erlang服务」按钮")

            # 4. 等待“部署”按钮出现并点击（自动等待按钮从隐藏→可见→可交互）
            deploy_btn = page.locator("text=部署", exact=True)
            # 显式等待按钮可见（可选，Playwright的click本身也会等，加这个更稳妥）
            deploy_btn.wait_for(state="visible", timeout=30000)
            deploy_btn.click()
            print("已点击「部署」按钮")

        except Exception as e:
            print(f"操作失败：{e}")
        finally:
            # 5. 可选：停留5秒查看结果，再关闭浏览器
            page.wait_for_timeout(5000)
            browser.close()


if __name__ == "__main__":
    click_erlang_then_deploy()
