import tkinter as tk
import pyautogui
import time
import threading
import json5
import os

# 读取配置文件
print("当前工作目录:", os.getcwd())

with open("./res/hs_tap_cfg.json", "r") as f:
    hs_tap_cfg = json5.load(f)


# 找到图片并点击
def click_res(res):
    label2.config(text=res)
    for i in range(hs_tap_cfg["one_pic_max_times"]):
        time.sleep(hs_tap_cfg["one_pic_cd"])
        png_center = pyautogui.locateCenterOnScreen(res, confidence=0.90)
        if png_center is not None:
            pyautogui.click(png_center)
            return

    label4.config(text="多次没有找到:{}".format(res))
    # print("多次没有找到:", res)


# 循环找图
def for_res():
    for element in hs_tap_cfg["png_res"]:
        click_res(element)
        pyautogui.moveTo(x=0, y=100)
        time.sleep(hs_tap_cfg["diff_pic_cd"])


# 主方法
def main_run():
    # 巴拉巴拉干事情
    while True:
        for_res()


####################################
# 创建窗体
####################################
root = tk.Tk()
root.title("二师兄")
# 置顶
root.attributes("-topmost", True)

# 调整窗口的宽度和高度
window_width = 500
window_height = 500
frame_padx = 20
frame_pady = 1
root.geometry(f"{window_width}x{window_height}")

####################################
# 当前运行中
####################################
label1 = tk.Label(root, text="当前查找图片：")
label2 = tk.Label(root, text="")
label3 = tk.Label(root, text="错误信息：")
label4 = tk.Label(root, text="")
label5 = tk.Label(root, text="")

label1.grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
label2.grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)
label3.grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
label4.grid(row=1, column=1, padx=10, pady=5, sticky=tk.W)
label5.grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)

####################################
# 添加提交按钮
####################################
####################################
# 提交按钮执行方法
####################################
submit_button_click_num = 0


def on_submit():
    global submit_button_click_num
    submit_button_click_num = submit_button_click_num + 1
    label5.config(text="你点了 {} 下按钮".format(submit_button_click_num))


submit_button = tk.Button(root, text="点了没反应", command=on_submit)
submit_button.grid(row=999, column=999)
####################################
#
####################################
# 启动一个线程执行长时间运行的任务
thread = threading.Thread(target=main_run)
thread.start()

# mainloop
root.mainloop()
