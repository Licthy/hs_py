import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import threading
import time
import logging
import pyautogui

from pystray import Icon, MenuItem as item
from PIL import Image, ImageDraw
from pynput import keyboard

# -------------------------- 配置与全局变量 --------------------------
# 日志配置（记录运行状态和错误）
logging.basicConfig(
    filename='text_converter.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 全局变量
is_hidden = False  # 窗口是否隐藏到托盘
listener_thread = None  # 快捷键监听线程
current_hotkey = None  # 当前活跃的快捷键监听实例
heartbeat_flag = False  # 线程心跳标记
listener_lock = threading.Lock()  # 线程锁（避免并发冲突）
last_run_time = 0 #最后的执行时间

# -------------------------- 核心功能：文本转换 --------------------------
def convert_text():
    """将剪贴板文本转换为目标格式"""
    try:
        # 读取剪贴板内容
        global last_run_time
        now_time = int(time.time() * 1000)
        if  now_time-last_run_time>200:
            last_run_time=now_time
            pyautogui.hotkey('ctrl', 'c')
            clipboard_text = pyperclip.paste()
            if not clipboard_text:
                logging.info("转换失败：剪贴板为空")
                return
            
            # 处理文本（去除引号、空格，按逗号分割）
            processed_text = clipboard_text.strip('"').strip()
            parts = [part.strip() for part in processed_text.split(',') if part.strip()]
            
            if not parts:
                logging.info(f"转换失败：无效内容 - {clipboard_text}")
                return
            
            # 转换格式并复制到剪贴板
            converted_parts = [f'{{"{part}",{part}}}' for part in parts]
            result = ','.join(converted_parts)
            pyperclip.copy(result)
            
            # 提示成功
            pyautogui.hotkey('ctrl', 'v')
            logging.info(f"转换成功：{clipboard_text} → {result}")
            
    except Exception as e:
        error_msg = f"转换失败：{str(e)}"
        logging.error(error_msg, exc_info=True)


# -------------------------- 快捷键监听（pynput） --------------------------
def on_hotkey_trigger():
    """快捷键触发时执行（更新心跳+调用转换函数）"""
    global heartbeat_flag
    heartbeat_flag = True  # 更新心跳标记
    logging.info("检测到 Ctrl+F1 触发")
    convert_text()


def pynput_listener_loop():
    """快捷键监听主循环（确保唯一绑定）"""
    global current_hotkey
    while True:
        try:
            with listener_lock:  # 加锁防止并发操作冲突
                # 停止旧的监听实例（如果存在）
                if current_hotkey is not None:
                    current_hotkey.stop()
                    logging.info("已停止旧的快捷键监听实例")
                
                # 创建新的快捷键监听（Ctrl+F1）
                current_hotkey = keyboard.GlobalHotKeys({
                    '<ctrl>+<f1>': on_hotkey_trigger
                })
                logging.info("已创建新的快捷键监听实例")

            # 启动监听（阻塞当前线程）
            with current_hotkey:
                current_hotkey.join()

        except Exception as e:
            logging.error(f"监听线程异常，5秒后重启：{str(e)}", exc_info=True)
            time.sleep(5)


def start_listener():
    """启动快捷键监听线程（确保单一线程）"""
    global listener_thread
    with listener_lock:
        if listener_thread is None or not listener_thread.is_alive():
            listener_thread = threading.Thread(target=pynput_listener_loop, daemon=True)
            listener_thread.start()
            logging.info("快捷键监听线程已启动")


# -------------------------- 心跳检测（防止监听失效） --------------------------
def heartbeat_monitor():
    """定期检查监听线程状态，失效则重启"""
    global heartbeat_flag
    while True:
        time.sleep(60)  # 每60秒检查一次
        # 检查条件：监听线程死亡 或 60秒内无心跳（未触发且未响应）
        thread_dead = (listener_thread is None or not listener_thread.is_alive())
        no_heartbeat = not heartbeat_flag
        
        if thread_dead or no_heartbeat:
            logging.warning(f"监听异常（线程存活：{not thread_dead}，心跳正常：{heartbeat_flag}），重启监听...")
            start_listener()  # 重启监听线程
        
        heartbeat_flag = False  # 重置心跳标记（等待下一次检查）


# -------------------------- 系统托盘功能 --------------------------
def create_tray_icon(window):
    """创建系统托盘图标和右键菜单"""
    # 生成简单图标（白色背景+黑色"T"）
    def create_image():
        img = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((15, 10), "T", font_size=40, fill='black')
        return img

    # 托盘图标点击：恢复窗口
    def on_tray_click(icon, item):
        global is_hidden
        if not is_hidden:
            return
        is_hidden = False
        window.deiconify()  # 显示窗口
        icon.stop()  # 停止托盘图标

    # 托盘右键菜单：退出程序
    def on_exit(icon, item):
        icon.stop()
        window.destroy()  # 关闭窗口
        logging.info("程序正常退出")
        exit()

    # 创建托盘菜单并启动
    menu = (item('退出', on_exit),)
    icon = Icon("TextConverter", create_image(), "文本转换工具", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


def minimize_to_tray(window):
    """最小化窗口到系统托盘"""
    global is_hidden
    is_hidden = True
    window.withdraw()  # 隐藏窗口
    create_tray_icon(window)  # 显示托盘图标


# -------------------------- GUI主窗口 --------------------------
def main_window():
    """创建主窗口"""
    window = tk.Tk()
    window.title("FormatLog")
    window.geometry("450x220")  # 窗口大小
    window.resizable(False, False)  # 禁止拉伸

    # 窗口最小化时隐藏到托盘
    def on_minimize(event):
        if window.state() == 'iconic':  # 检测到窗口被最小化
            minimize_to_tray(window)
    window.bind("<Unmap>", on_minimize)

    # 窗口内容：说明文本
    ttk.Label(
        window,
        text="功能说明：\n"
             "1. 复制格式为 'AAA,BBB,CCC' 的文本（可带引号或空格）\n"
             "2. 按下 Ctrl+F1 自动转换为 {'AAA',AAA},{'BBB',BBB},...\n"
             "提示：点击窗口最小化按钮可隐藏到系统托盘",
        justify="left",
        font=("微软雅黑", 10)
    ).pack(padx=20, pady=20)

    # 底部按钮
    frame = ttk.Frame(window)
    frame.pack(pady=10)
    ttk.Button(frame, text="退出", command=window.destroy).pack(side="right", padx=10)
    ttk.Button(frame, text="手动转换", command=convert_text).pack(side="right")

    # 窗口关闭时的清理
    def on_close():
        with listener_lock:
            if current_hotkey is not None:
                current_hotkey.stop()
        window.destroy()
        logging.info("窗口关闭，程序退出")
    window.protocol("WM_DELETE_WINDOW", on_close)

    # 启动核心线程
    start_listener()  # 启动快捷键监听
    threading.Thread(target=heartbeat_monitor, daemon=True).start()  # 启动心跳检测
    logging.info("程序启动完成")

    # 启动GUI主循环
    window.mainloop()


# -------------------------- 程序入口 --------------------------
if __name__ == "__main__":
    main_window()