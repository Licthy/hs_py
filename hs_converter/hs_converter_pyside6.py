"""
FormatLog - PySide6 版
- 双主题: 纯白极简 / 暗夜模式，手动切换
- 自动切换: 早上 8:00 → 白天主题，晚上 20:00 → 暗夜主题
- 全局快捷键监听 (pynput)
- 选中文本原地替换: 一键完成
- 系统托盘最小化/恢复

转换: AAA,BBB,CCC → {'AAA',AAA},{'BBB',BBB},{'CCC',CCC}
"""
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime

import pyperclip
import pyautogui
from pynput import keyboard

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QSystemTrayIcon,
    QMenu, QGroupBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QAction, QFont, QColor, QPixmap, QPainter, QBrush

# ── 初始化 ──────────────────────────────────────────────
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05
BASE_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = BASE_DIR / "config.json"

# ── 两套 QSS ───────────────────────────────────────────
LIGHT_QSS = """
QWidget { background: #ffffff; color: #1a1a2e; }
QMainWindow { background: #ffffff; }
QGroupBox {
    border: 1px solid #e5e5e5; border-radius: 10px;
    margin-top: 16px; padding: 20px 16px 16px 16px;
    font-weight: bold; color: #6b7280;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px; }
QPushButton {
    background: #ffffff; color: #2563eb;
    border: 1.5px solid #d1d5db; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}
QPushButton:hover { background: #f8fafc; border-color: #2563eb; }
QPushButton#applyBtn { background: #2563eb; color: #ffffff; border: none; font-weight: 700; border-radius: 8px; }
QPushButton#applyBtn:hover { background: #1d4ed8; }
QPushButton#themeBtn { background: #ffffff; color: #6b7280; border: 1px solid #e5e5e5; border-radius: 6px; padding: 6px 14px; font-weight: 600; font-size: 12px; }
QPushButton#themeBtn:hover { background: #f3f4f6; border-color: #2563eb; color: #2563eb; }
QPushButton#themeBtn[active="true"] { background: #2563eb; color: #ffffff; border-color: #2563eb; }
QCheckBox { color: #6b7280; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1.5px solid #d1d5db; border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { background: #2563eb; border-color: #2563eb; }
QLineEdit {
    background: #f9fafb; border: 1.5px solid #e5e5e5; border-radius: 8px;
    padding: 8px 12px; color: #111827;
}
QLineEdit:focus { border-color: #2563eb; background: #ffffff; }
QTextEdit {
    background: #f9fafb; border: 1.5px solid #e5e5e5; border-radius: 8px;
    padding: 10px; color: #374151;
}
QLabel#statusLabel { color: #059669; font-weight: 600; }
QLabel#statusLabel[inactive="true"] { color: #ef4444; }
QScrollBar:vertical { background: #ffffff; width: 6px; }
QScrollBar::handle:vertical { background: #d1d5db; border-radius: 3px; min-height: 20px; }
"""

DARK_QSS = """
QWidget { background: #020617; color: #cbd5e1; }
QMainWindow { background: #020617; }
QGroupBox {
    border: 1px solid #1e293b; border-radius: 10px;
    margin-top: 16px; padding: 20px 16px 16px 16px;
    font-weight: bold; color: #94a3b8;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px; }
QPushButton {
    background: #0f172a; color: #38bdf8;
    border: 1px solid #1e293b; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}
QPushButton:hover { background: #1e293b; border-color: #38bdf8; }
QPushButton#applyBtn { background: #06b6d4; color: #020617; border: none; font-weight: 700; border-radius: 8px; }
QPushButton#applyBtn:hover { background: #22d3ee; }
QPushButton#themeBtn { background: #0f172a; color: #64748b; border: 1px solid #1e293b; border-radius: 6px; padding: 6px 14px; font-weight: 600; font-size: 12px; }
QPushButton#themeBtn:hover { background: #1e293b; border-color: #38bdf8; color: #38bdf8; }
QPushButton#themeBtn[active="true"] { background: #06b6d4; color: #020617; border-color: #06b6d4; }
QCheckBox { color: #94a3b8; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #334155; border-radius: 4px; background: #0f172a; }
QCheckBox::indicator:checked { background: #06b6d4; border-color: #06b6d4; }
QLineEdit {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
    padding: 8px 12px; color: #e2e8f0;
}
QLineEdit:focus { border-color: #38bdf8; }
QTextEdit {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
    padding: 10px; color: #94a3b8;
}
QLabel#statusLabel { color: #10b981; font-weight: 600; }
QLabel#statusLabel[inactive="true"] { color: #ef4444; }
QScrollBar:vertical { background: #020617; width: 6px; }
QScrollBar::handle:vertical { background: #334155; border-radius: 3px; min-height: 20px; }
"""

THEME_QSS = {"light": LIGHT_QSS, "dark": DARK_QSS}
THEME_NAMES = {"light": "☀ 白天", "dark": "🌙 暗夜"}

# ── 快捷键解析 ────────────────────────────────────────
def parse_hotkey(s: str) -> str:
    parts = s.lower().replace(" ", "").split("+")
    mapped = []
    for p in parts:
        p = p.strip()
        if p in ("ctrl", "control"):   mapped.append("<ctrl>")
        elif p == "alt":                mapped.append("<alt>")
        elif p == "shift":              mapped.append("<shift>")
        elif p in ("cmd", "win", "super"): mapped.append("<cmd>")
        elif p.startswith("f") and p[1:].isdigit(): mapped.append(f"<{p}>")
        else:                           mapped.append(p)
    return "+".join(mapped)

def prettify_hotkey(s: str) -> str:
    result = s.replace("<", "").replace(">", "")
    parts = result.split("+")
    pretty = []
    for p in parts:
        p = p.strip()
        if p.lower() in ("ctrl", "control"): pretty.append("Ctrl")
        elif p.lower() == "alt":             pretty.append("Alt")
        elif p.lower() == "shift":           pretty.append("Shift")
        elif p.lower() in ("cmd", "win", "super"): pretty.append("Win")
        elif p.lower().startswith("f") and p[1:].isdigit(): pretty.append(p.upper())
        elif len(p) == 1:                    pretty.append(p.upper())
        else:                                pretty.append(p)
    return "+".join(pretty)


def get_auto_theme() -> str:
    """根据当前时间返回应该使用的主题"""
    now = datetime.now()
    hour = now.hour
    # 8:00 - 19:59 → 白天, 20:00 - 7:59 → 暗夜
    if 8 <= hour < 20:
        return "light"
    return "dark"


# ── 主窗口 ────────────────────────────────────────────
class FormatLogWindow(QMainWindow):
    log_signal = Signal(str)
    status_signal = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FormatLog")
        self.setFixedSize(560, 720)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        self.config = self._load_config()
        self._hotkey_obj = None
        self._running = True
        self._listener_thread = None
        self._last_convert_time = 0
        self._convert_lock = threading.Lock()
        self._current_theme = None  # 当前实际主题
        self._auto_mode = self.config.get("theme_auto", True)

        self._tray = None
        self._setup_tray()
        self._setup_ui()

        self.log_signal.connect(self._on_log)
        self.status_signal.connect(self._on_status)

        # 初始应用主题
        self._apply_initial_theme()
        # 启动定时器，每分钟检查一次是否需要自动切换
        self._theme_timer = QTimer(self)
        self._theme_timer.timeout.connect(self._check_auto_switch)
        self._theme_timer.start(60_000)  # 每 60 秒

        self._start_listener()

    # ── 配置 ─────────────────────────────────────
    def _load_config(self) -> dict:
        default = {"hotkey": "<ctrl>+<f1>", "theme_auto": True}
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg.setdefault("hotkey", default["hotkey"])
                cfg.setdefault("theme_auto", default["theme_auto"])
                return cfg
        except Exception:
            pass
        return default

    def _save_config(self):
        try:
            self.config["theme_auto"] = self._auto_mode
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"保存配置失败: {e}")

    # ── 主题切换 ─────────────────────────────────
    def _apply_initial_theme(self):
        """启动时决定初始主题"""
        if self._auto_mode:
            theme = get_auto_theme()
        else:
            theme = self.config.get("manual_theme", "light")
        self._switch_theme(theme)

    def _check_auto_switch(self):
        """定时器回调：自动模式下检查是否需要切换"""
        if not self._auto_mode:
            return
        target = get_auto_theme()
        if self._current_theme != target:
            self._log(f"自动切换主题: {THEME_NAMES[self._current_theme]} → {THEME_NAMES[target]}")
            self._switch_theme(target)

    def _switch_theme(self, theme: str):
        """切换到指定主题"""
        if self._current_theme == theme:
            return
        self._current_theme = theme
        # 更新 QSS
        app = QApplication.instance()
        if app:
            app.setStyleSheet(THEME_QSS[theme])
        # 更新按钮状态
        self._update_theme_buttons()
        # 更新内联样式
        self._update_inline_styles()

    def _update_theme_buttons(self):
        """刷新两个主题按钮的 active 状态"""
        for name, btn in [("light", self._btn_light), ("dark", self._btn_dark)]:
            is_active = (name == self._current_theme)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_inline_styles(self):
        """更新不在 QSS 中管理的行内样式（标题颜色等）"""
        if self._current_theme == "light":
            title_color = "#2563eb"
            sub_color = "#6b7280"
            hint_color = "#9ca3af"
            input_color = "#d97706"
            output_color = "#059669"
        else:
            title_color = "#38bdf8"
            sub_color = "#64748b"
            hint_color = "#475569"
            input_color = "#fbbf24"
            output_color = "#34d399"

        self._title_label.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {title_color};")
        self._subtitle_label.setStyleSheet(f"font-size: 13px; color: {sub_color};")
        self._hint_label.setStyleSheet(f"font-size: 12px; color: {hint_color};")
        self._input_example.setStyleSheet(f"color: {input_color}; font-family: 'Consolas', monospace; font-size: 14px;")
        self._output_example.setStyleSheet(f"color: {output_color}; font-family: 'Consolas', monospace; font-size: 14px;")
        self._usage_label.setStyleSheet(f"font-size: 13px; color: {sub_color}; margin-top: 4px;")

    def _toggle_light(self):
        """手动切换到白天主题（不影响自动模式）"""
        self.config["manual_theme"] = "light"
        self._switch_theme("light")
        self._log("已切换: 白天主题")

    def _toggle_dark(self):
        """手动切换到暗夜主题（不影响自动模式）"""
        self.config["manual_theme"] = "dark"
        self._switch_theme("dark")
        self._log("已切换: 暗夜主题")

    def _toggle_auto(self, state):
        """自动模式开关 — 只启用/禁用定时切换，不立即改变主题"""
        self._auto_mode = bool(state)
        self._save_config()
        if self._auto_mode:
            self._log("自动模式已开启 (到点 8:00/20:00 自动切换)")
        else:
            self._log("自动模式已关闭")

    # ── UI ───────────────────────────────────────
    def _setup_ui(self):
        self.setFont(QFont("Microsoft YaHei", 10))

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # ── 标题行 + 主题切换 ───────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        title_col = QVBoxLayout()
        self._title_label = QLabel("FormatLog")
        self._title_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #2563eb;")
        title_col.addWidget(self._title_label)
        self._subtitle_label = QLabel("文本格式转换工具")
        self._subtitle_label.setStyleSheet("font-size: 13px; color: #6b7280;")
        title_col.addWidget(self._subtitle_label)
        header.addLayout(title_col)
        header.addStretch()

        # 主题切换按钮组
        theme_col = QVBoxLayout()
        theme_col.setSpacing(4)
        theme_row = QHBoxLayout()
        theme_row.setSpacing(4)

        self._btn_light = QPushButton("☀")
        self._btn_light.setObjectName("themeBtn")
        self._btn_light.setFixedSize(36, 28)
        self._btn_light.setToolTip("白天主题")
        self._btn_light.clicked.connect(self._toggle_light)
        theme_row.addWidget(self._btn_light)

        self._btn_dark = QPushButton("🌙")
        self._btn_dark.setObjectName("themeBtn")
        self._btn_dark.setFixedSize(36, 28)
        self._btn_dark.setToolTip("暗夜主题")
        self._btn_dark.clicked.connect(self._toggle_dark)
        theme_row.addWidget(self._btn_dark)

        theme_col.addLayout(theme_row)

        self._auto_check = QCheckBox("自动")
        self._auto_check.setChecked(self._auto_mode)
        self._auto_check.stateChanged.connect(self._toggle_auto)
        theme_col.addWidget(self._auto_check)

        header.addLayout(theme_col)
        layout.addLayout(header)

        # ── 状态 ─────────────────────────────
        self._status_label = QLabel("● 快捷键监听中")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self._status_label)

        # ── 快捷键设置 ─────────────────────────
        shortcut_group = QGroupBox("快捷键设置")
        s_layout = QVBoxLayout(shortcut_group)
        s_layout.setSpacing(10)

        row = QHBoxLayout()
        row.addWidget(QLabel("当前快捷键:"))
        self._hotkey_display = QLineEdit(prettify_hotkey(self.config["hotkey"]))
        self._hotkey_display.setReadOnly(True)
        self._hotkey_display.setFixedWidth(130)
        row.addWidget(self._hotkey_display)
        row.addStretch()
        s_layout.addLayout(row)

        row2 = QHBoxLayout()
        self._hotkey_input = QLineEdit()
        self._hotkey_input.setPlaceholderText("例: Ctrl+Shift+K")
        self._hotkey_input.returnPressed.connect(self._apply_hotkey)
        row2.addWidget(self._hotkey_input)
        apply_btn = QPushButton("应用")
        apply_btn.setObjectName("applyBtn")
        apply_btn.clicked.connect(self._apply_hotkey)
        apply_btn.setFixedWidth(60)
        row2.addWidget(apply_btn)
        s_layout.addLayout(row2)

        self._hint_label = QLabel("格式: Ctrl+Alt+Shift+字母 或 Ctrl+F1~F12")
        self._hint_label.setStyleSheet("font-size: 12px; color: #9ca3af;")
        s_layout.addWidget(self._hint_label)
        layout.addWidget(shortcut_group)

        # ── 转换说明 ─────────────────────────
        info_group = QGroupBox("转换规则")
        i_layout = QVBoxLayout(info_group)
        i_layout.setSpacing(6)
        i_layout.addWidget(QLabel("输入格式:"))
        self._input_example = QLabel("  'AAA,BBB,CCC'")
        self._input_example.setStyleSheet("color: #d97706; font-family: 'Consolas', monospace; font-size: 14px;")
        i_layout.addWidget(self._input_example)
        i_layout.addWidget(QLabel("输出格式:"))
        self._output_example = QLabel("  {'AAA',AAA},{'BBB',BBB},{'CCC',CCC}")
        self._output_example.setStyleSheet("color: #059669; font-family: 'Consolas', monospace; font-size: 14px;")
        i_layout.addWidget(self._output_example)
        self._usage_label = QLabel("用法: 选中文本 → 按快捷键 → 原地替换")
        self._usage_label.setStyleSheet("font-size: 13px; color: #6b7280; margin-top: 4px;")
        i_layout.addWidget(self._usage_label)
        layout.addWidget(info_group)

        # ── 日志 ──────────────────────────────
        log_group = QGroupBox("运行日志")
        l_layout = QVBoxLayout(log_group)
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumHeight(110)
        l_layout.addWidget(self._log_view)
        layout.addWidget(log_group)
        layout.addStretch()

    # ── 系统托盘 ──────────────────────────────────
    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self)
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setBrush(QBrush(QColor("#06b6d4")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(2, 2, 28, 28, 6, 6)
        p.end()
        self._tray.setIcon(QIcon(pix))
        menu = QMenu()
        menu.addAction("显示主窗口", self._show_window)
        menu.addSeparator()
        menu.addAction("退出", self._quit_app)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self._show_window()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        self._tray.setToolTip("FormatLog - 文本转换工具")
        self._tray.show()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self):
        self._running = False
        self._stop_listener()
        if self._tray:
            self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if self._tray and self._tray.isVisible():
            self.hide()
            self._log("窗口已最小化到系统托盘")
            event.ignore()
        else:
            self._quit_app()

    # ── 日志 ─────────────────────────────────────
    def _log(self, msg: str):
        self.log_signal.emit(msg)

    def _on_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_view.append(f"[{ts}] {msg}")

    def _on_status(self, msg: str, active: bool):
        self._status_label.setText(f"{'●' if active else '○'} {msg}")
        self._status_label.setProperty("inactive", not active)
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    # ── 快捷键 ──────────────────────────────────
    def _apply_hotkey(self):
        raw = self._hotkey_input.text().strip()
        if not raw:
            return
        try:
            parsed = parse_hotkey(raw)
            self.config["hotkey"] = parsed
            self._save_config()
            self._hotkey_display.setText(prettify_hotkey(parsed))
            self._hotkey_input.clear()
            self._log(f"快捷键已更新: {prettify_hotkey(parsed)}")
            self._start_listener()
        except Exception as e:
            self._log(f"快捷键格式无效: {e}")

    def _stop_listener(self):
        if self._hotkey_obj:
            try:
                self._hotkey_obj.stop()
            except Exception:
                pass
            self._hotkey_obj = None

    def _start_listener(self):
        self._stop_listener()
        time.sleep(0.15)
        hotkey_str = self.config.get("hotkey", "<ctrl>+<f1>")

        def on_trigger():
            self._do_convert()

        try:
            self._hotkey_obj = keyboard.GlobalHotKeys({hotkey_str: on_trigger})
        except Exception as e:
            self._log(f"快捷键注册失败: {e}")
            return

        def loop():
            while self._running:
                try:
                    with self._hotkey_obj:
                        self._hotkey_obj.join()
                except Exception:
                    if self._running:
                        time.sleep(1)
                        try:
                            hk = self.config.get("hotkey", "<ctrl>+<f1>")
                            self._hotkey_obj = keyboard.GlobalHotKeys({hk: on_trigger})
                        except Exception:
                            time.sleep(2)
                if not self._running:
                    break

        self._listener_thread = threading.Thread(target=loop, daemon=True)
        self._listener_thread.start()
        self._log(f"快捷键监听已启动: {prettify_hotkey(hotkey_str)}")
        self.status_signal.emit("快捷键监听中", True)

    # ── 核心转换 ──────────────────────────────────
    def _do_convert(self):
        if not self._convert_lock.acquire(blocking=False):
            return
        try:
            now = time.time()
            if now - self._last_convert_time < 1.0:
                return
            self._last_convert_time = now

            hotkey_str = self.config.get("hotkey", "<ctrl>+<f1>")

            if "ctrl" in hotkey_str.lower():
                pyautogui.keyDown("c")
                time.sleep(0.03)
                pyautogui.keyUp("c")
            else:
                pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)

            text = pyperclip.paste()
            if not text or not text.strip():
                self._log("剪贴板为空，请先选中文本")
                return

            clean = text.strip('"').strip("'").strip()
            parts = [p.strip() for p in clean.split(",") if p.strip()]
            if not parts:
                self._log(f"无逗号分隔 [{text[:40]}]")
                return

            result = ",".join(f"{{'{p}',{p}}}" for p in parts)
            pyperclip.copy(result)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")

            self._log(f"✓ {text[:30]} → {result[:40]}")

        except Exception as e:
            self._log(f"异常: {e}")
        finally:
            self._convert_lock.release()


# ── 入口 ────────────────────────────────────────────────
def main():
    # 在 Qt 初始化前设置 DPI，消除 "SetProcessDpiAwarenessContext() failed" 警告
    import ctypes as _ct
    try:
        _ct.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    import ctypes
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "FormatLog_PySide6_SI")
        if ctypes.windll.kernel32.GetLastError() == 183:
            ctypes.windll.user32.MessageBoxW(0, "FormatLog 已在运行中。", "提示", 0x40)
            sys.exit(0)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = FormatLogWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
