import pyperclip
import keyboard
import time
import pyautogui


def convert_text():
    """执行文本转换逻辑"""
    try:
        # 从剪贴板获取文本
        pyautogui.hotkey('ctrl', 'c')
        clipboard_text = pyperclip.paste()
        
        if not clipboard_text:
            print("剪贴板为空，请先选中并复制文本（格式：AAA,BBB,CCC）")
            return
        
        # 处理文本（去除首尾引号和空格，按逗号分割）
        processed_text = clipboard_text.strip('"').strip()
        parts = [part.strip() for part in processed_text.split(',') if part.strip()]
        
        if not parts:
            print("未识别到有效内容，请检查格式（应为：AAA,BBB,CCC）")
            return
        
        # 转换为目标格式
        converted_parts = [f'{{"{part}",{part}}}' for part in parts]
        result = ','.join(converted_parts)
        
        # 输出结果并复制到剪贴板
        print(f"\n转换成功：\n{result}")
        pyperclip.copy(result)
        print("结果已复制到剪贴板\n")
        pyautogui.hotkey('ctrl', 'v')
        
    except Exception as e:
        print(f"转换出错：{str(e)}")

def main():
    # 注册全局快捷键：Ctrl+F1 触发转换函数
    keyboard.add_hotkey('ctrl+f1', convert_text)
    
    # 提示信息
    print("程序已启动，按下 Ctrl+F1 执行文本转换")
    print("格式要求：剪贴板文本应为 'AAA,BBB,CCC'（可带引号或空格）")
    print("转换后结果会自动复制到剪贴板，按 Ctrl+C 退出程序...\n")
    
    # 保持程序运行（监听快捷键）
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n程序已退出")

if __name__ == "__main__":
    main()