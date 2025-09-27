import pyautogui
import time
import tkinter as tk
from tkinter import ttk, messagebox

#小红书视频发送到微信使用的

class CopyPasteRepeater:
    def __init__(self, root):
        self.root = root
        self.root.title("自动发送视频")
        self.root.geometry("300x150")
        self.root.resizable(False, False)

        # 设置中文字体
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10))

        # 运行次数输入
        ttk.Label(root, text="请输入文件个数:").pack(pady=10)
        self.count_var = tk.StringVar(value="")
        count_frame = ttk.Frame(root)
        count_frame.pack(pady=5)
        ttk.Entry(count_frame, textvariable=self.count_var, width=10).pack(side=tk.LEFT)
        ttk.Label(count_frame, text="").pack(side=tk.LEFT, padx=5)

        # 开始按钮
        ttk.Button(root, text="开始执行", command=self.execute).pack(pady=15)

        # 状态标签
        self.status_var = tk.StringVar(value="请设置次数并点击开始")
        ttk.Label(root, textvariable=self.status_var).pack(pady=5)

    def execute(self):
        try:
            # 获取输入的运行次数
            count = int(self.count_var.get())
            if count <= 0:
                messagebox.showerror("错误", "文件个数不正确")
                return

            # 3秒准备时间，让用户切换到目标窗口
            for i in range(5, 0, -1):
                self.status_var.set(f"将在 {i} 秒后开始...")
                self.root.update()
                time.sleep(1)

            self.status_var.set("正在执行...")
            self.root.update()

            # 执行指定次数的复制粘贴
            for i in range(count):
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.3)
                pyautogui.hotkey('alt', 'tab')
                time.sleep(0.3)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(0.5)
                pyautogui.hotkey('alt', 'tab')
                time.sleep(0.3)
                pyautogui.press('down')
                time.sleep(0.3)
                # 更新状态
                self.status_var.set(f"已执行 {i + 1}/{count} 个")
                self.root.update()

            self.status_var.set(f"完成！共执行 {count} 个")
            messagebox.showinfo("完成", f"已成功执行 {count} 个")

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
        except Exception as e:
            messagebox.showerror("错误", f"发生错误: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CopyPasteRepeater(root)
    root.mainloop()
