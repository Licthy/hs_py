"""
FormatLog - PySide6 版
- 深色主题 (slate-950)
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

import pyperclip
import pyautogui
from pynput import keyboard

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QSystemTrayIcon,
    QMenu, QGroupBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction, QFont, QColor, QPixmap, QPainter, QBrush

# ── 初始化 ──────────────────────────────────────────────
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05  # 每次 pyautogui 操作间 50ms 延迟
BASE_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = BASE_DIR / "config.json"

# ── QSS（只负责颜色/边框，字体用 QFont） ────────────────
QSS = """
QWidget { background: #020617; color: #cbd5e1; }
QMainWindow { background: #020617; }
QGroupBox {
    border: 1px solid #1e293b; border-radius: 8px;
    margin-top: 16px; padding: 20px 16px 16px 16px;
    font-weight: bold; color: #94a3b8;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px; }
QPushButton {
    background: #0f172a; color: #38bdf8;
    border: 1px solid #1e293b; border-radius: 6px;
    padding: 8px 16px; font-weight: 600;
}
QPushButton:hover { background: #1e293b; border-color: #38bdf8; }
QPushButton#applyBtn { background: #06b6d4; color: #020617; border: none; font-weight: 700; }
QPushButton#applyBtn:hover { background: #22d3ee; }
QLineEdit {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 6px;
    padding: 8px 12px; color: #e2e8f0;
}
QLineEdit:focus { border-color: #38bdf8; }
QTextEdit {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 6px;
    padding: 10px; color: #94a3b8;
}
QLabel#statusLabel { color: #10b981; font-weight: 600; }
QLabel#statusLabel[inactive="true"] { color: #ef4444; }
QScrollBar:vertical { background: #020617; width: 6px; }
QScrollBar::handle:vertical { background: #334155; border-radius: 3px; min-height: 20px; }
"""

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


# ── 主窗口 ────────────────────────────────────────────
class FormatLogWindow(QMainWindow):
    log_signal = Signal(str)
    status_signal = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FormatLog")
        self.setFixedSize(560, 680)
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

        self._tray = None
        self._setup_tray()
        self._setup_ui()

        self.log_signal.connect(self._on_log)
        self.status_signal.connect(self._on_status)
        self._start_listener()

    # ── 配置 ─────────────────────────────────────
    def _load_config(self) -> dict:
        default = {"hotkey": "<ctrl>+<f1>"}
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg.setdefault("hotkey", default["hotkey"])
                return cfg
        except Exception:
            pass
        return default

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log(f"保存配置失败: {e}")

    # ── UI ───────────────────────────────────────
    def _setup_ui(self):
        self.setFont(QFont("Microsoft YaHei", 10))

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("FormatLog")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #38bdf8;")
        layout.addWidget(title)

        subtitle = QLabel("文本格式转换工具")
        subtitle.setStyleSheet("font-size: 13px; color: #64748b;")
        layout.addWidget(subtitle)

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

        hint = QLabel("格式: Ctrl+Alt+Shift+字母 或 Ctrl+F1~F12")
        hint.setStyleSheet("font-size: 12px; color: #475569;")
        s_layout.addWidget(hint)
        layout.addWidget(shortcut_group)

        # ── 转换说明 ─────────────────────────
        info_group = QGroupBox("转换规则")
        i_layout = QVBoxLayout(info_group)
        i_layout.setSpacing(6)
        i_layout.addWidget(QLabel("输入格式:"))
        ex1 = QLabel("  'AAA,BBB,CCC'")
        ex1.setStyleSheet("color: #fbbf24; font-family: 'Consolas', monospace; font-size: 14px;")
        i_layout.addWidget(ex1)
        i_layout.addWidget(QLabel("输出格式:"))
        ex2 = QLabel("  {'AAA',AAA},{'BBB',BBB},{'CCC',CCC}")
        ex2.setStyleSheet("color: #34d399; font-family: 'Consolas', monospace; font-size: 14px;")
        i_layout.addWidget(ex2)
        usage = QLabel("用法: 选中文本 → 按快捷键 → 原地替换")
        usage.setStyleSheet("font-size: 13px; color: #64748b; margin-top: 4px;")
        i_layout.addWidget(usage)
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
        from datetime import datetime
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
        """原位替换: 复制选中 → 转换 → 剪贴板粘贴替换
        使用剪贴板粘贴替代逐字键入，避免：
        1. pyautogui.write 花括号转义导致多余 {} 层
        2. 中文输入法拦截按键导致异常
        """
        if not self._convert_lock.acquire(blocking=False):
            return
        try:
            now = time.time()
            if now - self._last_convert_time < 1.0:
                return
            self._last_convert_time = now

            hotkey_str = self.config.get("hotkey", "<ctrl>+<f1>")

            # ── 复制选中文本（利用用户按住的 Ctrl，避免 hotkey() 释放 Ctrl）──
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

            # ── 转换（无需转义，直接写剪贴板）──
            result = ",".join(f"{{'{p}',{p}}}" for p in parts)

            # ── 写入剪贴板 ──
            pyperclip.copy(result)
            time.sleep(0.05)

            # ── 粘贴替换选中（自己发 Ctrl+V，不依赖用户按住 Ctrl）──
            pyautogui.hotkey("ctrl", "v")

            self._log(f"✓ {text[:30]} → {result[:40]}")

        except Exception as e:
            self._log(f"异常: {e}")
        finally:
            self._convert_lock.release()


# ── 入口 ────────────────────────────────────────────────
def main():
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
    app.setStyleSheet(QSS)
    app.setQuitOnLastWindowClosed(False)
    window = FormatLogWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
