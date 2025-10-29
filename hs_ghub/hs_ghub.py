import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
import keyboard
import threading
from pystray import Icon, MenuItem as item
from PIL import Image, ImageDraw
import pyautogui

# 全局变量：记录窗口是否隐藏到托盘
is_hidden = False

def convert_text():
    """文本转换逻辑（与之前相同，增加GUI提示）"""
    try:
        pyautogui.hotkey('ctrl', 'c')
        clipboard_text = pyperclip.paste()
        if not clipboard_text:
            return
        
        processed_text = clipboard_text.strip('"').strip()
        parts = [part.strip() for part in processed_text.split(',') if part.strip()]
        
        if not parts:
            return
        
        converted_parts = [f'{{"{part}",{part}}}' for part in parts]
        result = ','.join(converted_parts)
        
        pyperclip.copy(result)
        pyautogui.hotkey('ctrl', 'v')
        
    except Exception as e:
        print("error")

def create_tray_icon(window):
    """创建系统托盘图标和菜单"""
    # 创建一个简单的托盘图标（白色背景+黑色文字"T"）
    def create_image():
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        draw.text((15, 10), "T", font_size=40, fill='black')  # 简单文字图标
        return image

    # 托盘图标点击事件：恢复窗口显示
    def on_tray_click(icon, item):
        global is_hidden
        if not is_hidden:
            return
        is_hidden = False
        window.deiconify()  # 恢复窗口
        icon.stop()  # 停止托盘图标（避免重复显示）

    # 退出程序
    def on_exit(icon, item):
        icon.stop()  # 停止托盘
        window.destroy()  # 关闭窗口
        keyboard.unhook_all()  # 移除快捷键监听
        exit()  # 退出程序

    # 创建托盘菜单
    menu = (item('退出', on_exit),)
    # 创建托盘图标
    icon = Icon("TextConverter", create_image(), "TextConverter", menu)
    
    # 启动托盘图标监听（在子线程中运行，避免阻塞GUI）
    threading.Thread(target=icon.run, daemon=True).start()
    return icon

def minimize_to_tray(window):
    """最小化窗口到系统托盘"""
    global is_hidden
    is_hidden = True
    window.withdraw()  # 隐藏窗口
    create_tray_icon(window)  # 显示托盘图标

def main_window():
    """创建主窗口"""
    window = tk.Tk()
    window.title("TextConverter")
    window.geometry("400x200")  # 窗口大小
    window.resizable(False, False)  # 禁止拉伸

    # 窗口最小化事件绑定：最小化时隐藏到托盘
    def on_minimize(event):
        if window.state() == 'iconic':  # 检测到窗口被最小化
            minimize_to_tray(window)
    window.bind("<Unmap>", on_minimize)  # 窗口隐藏时触发

    # 界面内容
    ttk.Label(
        window,
        text="按下 Ctrl+F1 执行文本转换\n\n格式要求：剪贴板文本应为 Test,Name,Value（可带引号或空格）\n转换后结果会自动复制到剪贴板",
        justify="left",
        font=("微软雅黑", 10)
    ).pack(padx=20, pady=30)

    # 底部按钮
    frame = ttk.Frame(window)
    frame.pack(pady=10)
    ttk.Button(frame, text="退出", command=window.destroy).pack(side="right", padx=10)
    ttk.Button(frame, text="转换（Ctrl+F1）", command=convert_text).pack(side="right")

    # 注册全局快捷键（在子线程中监听，避免阻塞GUI）
    def start_hotkey_listener():
        keyboard.add_hotkey('ctrl+f1', convert_text)
        keyboard.wait()  # 持续监听

    threading.Thread(target=start_hotkey_listener, daemon=True).start()

    # 启动GUI主循环
    window.mainloop()

if __name__ == "__main__":
    main_window()