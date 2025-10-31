import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import threading
import time
import logging
import pyautogui



from pystray import Icon, MenuItem as item
from PIL import Image, ImageDraw
from pynput import keyboard  # 替换为pynput库

# 配置日志
logging.basicConfig(
    filename='text_converter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 全局变量
is_hidden = False
listener_thread = None  # 快捷键监听线程
heartbeat_flag = False  # 线程心跳标记
last_run_time = 0 #最后的执行时间


def convert_text():
    """文本转换逻辑（保持不变）"""
    try:
        global last_run_time
        now_time = int(time.time() * 1000)
        if  now_time-last_run_time>200:
            last_run_time=now_time
            pyautogui.hotkey('ctrl', 'c')
            clipboard_text = pyperclip.paste()
            if not clipboard_text:
                logging.info("转换失败：剪贴板为空")
                return
            
            processed_text = clipboard_text.strip('"').strip()
            parts = [part.strip() for part in processed_text.split(',') if part.strip()]
            
            if not parts:
                logging.info(f"转换失败：无效内容 - {clipboard_text}")
                return
            
            converted_parts = [f'{{"{part}",{part}}}' for part in parts]
            result = ','.join(converted_parts)
            
            pyperclip.copy(result)
            pyautogui.hotkey('ctrl', 'v')
            logging.info(f"转换成功：{clipboard_text} → {result}")
        
    except Exception as e:
        error_msg = f"转换失败：{str(e)}"
        logging.error(error_msg, exc_info=True)


def on_hotkey_press():
    """快捷键触发的函数（供pynput调用）"""
    global heartbeat_flag
    heartbeat_flag = True  # 触发时更新心跳标记
    convert_text()


def pynput_listener():
    """使用pynput监听Ctrl+F1快捷键"""
    global heartbeat_flag
    # 定义快捷键：Ctrl+F1
    hotkey = keyboard.GlobalHotKeys({
        '<ctrl>+<f1>': on_hotkey_press
    })
    
    while True:  # 循环确保监听失效后重启
        try:
            logging.info("pynput快捷键监听启动")
            heartbeat_flag = True  # 初始心跳标记
            with hotkey:
                hotkey.join()  # 阻塞监听（pynput的监听方式）
        except Exception as e:
            logging.error(f"pynput监听异常，5秒后重启：{str(e)}", exc_info=True)
            time.sleep(5)
        finally:
            hotkey.stop()  # 停止当前监听


def heartbeat_checker():
    """心跳检测线程：定期检查监听线程是否存活，失效则重启"""
    global heartbeat_flag, listener_thread
    while True:
        time.sleep(60)  # 每60秒检查一次
        # 检查条件：监听线程未运行 或 60秒内无心跳（未触发过快捷键且未响应）
        if (listener_thread is None or not listener_thread.is_alive()) or not heartbeat_flag:
            logging.warning("监听线程无响应，尝试重启...")
            # 强制终止旧线程（如果存在）
            if listener_thread and listener_thread.is_alive():
                # pynput的线程无法直接终止，通过重新创建线程覆盖
                pass
            # 启动新的监听线程
            start_listener_thread()
        # 重置心跳标记（等待下一次检查）
        heartbeat_flag = False


def start_listener_thread():
    """启动pynput监听线程"""
    global listener_thread
    listener_thread = threading.Thread(target=pynput_listener, daemon=True)
    listener_thread.start()
    logging.info("已启动pynput快捷键监听线程")


def create_tray_icon(window):
    """系统托盘（保持不变）"""
    def create_image():
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        draw.text((15, 10), "T", font_size=40, fill='black')
        return image

    def on_tray_click(icon, item):
        global is_hidden
        if not is_hidden:
            return
        is_hidden = False
        window.deiconify()
        icon.stop()

    def on_exit(icon, item):
        icon.stop()
        window.destroy()
        logging.info("程序正常退出")
        exit()

    menu = (item('退出', on_exit),)
    icon = Icon("TextConverter", create_image(), "文本转换工具", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


def minimize_to_tray(window):
    global is_hidden
    is_hidden = True
    window.withdraw()
    create_tray_icon(window)


def main_window():
    window = tk.Tk()
    window.title("ConvertText")
    window.geometry("400x200")
    window.resizable(False, False)

    def on_minimize(event):
        if window.state() == 'iconic':
            minimize_to_tray(window)
    window.bind("<Unmap>", on_minimize)

    ttk.Label(
        window,
        text="按下 Ctrl+F1 执行文本转换\n\n格式要求： AAA,BBB,CCC（可带引号或空格）\n",
        justify="left",
        font=("微软雅黑", 10)
    ).pack(padx=20, pady=30)

    frame = ttk.Frame(window)
    frame.pack(pady=10)
    ttk.Button(frame, text="退出", command=window.destroy).pack(side="right", padx=10)
    ttk.Button(frame, text="转换（Ctrl+F1）", command=convert_text).pack(side="right")

    # 启动核心线程：监听线程 + 心跳检测线程
    start_listener_thread()
    threading.Thread(target=heartbeat_checker, daemon=True).start()
    logging.info("心跳检测线程启动")

    def on_close():
        window.destroy()
        logging.info("窗口关闭，程序退出")
    window.protocol("WM_DELETE_WINDOW", on_close)

    window.mainloop()


if __name__ == "__main__":
    logging.info("程序启动")
    main_window()