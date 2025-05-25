import tkinter as tk
import threading
import ddddocr
import pyautogui
import time
import os
import logging

# 配置日志记录器
logging.basicConfig(
    filename="error.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
num_flag = 0


def test_fun1():
    global num_flag
    num_flag = num_flag + 1
    label2.config(text="执行中:{}".format(num_flag))
    label1.config(text="第一步，判断是否需要输入验证码")
    time.sleep(1)
    # label1.config(text="路径:{}".format(image_path))
    png_center = pyautogui.locateCenterOnScreen(
        "./res/qtdk.png", confidence=0.9, grayscale=True
    )
    if png_center is not None:
        label1.config(text="识别到需要输入验证码")
        # 截图
        screenshot = pyautogui.screenshot(region=(891, 514, 100, 40))
        screenshot.save("./res/1.png")
        # 识别
        ocr = ddddocr.DdddOcr()
        with open("./res/1.png", "rb") as f:
            image = f.read()
        res = ocr.classification(image)
        time.sleep(1)
        label1.config(text="验证码是:{}".format(res))
        # 填写
        pyautogui.click(png_center.x, png_center.y - 70)
        time.sleep(1)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(1)
        pyautogui.press("del")
        time.sleep(1)
        pyautogui.typewrite(res)
        time.sleep(1)
        # 点击确定
        pyautogui.click(png_center)
        time.sleep(1)
        num_flag = num_flag + 1000000

    label1.config(text="第二步，判断是否需要点击播放按钮")
    # 点击播放
    png_center2 = pyautogui.locateCenterOnScreen(
        "./res/bofh.png", confidence=0.9, grayscale=True
    )
    if png_center2 is not None:
        pyautogui.click(png_center2)


def test_fun():
    while True:
        try:
            # 这里是你的代码
            test_fun1()
            time.sleep(1)
        except Exception as e:
            # 如果发生错误，记录错误消息到日志文件
            logging.error("An error occurred: %s", str(e))


# 创建一个新的进程去执行下面的方法
def learn_main_thread():
    button.config(state="disabled")
    threading.Thread(target=test_fun, daemon=True).start()


root = tk.Tk()
root.title("自动学习")
# 置顶
root.attributes("-topmost", True)

# 调整窗口的宽度和高度
window_width = 300
window_height = 150
pad_x = 20
pad_y = 10
root.geometry(f"{window_width}x{window_height}")
label1 = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label1.pack()
label2 = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label2.pack()
button = tk.Button(root, text="开始", command=learn_main_thread)
button.pack()
root.mainloop()
# pyinstaller --onefile --noconsole hs_ocr.py
