from playwright.sync_api import sync_playwright, TimeoutError


def click_erlang_then_deploy():
    # 配置项（可根据实际调整）
    TARGET_URL_KEYWORD = "192.168.5.173"
    ERLANG_TEXT = "erlang服务"
    DEPLOY_TEXT = "部署"
    TIMEOUT = 30000  # 全局超时时间（毫秒）

    with sync_playwright() as p:
        # 1. 连接调试模式的Chrome
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]

        # 2. 筛选目标页面
        target_page = None
        for page in context.pages:
            if not page.url.startswith("chrome://") and TARGET_URL_KEYWORD in page.url:
                target_page = page
                break
        if not target_page:
            print(f"❌ 错误：未找到包含「{TARGET_URL_KEYWORD}」的页面！")
            browser.close()
            return
        print(f"✅ 已定位到目标页面：{target_page.url}")

        try:
            # 等待页面完全加载（适配SPA动态渲染）
            target_page.wait_for_load_state("networkidle")
            target_page.wait_for_timeout(1000)

            # 3. 定位所有“erlang服务”元素（基础定位器）
            erlang_btns = target_page.locator(f":text-is('{ERLANG_TEXT}')")

            # 4. 统计当前erlang服务元素数量
            btn_count = erlang_btns.count()
            print(f"📌 当前页面「{ERLANG_TEXT}」元素数量：{btn_count}")

            # 5. 分情况处理erlang服务点击
            if btn_count >= 2:
                # 场景1：已有≥2个，直接点击第二个（索引1）
                second_erlang_btn = erlang_btns.nth(1)
                second_erlang_btn.wait_for(state="visible", timeout=TIMEOUT)
                if second_erlang_btn.is_enabled():
                    second_erlang_btn.click()
                    print(f"✅ 页面已有{btn_count}个「{ERLANG_TEXT}」，已点击第二个")
                else:
                    raise Exception(f"第二个「{ERLANG_TEXT}」按钮不可点击（禁用状态）")

            elif btn_count == 1:
                # 场景2：只有1个，先点第一个，等待新增第二个后再点
                first_erlang_btn = erlang_btns.nth(0)
                first_erlang_btn.wait_for(state="visible", timeout=TIMEOUT)

                if first_erlang_btn.is_enabled():
                    first_erlang_btn.click()
                    print(
                        f"✅ 页面只有1个「{ERLANG_TEXT}」，已点击第一个（等待新增第二个）"
                    )
                else:
                    raise Exception(f"唯一的「{ERLANG_TEXT}」按钮不可点击（禁用状态）")

                # 等待第二个erlang服务元素出现（循环检查，最多等TIMEOUT毫秒）
                wait_start = target_page.evaluate("Date.now()")
                while target_page.evaluate("Date.now()") - wait_start < TIMEOUT:
                    new_count = erlang_btns.count()
                    if new_count >= 2:
                        # 新增成功，点击第二个
                        second_erlang_btn = erlang_btns.nth(1)
                        second_erlang_btn.wait_for(state="visible", timeout=TIMEOUT)
                        second_erlang_btn.click()
                        print(
                            f"✅ 新增「{ERLANG_TEXT}」成功，已点击第二个（当前总数：{new_count}）"
                        )
                        break
                    target_page.wait_for_timeout(500)  # 每500ms检查一次
                else:
                    raise TimeoutError(
                        f"等待{TIMEOUT/1000}秒后，仍未新增第二个「{ERLANG_TEXT}」元素"
                    )

            else:
                # 无erlang服务元素，直接报错
                raise Exception(f"❌ 页面未找到「{ERLANG_TEXT}」元素")

            # 6. 定位并点击“部署”按钮（处理多元素，选第一个可交互的）
            deploy_btn = target_page.locator(f":text-is('{DEPLOY_TEXT}')").first
            deploy_btn.wait_for(state="visible", timeout=TIMEOUT)
            if deploy_btn.is_enabled():
                deploy_btn.click()
                print(f"✅ 已点击「{DEPLOY_TEXT}」按钮")
            else:
                raise Exception(f"「{DEPLOY_TEXT}」按钮不可点击（禁用状态）")

        except TimeoutError as e:
            print(f"❌ 超时错误：{str(e)}")
            target_page.screenshot(path="timeout_screenshot.png")
        except Exception as e:
            print(f"❌ 操作失败：{str(e)}")
            target_page.screenshot(path="error_screenshot.png")
        finally:
            # 仅断开连接，不关闭Chrome
            browser.close()


if __name__ == "__main__":
    click_erlang_then_deploy()
