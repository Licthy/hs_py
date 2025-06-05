import tkinter as tk
import threading
import ddddocr
import pyautogui
import time
import os
import logging
from configparser import ConfigParser

# 配置文件路径常量
CONFIG_FILE_PATH = './cfg/config.ini'

# 配置日志记录器
logging.basicConfig(
    filename="error.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# 加载配置
def load_config():
    config = ConfigParser()
    print(f"当前工作目录: {os.getcwd()}")
    if os.path.exists(CONFIG_FILE_PATH):
        config.read(CONFIG_FILE_PATH)
    else:
        # 创建默认配置
        config['DEFAULT'] = {
            'screenshot_x': 891,
            'screenshot_y': 514,
            'screenshot_width': 100,
            'screenshot_height': 40,
            'verify_code_offset': 70,
            'confidence_threshold': 0.9,
            'check_interval': 1
        }
        with open(CONFIG_FILE_PATH, 'w',encoding='utf-8') as f:
            config.write(f)
    return config['DEFAULT']

class AutoLearningApp:
    def __init__(self, root):
        self.root = root
        self.root.title("自动学习")
        self.root.attributes("-topmost", True)
        
        # 窗口设置
        window_width = 300
        window_height = 150
        self.root.geometry(f"{window_width}x{window_height}")
        
        # 加载配置
        self.config = load_config()
        
        # 状态变量
        self.running = False
        self.execution_count = 0
        
        # 创建UI
        self.create_ui()
        
        # OCR初始化
        self.ocr = ddddocr.DdddOcr()
        
        # 资源路径
        self.resources = {
            'verify_code_img': './res/qtdk.png',
            'play_button_img': './res/bofh.png',
            'screenshot_path': './res/1.png'
        }
    
    def create_ui(self):
        pad_x = 20
        pad_y = 10
        
        self.status_label = tk.Label(self.root, text="就绪", anchor="w", padx=pad_x, pady=pad_y)
        self.status_label.pack()
        
        self.count_label = tk.Label(self.root, text="执行次数: 0", anchor="w", padx=pad_x, pady=pad_y)
        self.count_label.pack()
        
        self.start_button = tk.Button(self.root, text="开始", command=self.start_learning)
        self.start_button.pack()
    
    def start_learning(self):
        self.running = True
        self.start_button.config(state="disabled")
        threading.Thread(target=self.learning_loop, daemon=True).start()
    
    def stop_learning(self):
        self.running = False
        self.start_button.config(state="normal")
    
    def learning_loop(self):
        while self.running:
            try:
                self.execute_tasks()
                time.sleep(float(self.config['check_interval']))
            except Exception as e:
                logging.error(f"执行任务时出错: {str(e)}")
                self.update_status(f"错误: {str(e)}")
                time.sleep(5)  # 出错后等待更长时间
    
    def execute_tasks(self):
        self.execution_count += 1
        self.update_count()
        
        # 第一步：检查是否需要输入验证码
        self.update_status("第一步，判断是否需要输入验证码")
        verify_code_pos = self.locate_on_screen(self.resources['verify_code_img'])
        
        if verify_code_pos:
            self.update_status("识别到需要输入验证码")
            
            # 截图
            self.capture_screenshot()
            
            # 识别验证码
            code = self.recognize_code()
            self.update_status(f"验证码是:{code}")
            
            # 填写验证码
            self.fill_verify_code(verify_code_pos, code)
            
            # 点击确定
            pyautogui.click(verify_code_pos)
            time.sleep(1)
        
        # 第二步：检查是否需要点击播放按钮
        self.update_status("第二步，判断是否需要点击播放按钮")
        play_button_pos = self.locate_on_screen(self.resources['play_button_img'])
        
        if play_button_pos:
            pyautogui.click(play_button_pos)
            self.update_status("已点击播放按钮")
    
    def locate_on_screen(self, image_path):
        try:
            return pyautogui.locateCenterOnScreen(
                image_path, 
                confidence=float(self.config['confidence_threshold']), 
                grayscale=True
            )
        except Exception as e:
            logging.error(f"图像识别出错 ({image_path}): {str(e)}")
            return None
    
    def capture_screenshot(self):
        x = int(self.config['screenshot_x'])
        y = int(self.config['screenshot_y'])
        width = int(self.config['screenshot_width'])
        height = int(self.config['screenshot_height'])
        
        try:
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            screenshot.save(self.resources['screenshot_path'])
            return True
        except Exception as e:
            logging.error(f"截图出错: {str(e)}")
            return False
    
    def recognize_code(self):
        try:
            with open(self.resources['screenshot_path'], "rb") as f:
                image = f.read()
            return self.ocr.classification(image)
        except Exception as e:
            logging.error(f"验证码识别出错: {str(e)}")
            return ""
    
    def fill_verify_code(self, position, code):
        if not code:
            return
        
        try:
            # 点击输入框
            offset = int(self.config['verify_code_offset'])
            pyautogui.click(position.x, position.y - offset)
            time.sleep(0.5)
            
            # 清空输入框
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.3)
            pyautogui.press("del")
            time.sleep(0.3)
            
            # 输入验证码
            pyautogui.typewrite(code)
            time.sleep(0.5)
        except Exception as e:
            logging.error(f"填写验证码出错: {str(e)}")
    
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def update_count(self):
        self.count_label.config(text=f"执行次数: {self.execution_count}")
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoLearningApp(root)
    root.mainloop()        