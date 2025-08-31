import win32process
import tkinter as tk
import pyautogui
import psutil
import time
import threading
from tkinter import font

# 全局变量
learn_f_bool = True


def sleep(num):
    while num > 0:
        label_sleep.config(text=f"等待时间:{num}")
        time.sleep(1)
        num = num - 1
        label_sleep.config(text=f"等待时间:{num}")


############################################################################################
#      方法
############################################################################################
def find_and_click(res):
    png_center = pyautogui.locateCenterOnScreen(res, confidence=0.9)
    if png_center is not None:
        pyautogui.click(png_center)
        return True
    else:
        return False


####################################
# 清空显示信息
####################################
def clean_label():
    label_browser.config(text="")
    label_curr_state.config(text="")
    label_title.config(text="")
    label1.config(text="")
    label2.config(text="")
    label3.config(text="")
    label_error.config(text="")


####################################
# 提交按钮执行方法
####################################
def on_submit():
    global learn_f_bool
    learn_f_bool = False
    label_curr_state.config(text="当前运行中：你点了提交按钮")


####################################
# 逻辑方法
####################################
# 创建一个新的进程去执行下面的方法
def learn_main_thread():
    threading.Thread(target=learn_main, daemon=True).start()


def learn_main():
    while learn_f_bool:
        try:
            learn_f_start()
        except:
            label_curr_state.config(text="try-发生了错误")
            sleep(10)


def learn_f_start():
    all_windows = pyautogui.getAllWindows()
    for window in all_windows:
        clean_label()
        # # 这个电脑上的EDGE浏览器有问题，暂时不用EDGE
        # print(window.title)
        # # if "Edge" in window.title:
        # #     label_browser.config(text="Edge")
        # #     learn_f1(window)
        # #     sleep(2)
        # if "Chrome" in window.title:
        #     label_browser.config(text="Chrome")
        #     learn_f1(window)
        # if "Internet Explorer" in window.title:
        #     label_browser.config(text="Internet Explorer")
        #     learn_f1(window)
        # if "360极速浏览器" in window.title:
        #     label_browser.config(text="360极速浏览器")
        #     learn_f1(window)
        # if "世界之窗浏览器" in window.title:
        #     label_browser.config(text="世界之窗浏览器")
        #     learn_f1(window)
        hwnd = window._hWnd
        _, process_id = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(process_id)
        process_name = process.name()
        if process_name == 'msedge.exe' \
                or process_name == '360ChromeX.exe' \
                or process_name == 'QQBrowser.exe' \
                or process_name == 'iexplore.exe' \
                or process_name == 'firefox.exe' \
                or process_name == 'chrome.exe':
            label_browser.config(text=process_name)
            learn_f1(window)

    clean_label()
    label_curr_state.config(text="5秒后开始下一次")
    sleep(5)


def open_window(window):
    time.sleep(1)
    # # 激活
    # if not window.isActive:
    #     label_curr_state.config(text="激活并且最大化")
    #     window.restore()
    #     time.sleep(1)
    #     window.activate()
    if window.isMaximized:
        if not window.isActive:
            window.activate()
    else:
        window.maximize()
    time.sleep(2)


def learn_f1(window):
    label_title.config(text=window.title)
    learn_from_title(window)
    sleep(2)


def learn_from_title(window):
    if ("正在播放" in window.title) or ("课程学习" in window.title):
        # 最大化激活窗口
        open_window(window)
        label_curr_state.config(text="找到播放页面")
        png_center = pyautogui.locateCenterOnScreen("./res/web_learn/play_over.png", confidence=0.9,grayscale=True)
        if png_center is not None:
            label1.config(text="播放已经结束，关闭当前页面")
            pyautogui.hotkey('ctrl', 'w')
        else:
            find_and_click("./res/web_learn/bofh2.png")
            label1.config(text="播放中...")
    elif "福建省建设从业人员网络教育培训平台" in window.title:
        # 最大化激活窗口
        open_window(window)
        # 福建的 点了播放之后，还要在新页面点击播放
        label_curr_state.config(text="福建省--继续教育--选课界面")
        pyautogui.press('f5')
        label1.config(text="等待10秒，页面刷新")
        sleep(10)
        label1.config(text="点击学习进度，把没有学习的排上面")
        xtxijbdu = pyautogui.locateCenterOnScreen("./res/web_learn/xtxijbdu.png", confidence=0.9)
        if xtxijbdu is not None:
            pyautogui.click(x=xtxijbdu.x + 30, y=xtxijbdu.y)
            label1.config(text="等待,然后点击播放按钮")
            sleep(2)
            pyautogui.click(x=xtxijbdu.x, y=xtxijbdu.y + 85)
        else:
            label_error.config(text="出现流程错误，找不到【学习进度】")
    elif "平潭综合实验区建筑行业协会人员继续教育网络培训平台" in window.title:
        # 最大化激活窗口
        open_window(window)
        label_curr_state.config(text="平潭--继续教育--选课界面")
        pyautogui.press('f5')
        label1.config(text="等待，页面刷新，然后点击播放")
        sleep(10)
        if not find_and_click("./res/web_learn/play.png"):
            label1.config(text="没找到播放，是不是已经放完了")
    elif "厦门市建设从业人员继续教育培训平台" in window.title:
        # 最大化激活窗口
        open_window(window)
        # 厦门的播放点了之后，要手动切换到新的页面，这个不会自动跳到新页面去
        # 和平潭一样
        learn_xiamen(window)
    elif "个人主页" in window.title:
        learn_fuzhou(window)
    else:
        label_curr_state.config(text="没找到")


def learn_fuzhou(window):
    # 最大化激活窗口
    open_window(window)
    # 福建的 点了播放之后，还要在新页面点击播放
    label_curr_state.config(text="福州-89--继续教育--选课界面")
    pyautogui.press('f5')
    label1.config(text="等待10秒，页面刷新")
    sleep(10)
    find_and_click("./res/web_learn/89-jixujnyu.png")
    sleep(2)
    find_and_click("./res/web_learn/89-quxtxi.png")
    sleep(2)
    point1 = pyautogui.locateCenterOnScreen("./res/web_learn/89-wwkdui.png", confidence=0.9)
    sleep(2)
    if point1 is not None:
        label2.config(text="1111111111111111")
        pyautogui.click(x=point1.x + 168, y=point1.y)
        sleep(2)
        label1.config(text="等待,然后点击播放按钮")
        find_and_click("./res/web_learn/bofh2.png")
        sleep(2)
    else:
        point2 = pyautogui.locateCenterOnScreen("./res/web_learn/89-bdffhc.png", confidence=0.9)
        sleep(2)
        if point2 is not None:
            pyautogui.click(x=point2.x + 168, y=point2.y)
            label1.config(text="等待,然后点击播放按钮")
            sleep(2)
            find_and_click("./res/web_learn/bofh2.png")
        else:
            label3.config(text="福州平台出现未知错误")


def learn_xiamen(window):
    label_curr_state.config(text="厦门--继续教育--选课界面")
    pyautogui.press('f5')
    label1.config(text="等待，页面刷新，然后点击播放")
    sleep(10)
    if not find_and_click("./res/web_learn/play.png"):
        label1.config(text="没找到播放，是不是已经放完了")
    else:
        # 等5秒加载页面
        label1.config(text="已经点了播放，等待页面刷新")
        sleep(5)
        # 找目录，确定是否切换页面
        if pyautogui.locateCenterOnScreen("./res/web_learn/mulu.png", confidence=0.8) is not None:
            label2.config(text="找到mulu.png，在播放页面，判断是否需要点击播放按钮")
        else:
            label2.config(text="没有找到mulu.png,切换页面")
            pyautogui.hotkey('ctrl', 'tab')

        sleep(1)
        if find_and_click("./res/web_learn/bofh2.png"):
            label3.config(text="找到播放按钮，点击播放按钮")
        else:
            label3.config(text="没有找到播放按钮，应该是正在播放中")
        sleep(1)


####################################
# 关闭界面时调用，同时终止所有线程
####################################
def on_closing():
    root.destroy()


############################################################################################
#      主程序
############################################################################################
root = tk.Tk()
root.title("自动学习-2024-4-27")
# 置顶
root.attributes('-topmost', True)

# 调整窗口的宽度和高度
window_width = 300
window_height = 420
pad_x = 20
pad_y = 10
root.geometry(f"{window_width}x{window_height}")

title_font = font.Font(family="Helvetica", size=10, weight="bold")
label_browser = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y, font=title_font)
label_browser.pack(fill="x")
label_curr_state = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y, font=title_font)
label_curr_state.pack(fill="x")
label_sleep = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label_sleep.pack(fill="x")
label1 = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label1.pack(fill="x")
label2 = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label2.pack(fill="x")
label3 = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label3.pack(fill="x")
label_error = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label_error.pack(fill="x")
label_title_k = tk.Label(root, text="下面是测试信息", anchor="w", padx=pad_x, pady=pad_y)
label_title_k.pack(fill="x")
label_title = tk.Label(root, text="", anchor="w", padx=pad_x, pady=pad_y)
label_title.pack(fill="x")

button = tk.Button(root, text="开始", command=learn_main_thread)
button.pack()

# 逻辑处理
root.protocol("WM_DELETE_WINDOW", on_closing)  # 捕捉窗口关闭事件

root.mainloop()

# pyinstaller --onedir --noconsole --noconfirm hs_tk.py
