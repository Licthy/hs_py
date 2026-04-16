import tkinter as tk
import pyautogui
import threading
import time

# ---------------------- 配置参数 ----------------------
POINT_SIZE = 5       # 点的大小
UPDATE_INTERVAL = 0.05
CHECK_RANGE = 5
# ------------------------------------------------------

class AdaptivePoint:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-toolwindow', True)

        # 关键：透明背景
        self.root.attributes('-transparentcolor', 'white')

        self.window_size = POINT_SIZE
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.window_size) // 2
        y = (screen_height - self.window_size) // 2
        self.root.geometry(f"{self.window_size}x{self.window_size}+{x}+{y}")

        # 背景设为 white，会被自动透明掉
        self.canvas = tk.Canvas(
            self.root,
            width=self.window_size,
            height=self.window_size,
            bg="white",
            highlightthickness=0
        )
        self.canvas.pack()

        self.point = self.canvas.create_oval(
            1, 1,
            self.window_size - 1,
            self.window_size - 1,
            fill="red"
        )

        self.root.bind("<Escape>", self.quit_app)
        self.root.bind("<Control-q>", self.quit_app)

        self.running = True
        self.color_thread = threading.Thread(target=self.update_color_loop, daemon=True)
        self.color_thread.start()

    def get_background_brightness(self, x, y):
        total = 0
        count = 0
        for dx in range(-CHECK_RANGE, CHECK_RANGE + 1):
            for dy in range(-CHECK_RANGE, CHECK_RANGE + 1):
                try:
                    r, g, b = pyautogui.pixel(x + dx, y + dy)
                    total += 0.299*r + 0.587*g + 0.114*b
                    count += 1
                except:
                    continue
        return total / count if count else 128

    def update_color_loop(self):
        while self.running:
            x = self.root.winfo_rootx() + self.window_size // 2
            y = self.root.winfo_rooty() + self.window_size // 2
            bright = self.get_background_brightness(x, y)
            color = "black" if bright > 127 else "white"
            self.canvas.itemconfig(self.point, fill=color)
            time.sleep(UPDATE_INTERVAL)

    def quit_app(self, event=None):
        self.running = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AdaptivePoint()
    app.run()