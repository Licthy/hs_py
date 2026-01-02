import pyautogui
import time


def click_image(target_image_path):
    """
    精准匹配图片并点击（无需OpenCV）
    :param target_image_path: 目标图片的路径
    :return: 找到并点击返回True，未找到返回False
    """
    try:
        # 移除confidence参数，使用默认精准匹配
        image_position = pyautogui.locateOnScreen(target_image_path, grayscale=False)

        if not image_position:
            return False

        # 点击图片中心
        center_x, center_y = pyautogui.center(image_position)
        pyautogui.moveTo(center_x, center_y, duration=0.1)
        pyautogui.click(center_x, center_y)
        print(f"成功点击！位置：({center_x}, {center_y})")
        return True

    except Exception as e:
        print(f"单次操作异常：{str(e)}")
        return False


# ------------------- 循环执行逻辑 -------------------
if __name__ == "__main__":
    # 配置参数
    target_image = "tiug.png"  # 替换为你的目标图片路径
    total_run_time = 20  # 总循环时长（秒）
    interval = 0.5  # 每次操作间隔（秒）

    # 记录循环开始时间
    start_time = time.time()
    print(f"开始循环执行（总时长{total_run_time}秒，间隔{interval}秒）...")

    # 循环执行，直到达到总时长
    while (time.time() - start_time) < total_run_time:
        click_image(target_image)
        time.sleep(interval)

    print(f"循环结束！已执行{total_run_time}秒，停止操作。")
