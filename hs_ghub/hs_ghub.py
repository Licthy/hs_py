import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import keyboard
import threading
import time
import logging
import pyautogui

from pystray import Icon, MenuItem as item
from PIL import Image, ImageDraw

# 配置日志（记录错误和运行状态）
logging.basicConfig(
    filename='text_converter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 全局变量
is_hidden = False
hotkey_thread = None  # 快捷键监听线程


def convert_text():
    """文本转换逻辑（增加异常捕获和日志）"""
    try:
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
        logging.error(error_msg, exc_info=True)  # 记录详细错误堆栈


def hotkey_listener():
    """快捷键监听函数（带自动重启机制）"""
    while True:  # 循环确保线程崩溃后能重启
        try:
            logging.info("快捷键监听线程启动")
            keyboard.add_hotkey('ctrl+f1', convert_text)
            keyboard.wait()  # 持续监听（阻塞直到被中断）
        except Exception as e:
            logging.error(f"快捷键监听线程异常，将在2秒后重启：{str(e)}", exc_info=True)
            keyboard.unhook_all()  # 清除所有快捷键，避免重复注册
            time.sleep(2)  # 等待5秒后重启
        finally:
            keyboard.unhook_all()  # 退出前清除快捷键


def start_hotkey_thread():
    """启动快捷键监听线程（确保单一线程）"""
    global hotkey_thread
    if hotkey_thread is None or not hotkey_thread.is_alive():
        hotkey_thread = threading.Thread(target=hotkey_listener, daemon=True)
        hotkey_thread.start()
        logging.info("已启动快捷键监听线程")


def create_tray_icon(window):
    """创建系统托盘图标和菜单（优化线程管理）"""
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
        keyboard.unhook_all()
        logging.info("程序正常退出")
        exit()

    menu = (item('退出', on_exit),)
    icon = Icon("TextConverter", create_image(), "TextConverter", menu)
    
    # 托盘线程独立运行，避免阻塞
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


def minimize_to_tray(window):
    global is_hidden
    is_hidden = True
    window.withdraw()
    create_tray_icon(window)


def main_window():
    window = tk.Tk()
    window.title("TextConverter")
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

    # 启动快捷键监听线程
    start_hotkey_thread()

    # 窗口关闭时的清理
    def on_close():
        keyboard.unhook_all()
        logging.info("窗口关闭，程序退出")
        window.destroy()
    window.protocol("WM_DELETE_WINDOW", on_close)

    window.mainloop()


if __name__ == "__main__":
    logging.info("程序启动")
    main_window()