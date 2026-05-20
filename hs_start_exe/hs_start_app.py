#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量程序启动器 — Qt 版
"""

import os
import json
import sys
import subprocess
import ctypes

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QInputDialog, QAbstractItemView,
)
from PySide6.QtCore import Qt, QUrl

APP_NAME = "HermesBatchLauncher"
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

COL_NAME, COL_ADMIN, COL_PATH = 0, 1, 2


class DropTable(QTableWidget):
    """支持从资源管理器拖放文件的表格"""

    def __init__(self, tab):
        super().__init__()
        self._tab = tab
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.viewport().setAcceptDrops(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["程序名称", "管理员", "路径"])
        self.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(COL_ADMIN, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(COL_PATH, QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                files.append(path)
        if files:
            self._tab.add_files(files)


class ProgramTab(QWidget):
    """单个页签"""

    def __init__(self, app: "App", name: str):
        super().__init__()
        self._app = app
        self.name = name
        self._items: list[dict] = []  # [{"path": str, "admin": bool}]

        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # ── 表格 ──
        self.table = DropTable(self)
        layout.addWidget(self.table, 1)

        # ── 底部工具栏 ──
        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ 添加程序")
        btn_add.clicked.connect(self._on_add)
        toolbar.addWidget(btn_add)
        btn_del = QPushButton("- 删除选中")
        btn_del.clicked.connect(self._on_remove)
        toolbar.addWidget(btn_del)
        btn_admin = QPushButton("⚡ 切换管理员")
        btn_admin.clicked.connect(self._on_toggle_admin)
        toolbar.addWidget(btn_admin)
        toolbar.addStretch()
        btn_launch = QPushButton("▶ 启动所有")
        btn_launch.setMinimumHeight(32)
        btn_launch.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px 20px;")
        btn_launch.clicked.connect(self._on_launch_all)
        toolbar.addWidget(btn_launch)
        layout.addLayout(toolbar)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                files.append(path)
        if files:
            self.add_files(files)

    # ── 公开接口 ──

    def add_files(self, paths: list[str]):
        """添加文件到列表（用于拖放和加载配置）"""
        added = 0
        for fp in paths:
            if not os.path.isfile(fp):
                continue
            if any(it["path"] == fp for it in self._items):
                continue
            self._items.append({"path": fp, "admin": False})
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, COL_NAME, QTableWidgetItem(os.path.basename(fp)))
            self.table.setItem(row, COL_ADMIN, QTableWidgetItem("否"))
            self.table.item(row, COL_ADMIN).setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, COL_PATH, QTableWidgetItem(fp))
            added += 1
        if added:
            self._app.save_config()

    def load_items(self, items: list[dict]):
        """从配置加载"""
        self.add_files([it["path"] for it in items])
        for i, it in enumerate(items):
            if i < len(self._items):
                self._items[i]["admin"] = it.get("admin", False)
                item = self.table.item(i, COL_ADMIN)
                if item:
                    item.setText("是" if self._items[i]["admin"] else "否")

    # ── 内部 ──

    def _on_add(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择可执行文件", "",
            "可执行文件 (*.exe *.com *.bat *.cmd *.ps1);;所有文件 (*.*)"
        )
        if paths:
            self.add_files(paths)

    def _on_remove(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        if not rows:
            return
        for r in rows:
            self.table.removeRow(r)
            del self._items[r]
        self._app.save_config()

    def _on_toggle_admin(self):
        rows = set(i.row() for i in self.table.selectedItems())
        for r in rows:
            self._items[r]["admin"] = not self._items[r]["admin"]
            self.table.item(r, COL_ADMIN).setText("是" if self._items[r]["admin"] else "否")
        if rows:
            self._app.save_config()

    def _on_launch_all(self):
        if not self._items:
            QMessageBox.information(self, "提示", "当前列表没有程序")
            return
        errors = []
        for it in self._items:
            fp = it["path"]
            name = os.path.basename(fp)
            if not os.path.isfile(fp):
                errors.append(f"文件不存在: {name}")
                continue
            try:
                if it["admin"]:
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", fp, "", "", 1)
                else:
                    try:
                        subprocess.Popen(fp, shell=False)
                    except OSError as e:
                        if e.winerror == 740:
                            # 权限不足，自动提权重试
                            ctypes.windll.shell32.ShellExecuteW(None, "runas", fp, "", "", 1)
                        else:
                            raise
            except Exception as e:
                errors.append(f"{name}: {e}")
        if errors:
            QMessageBox.warning(self, "启动结果", "\n".join(errors))


# ═══════════════════════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════════════════════

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("二师兄")
        self.resize(900, 560)

        # DPI
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # 中央区域
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 页签工具栏（放页签上方）
        tb = QHBoxLayout()
        tb.setContentsMargins(0, 0, 0, 4)

        btn_new = QPushButton("+ 添加页签")
        btn_new.clicked.connect(lambda checked, s=self: s._add_tab())
        tb.addWidget(btn_new)

        btn_copy = QPushButton("⧉ 复制页签")
        btn_copy.clicked.connect(self._copy_tab)
        tb.addWidget(btn_copy)

        btn_del = QPushButton("- 删除页签")
        btn_del.clicked.connect(self._remove_tab)
        tb.addWidget(btn_del)

        btn_rename = QPushButton("✏ 重命名")
        btn_rename.clicked.connect(self._rename_tab)
        tb.addWidget(btn_rename)

        tb.addStretch()
        main_layout.addLayout(tb)

        # 页签
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; }
            QTabBar::tab {
                padding: 6px 16px;
                margin-right: 2px;
                border: 1px solid #bbb;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background: #e8e8e8;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-bottom: 2px solid #1890ff;
                color: #1890ff;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #f0f0f0;
            }
        """)
        main_layout.addWidget(self.tabs, 1)

        # 数据
        self._tab_wrappers: list[ProgramTab] = []
        self._last_active_tab = 0
        self._load_config()
        if not self._tab_wrappers:
            self._add_tab("默认列表")
        # 恢复上次停留的页签
        if 0 <= self._last_active_tab < self.tabs.count():
            self.tabs.setCurrentIndex(self._last_active_tab)
        # 页签切换时自动保存
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # ── 页签管理 ──

    def _on_tab_changed(self, index: int):
        """页签切换时自动保存"""
        self._last_active_tab = index
        self.save_config()

    def _add_tab(self, name: str | None = None) -> ProgramTab:
        if name is None:
            name = f"列表 {len(self._tab_wrappers) + 1}"
        existing = {tw.name for tw in self._tab_wrappers}
        if name in existing:
            i = 2
            while f"{name} ({i})" in existing:
                i += 1
            name = f"{name} ({i})"

        try:
            tab = ProgramTab(self, name)
            self.tabs.addTab(tab, name)
            self._tab_wrappers.append(tab)
            self.tabs.setCurrentWidget(tab)
            self.save_config()
            return tab
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _remove_tab(self):
        if len(self._tab_wrappers) <= 1:
            QMessageBox.warning(self, "提示", "至少要保留一个列表")
            return
        idx = self.tabs.currentIndex()
        if idx < 0:
            return
        tab = self._tab_wrappers[idx]
        if tab._items:
            reply = QMessageBox.question(
                self, "确认删除",
                f"列表「{tab.name}」中有 {len(tab._items)} 个程序，确定删除？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.tabs.removeTab(idx)
        self._tab_wrappers.pop(idx)
        self.save_config()

    def _rename_tab(self):
        idx = self.tabs.currentIndex()
        if idx < 0:
            return
        tab = self._tab_wrappers[idx]
        name, ok = QInputDialog.getText(self, "重命名页签", "新名称:", text=tab.name)
        if ok and name.strip():
            name = name.strip()
            tab.name = name
            self.tabs.setTabText(idx, name)
            self.save_config()

    def _copy_tab(self):
        idx = self.tabs.currentIndex()
        if idx < 0:
            return
        source = self._tab_wrappers[idx]
        base = source.name
        name = f"{base}（复制）"
        existing = {tw.name for tw in self._tab_wrappers}
        if name in existing:
            i = 2
            while f"{base}（复制 {i}）" in existing:
                i += 1
            name = f"{base}（复制 {i}）"
        tab = self._add_tab(name)
        tab.load_items([dict(it) for it in source._items])

    # ── 持久化 ──

    def save_config(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = {
            "last_active_tab": self.tabs.currentIndex(),
            "tabs": [
                {"name": tw.name, "programs": tw._items}
                for tw in self._tab_wrappers
            ],
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_config(self):
        if not os.path.isfile(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "读取配置失败", str(e))
            return
        # 兼容旧格式（数组 → 新格式）
        if isinstance(data, list):
            tabs_data = data
        else:
            tabs_data = data.get("tabs", [])
            self._last_active_tab = data.get("last_active_tab", 0)
        for item in tabs_data:
            tab = self._add_tab(item.get("name", "未命名"))
            tab.load_items(item.get("programs", []))

    def closeEvent(self, event):
        self.save_config()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = App()
    win.show()
    sys.exit(app.exec())
