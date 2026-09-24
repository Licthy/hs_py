# -*- coding: utf-8 -*-
"""微信视频自动发送。

找图：OpenCV matchTemplate（TM_CCOEFF_NORMED），只取最高分。
本机微信 4.1.9.55、DPI 96 实测：sousuo.png、fasongwenjian.png 最高相似度 1.000；
没有继续发送弹窗时，jixufasong.png 最高误匹配 0.542。阈值用 0.85。
搜索框没有「搜索」占位时，改点实测搜索框，再全选清空后粘贴群名。
「打开」不找图。文件框是系统窗口 #32770，按钮文字是「打开(&O)」，文件列表类名是 SHELLDLL_DefView。
进入目录后用 SendMessageTimeout 等文件框空闲，再全选、打开。
阻塞式 GetWindowText 会在加载视频时把脚本卡死在回车之后、全选之前。
会话名核对：用微软雅黑 14 绘制「群名 (」做模板匹配。实测正确「1群 (」0.818，其他群名最高 0.618。
"""
import ctypes
import json
import re
import sys
import time
from ctypes import wintypes
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import cv2
import numpy as np
import pyautogui
import pyperclip
from PIL import Image, ImageDraw, ImageFont, ImageGrab
from PySide6.QtCore import QPoint, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = app_dir()
RES_DIR = BASE_DIR / "res"
CONFIG_PATH = RES_DIR / "send_config.json"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")


def read_bgr(path):
    # Windows 下 cv2.imread 打不开中文路径。
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_bgr(path, image):
    suffix = Path(path).suffix.lower() or ".png"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        return False
    encoded.tofile(path)
    return True

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
TEMPLATE_THRESHOLD = 0.85
TITLE_THRESHOLD = 0.75
SEARCH_BOX_REL = (84, 42, 255, 68)
FIRST_RESULT_FROM_BOX = (76, 66)
INPUT_FROM_FILE_BUTTON = (150, -100)
WM_CLOSE = 0x0010
WM_NULL = 0x0000
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
SMTO_ABORTIFHUNG = 0x0002
user32 = ctypes.windll.user32
user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_longlong),
]
user32.SendMessageTimeoutW.restype = wintypes.LPARAM


class StopRequested(Exception):
    pass


class SendError(Exception):
    pass


def natural_key(name):
    parts = re.split(r"(\d+)", name)
    key = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.casefold()))
    return key


def pair_targets(folder_names, group_names):
    if not folder_names or not group_names:
        return []
    return [
        (folder_name, group_names[index % len(group_names)])
        for index, folder_name in enumerate(folder_names)
    ]


def inspect_crop(folder):
    crop = folder / "output_crop"
    result = {
        "ok": False,
        "reason": "",
        "videos": 0,
        "others": 0,
        "subdirs": 0,
        "files": [],
        "crop": crop,
    }
    if not crop.is_dir():
        result["reason"] = "没有 output_crop"
        return result
    children = list(crop.iterdir())
    files = [path for path in children if path.is_file()]
    subdirs = [path for path in children if path.is_dir()]
    videos = [path for path in files if path.suffix.lower() in VIDEO_SUFFIXES]
    others = [path for path in files if path.suffix.lower() not in VIDEO_SUFFIXES]
    result["videos"] = len(videos)
    result["others"] = len(others)
    result["subdirs"] = len(subdirs)
    result["files"] = sorted(files, key=lambda path: natural_key(path.name))
    if subdirs:
        result["reason"] = "output_crop 里有子文件夹，全选后打开可能进入子文件夹"
        return result
    if not files:
        result["reason"] = "没有文件"
        return result
    result["ok"] = True
    return result


def window_text(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def send_timeout(hwnd, msg, wparam=0, lparam=0, timeout_ms=200):
    result = ctypes.c_longlong(0)
    ok = user32.SendMessageTimeoutW(
        hwnd,
        msg,
        wparam,
        lparam,
        SMTO_ABORTIFHUNG,
        timeout_ms,
        ctypes.byref(result),
    )
    if not ok:
        return None
    return int(result.value)


def window_text_timeout(hwnd, timeout_ms=200):
    length = send_timeout(hwnd, WM_GETTEXTLENGTH, 0, 0, timeout_ms)
    if length is None or length < 0:
        return None
    length = min(length, 65535)
    buffer = ctypes.create_unicode_buffer(length + 1)
    copied = send_timeout(hwnd, WM_GETTEXT, length + 1, ctypes.addressof(buffer), timeout_ms)
    if copied is None:
        return None
    return buffer.value


def same_dir(left, right):
    if not left or not right:
        return False
    left_path = str(Path(left)).replace("/", "\\").rstrip("\\").casefold()
    right_path = str(Path(right)).replace("/", "\\").rstrip("\\").casefold()
    return left_path == right_path


def window_class(hwnd):
    buffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buffer, 256)
    return buffer.value


def window_rect(hwnd):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def enum_top_windows():
    found = []

    def callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(proto(callback), 0)
    return found


def enum_child_windows(hwnd):
    found = []

    def callback(child, _lparam):
        found.append(child)
        return True

    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumChildWindows(hwnd, proto(callback), 0)
    return found


def find_wechat_hwnd():
    candidates = []
    for hwnd in enum_top_windows():
        if window_text(hwnd) != "微信" or window_class(hwnd) != "Qt51514QWindowIcon":
            continue
        rect = window_rect(hwnd)
        if rect is None:
            continue
        left, top, right, bottom = rect
        candidates.append(((right - left) * (bottom - top), hwnd))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def activate_hwnd(hwnd):
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)
    user32.keybd_event(0x12, 0, 0, 0)
    user32.SetForegroundWindow(hwnd)
    user32.keybd_event(0x12, 0, 2, 0)


def grab_region(rect):
    left, top, right, bottom = rect
    image = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def virtual_screen():
    left = user32.GetSystemMetrics(76)
    top = user32.GetSystemMetrics(77)
    width = user32.GetSystemMetrics(78)
    height = user32.GetSystemMetrics(79)
    return left, top, left + width, top + height


def render_title_template(group_name):
    if not FONT_PATH.exists():
        raise SendError(f"找不到字体：{FONT_PATH}")
    canvas = Image.new("L", (560, 48), 255)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT_PATH), 14)
    draw.text((2, 2), f"{group_name} (", font=font, fill=30)
    pixels = np.array(canvas)
    mask = pixels < 200
    rows, cols = np.where(mask)
    if len(cols) == 0:
        raise SendError(f"无法绘制群名：{group_name}")
    return pixels[rows.min(): rows.max() + 1, cols.min(): cols.max() + 1]


def load_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data):
    RES_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CONFIG_PATH)

class SendWorker(QThread):
    logged = Signal(str)
    progressed = Signal(int, str)
    hide_requested = Signal()
    show_requested = Signal()
    run_finished = Signal(bool, str)

    def __init__(self, jobs, continue_wait, attach_wait):
        super().__init__()
        self.jobs = jobs
        self.continue_wait = continue_wait
        self.attach_wait = attach_wait
        self.stop_requested = False
        self.saved_clipboard = None
        self.templates = {}
        self.search_box_rel = SEARCH_BOX_REL
        self.opened_dialogs = []

    def request_stop(self):
        self.stop_requested = True

    def log(self, text):
        self.logged.emit(text)

    def check_stop(self):
        if self.stop_requested:
            raise StopRequested()
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        if point.x <= 2 and point.y <= 2:
            self.log("鼠标移到屏幕左上角，已停止")
            raise StopRequested()

    def wait_seconds(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.check_stop()
            time.sleep(0.05)

    def paste_text(self, text):
        pyperclip.copy(text)
        self.wait_seconds(0.05)
        pyautogui.hotkey("ctrl", "v")
        self.wait_seconds(0.05)

    def require_wechat(self):
        hwnd = find_wechat_hwnd()
        if hwnd is None:
            raise SendError("没有找到已打开的微信窗口")
        activate_hwnd(hwnd)
        self.wait_seconds(0.25)
        if user32.GetForegroundWindow() != hwnd:
            activate_hwnd(hwnd)
            self.wait_seconds(0.25)
        if user32.GetForegroundWindow() != hwnd:
            raise SendError("微信没有切到前台，已停止")
        rect = window_rect(hwnd)
        if rect is None:
            raise SendError("读不到微信窗口位置")
        return hwnd, rect

    def match_template(self, name, rect, threshold):
        screen = grab_region(rect)
        template = self.templates[name]
        if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
            return None, 0.0
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _min_value, score, _min_loc, loc = cv2.minMaxLoc(result)
        score = float(score)
        if score < threshold:
            return None, score
        height, width = template.shape[:2]
        left = rect[0] + loc[0]
        top = rect[1] + loc[1]
        return {
            "score": score,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "center": (left + width // 2, top + height // 2),
        }, score

    def find_file_button(self, rect):
        left, top, right, bottom = rect
        narrow = (left, max(top, bottom - 160), right, bottom)
        match, score = self.match_template("fasongwenjian.png", narrow, TEMPLATE_THRESHOLD)
        if match is None:
            match, score = self.match_template("fasongwenjian.png", rect, TEMPLATE_THRESHOLD)
        if match is None:
            raise SendError(f"没有找到发送文件按钮，最高相似度 {score:.3f}")
        return match

    def click_search_box(self, rect):
        region = (rect[0], rect[1], min(rect[2], rect[0] + 420), min(rect[3], rect[1] + 130))
        match, score = self.match_template("sousuo.png", region, TEMPLATE_THRESHOLD)
        if match is not None:
            rel_left = match["left"] - rect[0]
            rel_top = match["top"] - rect[1]
            box_left = rel_left - 5
            box_top = rel_top - 2
            box_bottom = rel_top + match["height"] - 1
            box_right = box_left + (SEARCH_BOX_REL[2] - SEARCH_BOX_REL[0])
            self.search_box_rel = (box_left, box_top, box_right, box_bottom)
            pyautogui.click(*match["center"])
            self.log(f"已点击搜索框，相似度 {match['score']:.3f}")
            return
        box_left, box_top, box_right, box_bottom = self.search_box_rel
        pyautogui.click(rect[0] + (box_left + box_right) // 2, rect[1] + (box_top + box_bottom) // 2)
        self.log(f"搜索占位图未出现（最高 {score:.3f}），改点已记录的搜索框")

    def click_first_result(self, rect):
        box_left, _box_top, _box_right, box_bottom = self.search_box_rel
        click_x = rect[0] + box_left + FIRST_RESULT_FROM_BOX[0]
        click_y = rect[1] + box_bottom + FIRST_RESULT_FROM_BOX[1]
        click_x = min(max(click_x, rect[0] + 8), rect[2] - 8)
        click_y = min(max(click_y, rect[1] + 8), rect[3] - 8)
        pyautogui.click(click_x, click_y)

    def title_score(self, rect, group_name):
        screen = grab_region((rect[0], rect[1], rect[2], min(rect[3], rect[1] + 90)))
        band = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        template = render_title_template(group_name)
        if template.shape[0] >= band.shape[0] or template.shape[1] >= band.shape[1]:
            return 0.0, 1.0
        result = cv2.matchTemplate(band, template, cv2.TM_CCOEFF_NORMED)
        _min_value, score, _min_loc, loc = cv2.minMaxLoc(result)
        height = template.shape[0]
        left_slice = band[loc[1]: loc[1] + height, max(0, loc[0] - 8): loc[0]]
        left_dark = float((left_slice < 180).mean()) if left_slice.size else 0.0
        return float(score), left_dark

    def verify_title(self, group_name):
        hwnd = find_wechat_hwnd()
        rect = window_rect(hwnd) if hwnd else None
        if rect is None:
            raise SendError("进入会话后找不到微信窗口")
        score, left_dark = self.title_score(rect, group_name)
        if score < TITLE_THRESHOLD or left_dark > 0.12:
            self.wait_seconds(0.45)
            hwnd = find_wechat_hwnd()
            rect = window_rect(hwnd) if hwnd else rect
            score, left_dark = self.title_score(rect, group_name)
        if score < TITLE_THRESHOLD or left_dark > 0.12:
            raise SendError(
                f"会话名对不上「{group_name}」，相似度 {score:.3f}，左侧文字 {left_dark:.3f}，没有发送"
            )
        self.log(f"会话名核对通过，相似度 {score:.3f}")

    def focus_input(self, file_button, rect):
        click_x = file_button["center"][0] + INPUT_FROM_FILE_BUTTON[0]
        click_y = file_button["center"][1] + INPUT_FROM_FILE_BUTTON[1]
        click_x = min(max(click_x, rect[0] + 20), rect[2] - 20)
        click_y = min(max(click_y, rect[1] + 20), rect[3] - 20)
        pyautogui.click(click_x, click_y)

    def send_markers(self, folder_name, file_button, rect):
        self.focus_input(file_button, rect)
        self.wait_seconds(0.15)
        text = f"开始发送-{folder_name}"
        for index in range(5):
            self.check_stop()
            pyautogui.hotkey("ctrl", "a")
            self.wait_seconds(0.05)
            self.paste_text(text)
            pyautogui.press("enter")
            self.wait_seconds(0.3)
            self.log(f"已发送开头消息 {index + 1}/5")

    def list_file_dialogs(self):
        dialogs = []
        for hwnd in enum_top_windows():
            if window_class(hwnd) != "#32770":
                continue
            text = window_text_timeout(hwnd, 200)
            if text == "选择文件":
                dialogs.append(hwnd)
        return dialogs

    def close_opened_dialogs(self):
        for hwnd in self.opened_dialogs:
            if user32.IsWindow(hwnd):
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    def wait_file_dialog(self):
        for _ in range(32):
            self.check_stop()
            dialogs = self.list_file_dialogs()
            if dialogs:
                hwnd = dialogs[-1]
                if hwnd not in self.opened_dialogs:
                    self.opened_dialogs.append(hwnd)
                return hwnd
            self.wait_seconds(0.25)
        raise SendError("点击发送文件后没有出现文件选择窗口")

    def dialog_responsive(self, hwnd):
        if send_timeout(hwnd, WM_NULL, 0, 0, 200) is None:
            return False
        for child in enum_child_windows(hwnd):
            if window_class(child) != "SHELLDLL_DefView":
                continue
            if send_timeout(child, WM_NULL, 0, 0, 200) is None:
                return False
        return True

    def wait_dialog_idle(self, hwnd, timeout):
        start = time.time()
        logged = False
        stable = 0
        while time.time() - start < timeout:
            self.check_stop()
            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                raise SendError("文件框在加载目录时关闭了")
            if self.dialog_responsive(hwnd):
                stable += 1
                if stable >= 2:
                    return
            else:
                stable = 0
                if not logged:
                    self.log("文件框正在加载目录，等它空闲后再全选")
                    logged = True
            self.wait_seconds(0.25)
        raise SendError("文件框一直在加载，超时未全选")

    def find_class_rect(self, hwnd, class_name):
        for child in enum_child_windows(hwnd):
            if window_class(child) != class_name:
                continue
            rect = window_rect(child)
            if rect is not None:
                return rect
        return None

    def find_button_rect(self, hwnd, prefix):
        for child in enum_child_windows(hwnd):
            if window_class(child) != "Button":
                continue
            text = window_text_timeout(child, 200)
            if not text or not text.startswith(prefix):
                continue
            return window_rect(child)
        return None

    def filename_box_text(self, hwnd):
        found = False
        best_top = None
        best_text = ""
        for child in enum_child_windows(hwnd):
            if window_class(child) != "Edit":
                continue
            rect = window_rect(child)
            if rect is None:
                continue
            found = True
            text = window_text_timeout(child, 200) or ""
            if best_top is None or rect[1] >= best_top:
                best_top = rect[1]
                best_text = text
        if not found:
            return None
        return best_text

    def filename_matches(self, text, file_names):
        if not text:
            return ""
        lowered = text.casefold()
        for name in file_names:
            if name.casefold() in lowered:
                return name
        return ""

    def save_dialog_shot(self, hwnd):
        rect = window_rect(hwnd)
        if rect is None:
            return
        image = grab_region(rect)
        RES_DIR.mkdir(parents=True, exist_ok=True)
        path = RES_DIR / "last_dialog.png"
        if not write_bgr(path, image):
            self.log("文件框截图没有保存成功")
            return
        self.log(f"已保存文件框截图 {path}")

    def paste_folder_path(self, hwnd, crop_path):
        activate_hwnd(hwnd)
        self.wait_seconds(0.12)
        pyautogui.hotkey("alt", "d")
        self.wait_seconds(0.12)
        pyautogui.hotkey("ctrl", "a")
        self.paste_text(str(crop_path))
        self.wait_seconds(0.05)
        pyautogui.press("enter")

    def select_target_files(self, hwnd, file_names):
        list_rect = self.find_class_rect(hwnd, "SHELLDLL_DefView")
        if list_rect is None:
            rect = window_rect(hwnd)
            if rect is None:
                raise SendError("文件框位置丢失")
            click = ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)
            self.log("没有找到文件列表，改点文件框中间")
        else:
            click = ((list_rect[0] + list_rect[2]) // 2, (list_rect[1] + list_rect[3]) // 2)
        activate_hwnd(hwnd)
        self.wait_seconds(0.1)
        for attempt in range(6):
            self.check_stop()
            pyautogui.click(*click)
            self.wait_seconds(0.15)
            pyautogui.hotkey("ctrl", "a")
            self.wait_seconds(0.25)
            name_text = self.filename_box_text(hwnd)
            if not name_text or not name_text.strip():
                self.log(f"第 {attempt + 1} 次文件名框是空的")
                if attempt == 5:
                    self.log("文件名框没有显示已选文件，仍点击打开")
                    return
            else:
                matched = self.filename_matches(name_text, file_names)
                if matched:
                    shown = name_text.strip()
                    if len(shown) > 80:
                        shown = shown[:80] + "..."
                    self.log(f"已全选，文件名框含 {matched}：{shown}")
                    return
                self.log(f"第 {attempt + 1} 次全选没有选中目标文件")
                if attempt == 5:
                    self.save_dialog_shot(hwnd)
                    raise SendError("全选后文件名框不是目标文件，没有点打开")
            self.wait_seconds(0.4)

    def click_open(self, hwnd):
        button_rect = self.find_button_rect(hwnd, "打开")
        activate_hwnd(hwnd)
        self.wait_seconds(0.1)
        if button_rect is None:
            self.log("没有定位到打开按钮，改用 Alt+O")
            pyautogui.hotkey("alt", "o")
        else:
            pyautogui.click(
                (button_rect[0] + button_rect[2]) // 2,
                (button_rect[1] + button_rect[3]) // 2,
            )
            self.log("已点击打开")
        self.wait_seconds(0.6)
        if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
            self.log("文件框还在，补按 Alt+O")
            activate_hwnd(hwnd)
            pyautogui.hotkey("alt", "o")

    def wait_dialog_closed(self, hwnd):
        start = time.time()
        next_log = 5
        while time.time() - start < 60:
            self.check_stop()
            if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
                self.log(f"文件已放入输入框，文件框关闭用时 {time.time() - start:.1f} 秒")
                return
            elapsed = time.time() - start
            if elapsed >= next_log:
                self.log(f"已点打开，文件框仍在，已等 {elapsed:.0f} 秒")
                next_log += 5
            self.wait_seconds(0.25)
        self.save_dialog_shot(hwnd)
        raise SendError("点击打开后文件框没有关闭")

    def address_state(self, hwnd, target):
        saw_edit = False
        for child in enum_child_windows(hwnd):
            if window_class(child) != "Edit":
                continue
            saw_edit = True
            text = window_text_timeout(child, 200) or ""
            if same_dir(text, target):
                return "editing"
        if not saw_edit:
            return "unknown"
        return "closed"

    def attach_files(self, crop_path, file_button, file_names):
        pyautogui.click(*file_button["center"])
        dialog = self.wait_file_dialog()
        activate_hwnd(dialog)
        self.wait_seconds(0.2)
        target = str(crop_path)
        for attempt in range(3):
            self.check_stop()
            self.paste_folder_path(dialog, target)
            self.log(f"已输入目录并回车（第 {attempt + 1} 次），等文件框空闲后再全选")
            self.wait_dialog_idle(dialog, 60)
            if self.address_state(dialog, target) == "editing":
                self.log("地址还停在输入框，再按一次回车")
                activate_hwnd(dialog)
                pyautogui.press("enter")
                self.wait_dialog_idle(dialog, 60)
            self.log("文件框已空闲，开始全选")
            try:
                self.select_target_files(dialog, file_names)
            except SendError as exc:
                if attempt == 2:
                    raise
                self.log(f"{exc}，重新进入目录")
                continue
            self.click_open(dialog)
            self.wait_dialog_closed(dialog)
            return
        self.save_dialog_shot(dialog)
        raise SendError(f"文件框没有完成全选和打开：{target}")

    def flush_sends(self, file_count):
        hwnd = find_wechat_hwnd()
        if hwnd is not None:
            activate_hwnd(hwnd)
            self.wait_seconds(0.15)
        pyautogui.press("enter")
        clicks = 0
        limit = max(8, (file_count + 8) // 9 + 2)
        while True:
            self.check_stop()
            self.wait_seconds(self.continue_wait)
            match, score = self.match_template("jixufasong.png", virtual_screen(), TEMPLATE_THRESHOLD)
            if match is None:
                self.log(f"未找到继续发送，最高相似度 {score:.3f}，本文件夹视为已发完")
                return
            clicks += 1
            if clicks > limit:
                raise SendError(f"继续发送点了 {clicks - 1} 次仍未结束，已停止")
            pyautogui.click(*match["center"])
            self.log(f"已点击继续发送 {clicks}，相似度 {match['score']:.3f}")
            disappeared = False
            for _ in range(10):
                self.wait_seconds(0.1)
                again, _score = self.match_template("jixufasong.png", virtual_screen(), TEMPLATE_THRESHOLD)
                if again is None:
                    disappeared = True
                    break
            if not disappeared:
                pyautogui.click(*match["center"])
                self.wait_seconds(0.4)
                again, again_score = self.match_template(
                    "jixufasong.png", virtual_screen(), TEMPLATE_THRESHOLD
                )
                if again is not None:
                    raise SendError(f"继续发送按钮没有消失，相似度 {again_score:.3f}")
            hwnd = find_wechat_hwnd()
            if hwnd is not None:
                activate_hwnd(hwnd)
                self.wait_seconds(0.1)
            pyautogui.press("enter")

    def send_one(self, index, total, job):
        folder_name = job["folder_name"]
        group_name = job["group_name"]
        prefix = f"[{index}/{total}] {folder_name} → {group_name}"
        self.progressed.emit(int((index - 1) * 100 / total), f"正在发送 {prefix}")
        self.log(f"{prefix} 开始，{len(job['files'])} 个文件")
        for file_name in job["files"]:
            self.log(f"  待发送 {file_name}")
        _hwnd, rect = self.require_wechat()
        self.click_search_box(rect)
        self.wait_seconds(0.2)
        pyautogui.hotkey("ctrl", "a")
        self.wait_seconds(0.05)
        pyautogui.press("backspace")
        self.paste_text(group_name)
        self.wait_seconds(0.9)
        _hwnd, rect = self.require_wechat()
        self.click_first_result(rect)
        self.wait_seconds(0.3)
        pyautogui.press("enter")
        self.wait_seconds(0.5)
        self.verify_title(group_name)
        _hwnd, rect = self.require_wechat()
        file_button = self.find_file_button(rect)
        self.send_markers(folder_name, file_button, rect)
        _hwnd, rect = self.require_wechat()
        file_button = self.find_file_button(rect)
        self.attach_files(job["crop"], file_button, job["files"])
        self.wait_seconds(self.attach_wait)
        self.flush_sends(len(job["files"]))
        self.progressed.emit(int(index * 100 / total), f"已完成 {prefix}")
        self.log(f"{prefix} 完成")

    def run(self):
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05
        ok = False
        message = "已停止"
        try:
            try:
                self.saved_clipboard = pyperclip.paste()
            except Exception:
                self.saved_clipboard = None
            for name in ("sousuo.png", "fasongwenjian.png", "jixufasong.png"):
                path = RES_DIR / name
                image = read_bgr(path)
                if image is None:
                    raise SendError(f"读不到模板图：{path}")
                self.templates[name] = image
            self.log("请确认微信已设置为回车发送。找图阈值 0.85。")
            for second in range(3, 0, -1):
                self.progressed.emit(0, f"{second} 秒后开始，可把鼠标移到左上角停止")
                self.wait_seconds(1)
            self.hide_requested.emit()
            self.wait_seconds(0.4)
            total = len(self.jobs)
            for index, job in enumerate(self.jobs, start=1):
                self.check_stop()
                self.send_one(index, total, job)
            ok = True
            message = "全部发送完成"
        except StopRequested:
            message = "已停止"
            self.close_opened_dialogs()
        except SendError as exc:
            message = str(exc)
            self.log(message)
            self.close_opened_dialogs()
        except Exception as exc:
            message = f"发送失败：{exc}"
            self.log(message)
            self.close_opened_dialogs()
        finally:
            if self.saved_clipboard is not None:
                try:
                    pyperclip.copy(self.saved_clipboard)
                except Exception:
                    pass
            self.show_requested.emit()
            self.run_finished.emit(ok, message)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("微信视频自动发送工具")
        self.resize(1040, 820)
        self.setMinimumSize(920, 700)
        self.setFont(QFont("Microsoft YaHei", 10))
        self.setWindowIcon(self.build_icon())
        self.worker = None
        self._updating_labels = False
        self._loading = True
        self.build_ui()
        self.setStyleSheet(self.style_text())
        self.load_state()
        self._loading = False

    def build_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#2f7cf6"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(1, 1, 30, 30, 7, 7)
        painter.setBrush(QColor("#ffffff"))
        center = pixmap.rect().center()
        painter.drawPolygon([
            center + QPoint(-4, -7),
            center + QPoint(-4, 7),
            center + QPoint(8, 0),
        ])
        painter.end()
        return QIcon(pixmap)

    def build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        title = QLabel("微信视频自动发送工具")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        subtitle = QLabel("选择文件夹和目标群，自动遍历 output_crop 发送视频到微信群")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        path_card = self.card()
        path_layout = QVBoxLayout(path_card)
        path_layout.setContentsMargins(12, 10, 12, 10)
        path_layout.setSpacing(8)
        path_layout.addWidget(QLabel("待发送文件夹"))
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择包含子文件夹的目录")
        self.path_edit.returnPressed.connect(self.scan_folders)
        browse = QPushButton("浏览")
        browse.setObjectName("browseBtn")
        browse.clicked.connect(self.browse_folder)
        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse)
        path_layout.addLayout(path_row)
        layout.addWidget(path_card)

        columns = QHBoxLayout()
        columns.setSpacing(10)
        columns.addWidget(self.build_folder_card(), 1)
        columns.addWidget(self.build_group_card(), 1)
        layout.addLayout(columns, 3)

        self.pair_label = QLabel("勾选后按从上到下配对，群不够就从第一个再循环")
        self.pair_label.setObjectName("hint")
        self.pair_label.setWordWrap(True)
        layout.addWidget(self.pair_label)

        progress_card = self.card()
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(12, 10, 12, 10)
        progress_layout.setSpacing(8)
        progress_layout.addWidget(QLabel("发送进度"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.status_label = QLabel("等待开始")
        self.status_label.setObjectName("status")
        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.status_label)
        layout.addWidget(progress_card)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("开始发送")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_send)
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("danger")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_send)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        button_row.addStretch(1)
        button_row.addWidget(self.hint_label("继续发送判定"))
        self.continue_spin = self.make_spin(0.3)
        button_row.addWidget(self.continue_spin)
        button_row.addWidget(self.hint_label("放入后等待"))
        self.attach_spin = self.make_spin(1.0)
        button_row.addWidget(self.attach_spin)
        hint = QLabel("鼠标移到屏幕左上角可紧急停止")
        hint.setObjectName("hint")
        button_row.addWidget(hint)
        layout.addLayout(button_row)

        log_card = self.card()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(12, 10, 12, 10)
        log_layout.setSpacing(8)
        log_layout.addWidget(QLabel("运行日志"))
        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("log")
        self.log_edit.setReadOnly(True)
        log_font = QFont()
        log_font.setFamilies(["Consolas", "Microsoft YaHei"])
        log_font.setPointSize(9)
        self.log_edit.setFont(log_font)
        log_layout.addWidget(self.log_edit)
        layout.addWidget(log_card, 1)

    def hint_label(self, text):
        label = QLabel(text)
        label.setObjectName("hint")
        return label

    def make_spin(self, value):
        spin = QDoubleSpinBox()
        spin.setRange(0.1, 5.0)
        spin.setSingleStep(0.1)
        spin.setDecimals(1)
        spin.setValue(value)
        spin.setSuffix(" 秒")
        spin.valueChanged.connect(lambda _value: self.save_state())
        return spin

    def card(self):
        frame = QFrame()
        frame.setObjectName("card")
        return frame

    def build_folder_card(self):
        card = self.card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(QLabel("选择要处理的文件夹"))
        row = QHBoxLayout()
        row.addWidget(self.small_button("全选", self.check_all_folders))
        row.addWidget(self.small_button("取消", self.uncheck_all_folders))
        row.addStretch(1)
        row.addWidget(self.small_button("刷新", self.scan_folders))
        layout.addLayout(row)
        self.folder_list = QListWidget()
        self.folder_list.setMinimumHeight(240)
        self.folder_list.itemChanged.connect(self.on_folder_changed)
        layout.addWidget(self.folder_list)
        return card

    def build_group_card(self):
        card = self.card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(QLabel("选择目标群（循环发送）"))
        row = QHBoxLayout()
        row.addWidget(self.small_button("全选", self.check_all_groups))
        row.addWidget(self.small_button("取消", self.uncheck_all_groups))
        row.addStretch(1)
        row.addWidget(self.small_button("添加群", self.add_group))
        row.addWidget(self.small_button("删除", self.delete_groups))
        layout.addLayout(row)
        self.group_list = QListWidget()
        self.group_list.setMinimumHeight(240)
        self.group_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.group_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.group_list.itemChanged.connect(self.on_group_changed)
        self.group_list.itemDoubleClicked.connect(self.rename_group)
        self.group_list.model().rowsMoved.connect(lambda *_args: self.on_group_changed(None))
        layout.addWidget(self.group_list)
        return card

    def small_button(self, text, handler):
        button = QPushButton(text)
        button.setObjectName("ghost")
        button.clicked.connect(handler)
        return button

    def ensure_check_icon(self):
        RES_DIR.mkdir(parents=True, exist_ok=True)
        icon_path = RES_DIR / "check_mark.png"
        if icon_path.exists():
            return icon_path
        image = QPixmap(16, 16)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = painter.pen()
        pen.setColor(QColor("#ffffff"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(3, 8, 6, 12)
        painter.drawLine(6, 12, 13, 3)
        painter.end()
        image.save(str(icon_path))
        return icon_path

    def style_text(self):
        icon = self.ensure_check_icon().as_posix()
        return """
        QWidget#root { background: #f3f5f7; }
        QFrame#card { background: #ffffff; border: 1px solid #e6e8ec; border-radius: 10px; }
        QLabel#title { color: #1f2937; }
        QLabel#subtitle, QLabel#hint { color: #8b93a0; }
        QLabel#status { color: #374151; }
        QLineEdit, QDoubleSpinBox {
            background: #ffffff; border: 1px solid #d7dbe2; border-radius: 8px;
            padding: 4px 8px; min-height: 28px;
        }
        QPushButton#browseBtn, QPushButton#primary {
            background: #2f7cf6; color: white; border: none; border-radius: 8px;
            padding: 4px 16px; min-height: 32px;
        }
        QPushButton#primary { min-width: 120px; min-height: 36px; }
        QPushButton#danger {
            background: #e3534a; color: white; border: none; border-radius: 8px;
            padding: 4px 16px; min-width: 88px; min-height: 36px;
        }
        QPushButton#ghost {
            background: #ffffff; color: #2563eb; border: 1px solid #bfdbfe;
            border-radius: 8px; padding: 4px 12px; min-height: 28px;
        }
        QPushButton#primary:disabled, QPushButton#danger:disabled, QPushButton#browseBtn:disabled, QPushButton#ghost:disabled {
            background: #e5e7eb; color: #9ca3af; border: 1px solid #e5e7eb;
        }
        QListWidget {
            background: #f8fafc; border: 1px solid #eef0f3; border-radius: 8px; padding: 4px;
        }
        QListWidget::item { padding: 2px 4px; }
        QListWidget::item:selected, QListWidget::item:selected:!active { background: #e8f1ff; color: #1f2937; }
        QListWidget::indicator {
            width: 16px; height: 16px; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff;
        }
        QListWidget::indicator:checked {
            background: #2f7cf6; border: 1px solid #2f7cf6; image: url(ICON);
        }
        QProgressBar {
            border: none; background: #e8eef5; border-radius: 6px; min-height: 14px;
        }
        QProgressBar::chunk { background: #2f7cf6; border-radius: 6px; }
        QTextEdit#log { background: #ffffff; border: 1px solid #e6e8ec; border-radius: 8px; }
        """.replace("ICON", icon)

    def load_state(self):
        data = load_config()
        folder = data.get("folder") or ""
        if folder:
            self.path_edit.setText(folder)
            self.scan_folders()
        groups = data.get("groups") or [
            {"name": f"{index}群", "checked": False} for index in range(1, 11)
        ]
        for group in groups:
            name = str(group.get("name") or "").strip()
            if name:
                self.add_group_item(name, bool(group.get("checked")))
        if "continue_wait" in data:
            self.continue_spin.setValue(float(data["continue_wait"]))
        if "attach_wait" in data:
            self.attach_spin.setValue(float(data["attach_wait"]))
        self.refresh_pairing()

    def save_state(self):
        if self._loading:
            return
        groups = []
        for row in range(self.group_list.count()):
            item = self.group_list.item(row)
            groups.append({
                "name": item.text(),
                "checked": item.checkState() == Qt.CheckState.Checked,
            })
        save_config({
            "folder": self.path_edit.text().strip(),
            "groups": groups,
            "continue_wait": self.continue_spin.value(),
            "attach_wait": self.attach_spin.value(),
        })

    def browse_folder(self):
        current = self.path_edit.text().strip()
        selected = QFileDialog.getExistingDirectory(self, "选择待发送文件夹", current or str(Path.home()))
        if not selected:
            return
        self.path_edit.setText(selected)
        self.scan_folders()

    def scan_folders(self):
        checked = set()
        for row in range(self.folder_list.count()):
            item = self.folder_list.item(row)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable and item.checkState() == Qt.CheckState.Checked:
                checked.add(item.data(Qt.ItemDataRole.UserRole))
        self.folder_list.clear()
        folder = Path(self.path_edit.text().strip())
        if not folder.is_dir():
            self.append_log("待发送文件夹不存在")
            self.refresh_pairing()
            self.save_state()
            return
        children = [path for path in folder.iterdir() if path.is_dir()]
        children.sort(key=lambda path: natural_key(path.name))
        self._updating_labels = True
        for child in children:
            info = inspect_crop(child)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, str(child))
            item.setData(Qt.ItemDataRole.UserRole + 1, info["videos"])
            item.setData(Qt.ItemDataRole.UserRole + 2, info["others"])
            item.setData(Qt.ItemDataRole.UserRole + 3, info["reason"])
            if info["ok"]:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                state = Qt.CheckState.Checked if str(child) in checked else Qt.CheckState.Unchecked
                item.setCheckState(state)
            else:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setText(self.folder_text(child.name, info, None))
            self.folder_list.addItem(item)
        self._updating_labels = False
        self.refresh_pairing()
        self.save_state()

    def folder_text(self, name, info, group_name):
        if not info["ok"]:
            return f"{name}（{info['reason']}）"
        text = f"{name}（{info['videos']}个视频"
        if info["others"]:
            text += f"，另有{info['others']}个其他文件"
        text += "）"
        if group_name:
            text += f"  →  {group_name}"
        return text

    def checked_folder_items(self):
        items = []
        for row in range(self.folder_list.count()):
            item = self.folder_list.item(row)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable and item.checkState() == Qt.CheckState.Checked:
                items.append(item)
        return items

    def checked_group_names(self):
        names = []
        for row in range(self.group_list.count()):
            item = self.group_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                names.append(item.text())
        return names

    def item_info(self, item):
        folder = Path(item.data(Qt.ItemDataRole.UserRole))
        return {
            "ok": not item.data(Qt.ItemDataRole.UserRole + 3),
            "reason": item.data(Qt.ItemDataRole.UserRole + 3) or "",
            "videos": item.data(Qt.ItemDataRole.UserRole + 1) or 0,
            "others": item.data(Qt.ItemDataRole.UserRole + 2) or 0,
        }, folder

    def refresh_pairing(self):
        folders = self.checked_folder_items()
        groups = self.checked_group_names()
        names = [Path(item.data(Qt.ItemDataRole.UserRole)).name for item in folders]
        mapping = dict(pair_targets(names, groups))
        self._updating_labels = True
        for row in range(self.folder_list.count()):
            item = self.folder_list.item(row)
            info, folder = self.item_info(item)
            group_name = mapping.get(folder.name) if item in folders else None
            item.setText(self.folder_text(folder.name, info, group_name))
        self._updating_labels = False
        pairs = pair_targets(names, groups)
        if not pairs:
            self.pair_label.setText("勾选后按从上到下配对，群不够就从第一个再循环")
            return
        shown = "；".join(f"{folder} → {group}" for folder, group in pairs[:8])
        if len(pairs) > 8:
            shown += f"；等 {len(pairs)} 对"
        self.pair_label.setText(shown)

    def on_folder_changed(self, _item):
        if self._updating_labels or self._loading:
            return
        self.refresh_pairing()
        self.save_state()

    def on_group_changed(self, _item):
        if self._updating_labels or self._loading:
            return
        self.refresh_pairing()
        self.save_state()

    def set_all_checks(self, widget, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(widget.count()):
            item = widget.item(row)
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                item.setCheckState(state)

    def check_all_folders(self):
        self.set_all_checks(self.folder_list, True)

    def uncheck_all_folders(self):
        self.set_all_checks(self.folder_list, False)

    def check_all_groups(self):
        self.set_all_checks(self.group_list, True)

    def uncheck_all_groups(self):
        self.set_all_checks(self.group_list, False)

    def add_group_item(self, name, checked):
        item = QListWidgetItem(name)
        flags = item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
        item.setFlags(flags)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.group_list.addItem(item)

    def existing_groups(self):
        return [self.group_list.item(row).text() for row in range(self.group_list.count())]

    def add_group(self):
        name, accepted = QInputDialog.getText(self, "添加群", "群名要和微信里显示的一致")
        if not accepted:
            return
        name = name.strip()
        if not name:
            return
        if name in self.existing_groups():
            QMessageBox.warning(self, "添加群", "这个群已经在列表里")
            return
        self.add_group_item(name, True)
        self.refresh_pairing()
        self.save_state()

    def rename_group(self, item):
        name, accepted = QInputDialog.getText(self, "修改群名", "群名", text=item.text())
        if not accepted:
            return
        name = name.strip()
        if not name or name == item.text():
            return
        if name in self.existing_groups():
            QMessageBox.warning(self, "修改群名", "这个群已经在列表里")
            return
        item.setText(name)
        self.refresh_pairing()
        self.save_state()

    def delete_groups(self):
        selected = list(self.group_list.selectedItems())
        if not selected:
            self.append_log("请先选中要删除的群")
            return
        for item in selected:
            self.group_list.takeItem(self.group_list.row(item))
        self.refresh_pairing()
        self.save_state()

    def append_log(self, text):
        stamp = time.strftime("%H:%M:%S")
        self.log_edit.append(f"[{stamp}] {text}")

    def build_jobs(self):
        folders = self.checked_folder_items()
        groups = self.checked_group_names()
        if not folders:
            raise SendError("请勾选要发送的文件夹")
        if not groups:
            raise SendError("请勾选目标群")
        names = []
        infos = []
        for item in folders:
            folder = Path(item.data(Qt.ItemDataRole.UserRole))
            info = inspect_crop(folder)
            if not info["ok"]:
                raise SendError(f"{folder.name}：{info['reason']}")
            names.append(folder.name)
            infos.append((folder, info))
        jobs = []
        for (folder, info), (_name, group_name) in zip(infos, pair_targets(names, groups)):
            jobs.append({
                "folder_name": folder.name,
                "group_name": group_name,
                "crop": info["crop"],
                "files": [path.name for path in info["files"]],
            })
        return jobs

    def start_send(self):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            jobs = self.build_jobs()
        except SendError as exc:
            QMessageBox.warning(self, "不能开始", str(exc))
            return
        self.progress.setValue(0)
        self.status_label.setText("准备发送")
        self.status_label.setStyleSheet("color: #374151;")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.append_log("本次对应关系：")
        for job in jobs:
            self.append_log(f"  {job['folder_name']} → {job['group_name']}，{len(job['files'])} 个文件")
        self.worker = SendWorker(jobs, self.continue_spin.value(), self.attach_spin.value())
        self.worker.logged.connect(self.append_log)
        self.worker.progressed.connect(self.on_progress)
        self.worker.hide_requested.connect(self.showMinimized)
        self.worker.show_requested.connect(self.restore_window)
        self.worker.run_finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, value, text):
        self.progress.setValue(value)
        self.status_label.setText(text)

    def restore_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def stop_send(self):
        if self.worker is not None:
            self.worker.request_stop()
            self.append_log("正在停止")

    def on_finished(self, ok, message):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.restore_window()
        self.append_log(message)
        if ok:
            self.progress.setValue(100)
            self.status_label.setText("全部发送完成！")
            self.status_label.setStyleSheet("color: #16a34a;")
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #b91c1c;")
            if message != "已停止":
                QMessageBox.warning(self, "发送未完成", message)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(3000)
        self.save_state()
        event.accept()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication([])
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
