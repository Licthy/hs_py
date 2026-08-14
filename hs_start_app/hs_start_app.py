"""HS App Launcher - organize and launch groups of Windows applications."""

from __future__ import annotations

import ctypes
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QByteArray, QFileInfo, QMimeData, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


APP_NAME = "HS App Launcher"
REQUIRED_GROUP_ID = "required"
SUPPORTED_EXTENSIONS = {".exe", ".lnk", ".bat", ".cmd", ".com", ".url", ".msc"}
LIGHT_QSS = """
QWidget { background: transparent; color: #202124; }
QMainWindow, QWidget#workspace { background: #f5f8fc; }
QFrame#sidebar { background: #ffffff; border: none; border-right: 1px solid #dfe7f1; }
QLabel#brandTitle { color: #172033; font-size: 17px; font-weight: 800; }
QLabel#brandSub { color: #8a96a8; font-size: 11px; }
QLabel#sectionLabel { color: #8491a5; font-size: 11px; font-weight: 700; }
QLabel#pageTitle { color: #172033; font-size: 24px; font-weight: 800; }
QLabel#pageSub { color: #7a8799; font-size: 12px; }
QPushButton {
    background: #ffffff; color: #33363b;
    border: 1px solid #d9e2ee; border-radius: 6px;
    padding: 7px 13px; font-weight: 600;
}
QPushButton:hover { background: #f4f9ff; border-color: #78aef8; color: #1769d2; }
QPushButton:pressed { background: #e9f2ff; }
QPushButton:disabled { background: #f1f4f8; color: #b0bac8; border-color: #e2e8f0; }
QPushButton#addProgramBtn { background: #1769d2; color: #ffffff; border: none; padding: 8px 16px; }
QPushButton#addProgramBtn:hover { background: #247be5; color: #ffffff; }
QPushButton#launchBtn {
    background: #d91f35; color: #ffffff; border: none;
    border-radius: 6px; padding: 11px 26px; font-size: 14px; font-weight: 800;
}
QPushButton#launchBtn:hover { background: #ef2942; }
QPushButton#launchBtn:pressed { background: #b8172a; }
QPushButton#deleteBtn { color: #dc2626; border-color: #fca5a5; }
QPushButton#deleteBtn:hover { background: #fef2f2; border-color: #dc2626; }
QPushButton#toolBtn { padding: 5px; min-width: 28px; min-height: 28px; }
QPushButton#themeBtn { background: #f7f9fc; color: #718096; border: 1px solid #dce5f0; padding: 4px; }
QPushButton#themeBtn:hover { background: #eef6ff; color: #1769d2; border-color: #8bbaf8; }
QPushButton#themeBtn[active="true"] { background: #1769d2; color: #ffffff; border-color: #1769d2; }
QPushButton#addSceneBtn { background: #f4f8fd; color: #1769d2; border: 1px solid #d7e5f6; font-size: 18px; padding: 0; }
QPushButton#addSceneBtn:hover { background: #e7f2ff; border-color: #78aef8; }
QPushButton#configFolderBtn { background: #f7f9fc; color: #56647a; border: 1px solid #dce5f0; text-align: left; padding: 8px 10px; }
QPushButton#configFolderBtn:hover { background: #eef6ff; color: #1769d2; border-color: #8bbaf8; }
QListWidget#sceneList {
    background: transparent; color: #56647a; border: none; outline: none; padding: 0;
}
QListWidget#sceneList::item { border-radius: 6px; padding: 11px 12px; margin: 2px 0; min-height: 22px; font-weight: 600; }
QListWidget#sceneList::item:hover { background: #f0f6fd; color: #1769d2; }
QListWidget#sceneList::item:selected { background: #e6f1ff; color: #1769d2; border-left: 3px solid #2c7be5; }
QTreeWidget {
    background: #ffffff; border: 1px solid #dce5f0; border-radius: 6px;
    color: #263247; alternate-background-color: #fbfdff; outline: none;
}
QTreeWidget::item { min-height: 42px; padding: 3px 6px; border-bottom: 1px solid #edf2f7; }
QTreeWidget::item:hover { background: #f4f8fd; }
QTreeWidget::item:selected, QTreeWidget::item:selected:!active { background: #e6f1ff; color: #155eb8; }
QHeaderView::section { background: #f7fafe; color: #68778d; border: none; border-bottom: 1px solid #dce5f0; padding: 10px 8px; font-size: 11px; font-weight: 700; }
QCheckBox { color: #738197; spacing: 6px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #b7c4d5; border-radius: 3px; background: #ffffff; }
QCheckBox::indicator:checked { background: #2c7be5; border-color: #2c7be5; }
QFrame#launchBar { background: #ffffff; border: 1px solid #dce5f0; border-radius: 6px; }
QLabel#launchTitle { color: #24272c; font-size: 13px; font-weight: 700; }
QLabel#launchSummary { color: #7b889b; font-size: 11px; }
QTextEdit { background: #ffffff; border: 1px solid #dce5f0; border-radius: 6px; padding: 8px; color: #4d5c72; }
QLabel#countLabel { color: #1769d2; font-weight: 700; }
QMenu { background: #ffffff; color: #25282d; border: 1px solid #dce5f0; padding: 4px; }
QMenu::item { padding: 7px 28px 7px 16px; border-radius: 4px; }
QMenu::item:selected { background: #e6f1ff; color: #155eb8; }
QScrollBar:vertical { background: transparent; width: 7px; }
QScrollBar::handle:vertical { background: #c3cede; border-radius: 3px; min-height: 24px; }
"""


DARK_QSS = """
QWidget { background: transparent; color: #e5e7eb; }
QMainWindow, QWidget#workspace { background: #101114; }
QFrame#sidebar { background: #090a0c; border: none; }
QLabel#brandTitle { color: #ffffff; font-size: 17px; font-weight: 800; }
QLabel#brandSub { color: #666b74; font-size: 11px; }
QLabel#sectionLabel { color: #686d76; font-size: 11px; font-weight: 700; }
QLabel#pageTitle { color: #f4f4f5; font-size: 24px; font-weight: 800; }
QLabel#pageSub { color: #797f89; font-size: 12px; }
QPushButton {
    background: #1a1c20; color: #d5d7db;
    border: 1px solid #2b2e34; border-radius: 6px;
    padding: 7px 13px; font-weight: 600;
}
QPushButton:hover { background: #24272c; border-color: #474b53; }
QPushButton:pressed { background: #30333a; }
QPushButton:disabled { background: #15171a; color: #555a62; border-color: #24262b; }
QPushButton#addProgramBtn { background: #f1f2f4; color: #17181b; border: none; padding: 8px 16px; }
QPushButton#addProgramBtn:hover { background: #ffffff; }
QPushButton#launchBtn {
    background: #e11d36; color: #ffffff; border: none;
    border-radius: 6px; padding: 11px 26px; font-size: 14px; font-weight: 800;
}
QPushButton#launchBtn:hover { background: #f02b43; }
QPushButton#launchBtn:pressed { background: #ba172b; }
QPushButton#deleteBtn { color: #f87171; border-color: #7f1d1d; }
QPushButton#deleteBtn:hover { background: #1e0a0a; border-color: #f87171; }
QPushButton#toolBtn { padding: 5px; min-width: 28px; min-height: 28px; }
QPushButton#themeBtn { background: #141518; color: #747983; border: 1px solid #24262b; padding: 4px; }
QPushButton#themeBtn:hover { color: #ffffff; border-color: #4a4e56; }
QPushButton#themeBtn[active="true"] { background: #e11d36; color: #ffffff; border-color: #e11d36; }
QPushButton#addSceneBtn { background: #141518; color: #ffffff; border: 1px solid #24262b; font-size: 18px; padding: 0; }
QPushButton#addSceneBtn:hover { background: #202226; border-color: #e11d36; }
QListWidget#sceneList {
    background: transparent; color: #999fa9; border: none; outline: none; padding: 0;
}
QListWidget#sceneList::item { border-radius: 6px; padding: 11px 12px; margin: 2px 0; min-height: 22px; font-weight: 600; }
QListWidget#sceneList::item:hover { background: #17191d; color: #ffffff; }
QListWidget#sceneList::item:selected { background: #e11d36; color: #ffffff; }
QTreeWidget {
    background: #17191d; border: 1px solid #292c31; border-radius: 6px;
    color: #e3e5e8; alternate-background-color: #141619; outline: none;
}
QTreeWidget::item { min-height: 42px; padding: 3px 6px; border-bottom: 1px solid #22252a; }
QTreeWidget::item:hover { background: #202329; }
QTreeWidget::item:selected, QTreeWidget::item:selected:!active { background: #48151e; color: #ffffff; }
QHeaderView::section { background: #141619; color: #818791; border: none; border-bottom: 1px solid #292c31; padding: 10px 8px; font-size: 11px; font-weight: 700; }
QCheckBox { color: #8d929b; spacing: 6px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #4b4f57; border-radius: 3px; background: #16181c; }
QCheckBox::indicator:checked { background: #e11d36; border-color: #e11d36; }
QFrame#launchBar { background: #17191d; border: 1px solid #292c31; border-radius: 6px; }
QLabel#launchTitle { color: #f0f1f2; font-size: 13px; font-weight: 700; }
QLabel#launchSummary { color: #7f858f; font-size: 11px; }
QTextEdit { background: #17191d; border: 1px solid #292c31; border-radius: 6px; padding: 8px; color: #a5aab2; }
QLabel#countLabel { color: #f04459; font-weight: 700; }
QMenu { background: #1a1c20; color: #e4e5e7; border: 1px solid #30333a; padding: 4px; }
QMenu::item { padding: 7px 28px 7px 16px; border-radius: 4px; }
QMenu::item:selected { background: #48151e; color: #ffffff; }
QScrollBar:vertical { background: transparent; width: 7px; }
QScrollBar::handle:vertical { background: #3b3f46; border-radius: 3px; min-height: 24px; }
"""


def resource_path(filename: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def config_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home())) / "HSStartApp"
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


def new_id() -> str:
    return uuid.uuid4().hex


def default_config() -> dict:
    return {
        "version": 2,
        "theme": "light",
        "last_group_id": "work",
        "window_geometry": "",
        "groups": [
            {"id": REQUIRED_GROUP_ID, "name": "必起", "programs": []},
            {"id": "music", "name": "听歌", "programs": []},
            {"id": "games", "name": "游戏", "programs": []},
            {"id": "work", "name": "办公", "programs": []},
        ],
    }


def normalize_config(data: object) -> dict:
    if not isinstance(data, dict):
        return default_config()
    groups = data.get("groups")
    if not isinstance(groups, list):
        groups = []
    clean_groups = []
    seen_group_ids = set()
    for raw_group in groups:
        if not isinstance(raw_group, dict):
            continue
        group_id = str(raw_group.get("id") or new_id())
        if group_id in seen_group_ids:
            group_id = new_id()
        seen_group_ids.add(group_id)
        programs = []
        for raw_program in raw_group.get("programs", []):
            if not isinstance(raw_program, dict) or not raw_program.get("path"):
                continue
            path = os.path.abspath(os.path.expandvars(str(raw_program["path"])))
            programs.append(
                {
                    "id": str(raw_program.get("id") or new_id()),
                    "name": str(raw_program.get("name") or Path(path).stem),
                    "path": path,
                    "admin": bool(raw_program.get("admin", False)),
                    "enabled": bool(raw_program.get("enabled", True)),
                }
            )
        clean_groups.append(
            {"id": group_id, "name": str(raw_group.get("name") or "未命名"), "programs": programs}
        )
    required = next((g for g in clean_groups if g["id"] == REQUIRED_GROUP_ID), None)
    if required is None:
        required = {"id": REQUIRED_GROUP_ID, "name": "必起", "programs": []}
    required["name"] = "必起"
    clean_groups = [required] + [g for g in clean_groups if g["id"] != REQUIRED_GROUP_ID]
    if len(clean_groups) == 1:
        clean_groups.append({"id": new_id(), "name": "默认", "programs": []})
    version = data.get("version", 1)
    theme = data.get("theme") if data.get("theme") in {"auto", "light", "dark"} else "light"
    if version < 2 and theme == "auto":
        theme = "light"
    group_ids = {g["id"] for g in clean_groups}
    last_group_id = str(data.get("last_group_id") or "")
    if last_group_id not in group_ids:
        last_group_id = clean_groups[1]["id"] if len(clean_groups) > 1 else REQUIRED_GROUP_ID
    return {
        "version": 2,
        "theme": theme,
        "last_group_id": last_group_id,
        "window_geometry": str(data.get("window_geometry") or ""),
        "groups": clean_groups,
    }


def load_config() -> tuple[dict, str]:
    path = config_path()
    if not path.exists():
        return default_config(), ""
    try:
        with path.open("r", encoding="utf-8") as file:
            return normalize_config(json.load(file)), ""
    except (OSError, ValueError) as exc:
        backup = path.with_name(f"config.invalid-{datetime.now():%Y%m%d-%H%M%S}.json")
        try:
            path.replace(backup)
            detail = f"配置损坏，已备份到 {backup.name}：{exc}"
        except OSError:
            detail = f"配置读取失败：{exc}"
        return default_config(), detail


def save_config(data: dict) -> None:
    path = config_path()
    temp_path = path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def launch_program(path: str, as_admin: bool) -> tuple[bool, str]:
    if not os.path.isfile(path):
        return False, "文件不存在"
    verb = "runas" if as_admin else "open"
    workdir = os.path.dirname(path)
    try:
        result = ctypes.windll.shell32.ShellExecuteW(None, verb, path, None, workdir, 1)
    except Exception as exc:  # pragma: no cover - depends on Windows shell state
        return False, str(exc)
    if result <= 32:
        messages = {
            2: "文件不存在",
            5: "拒绝访问或取消了管理员授权",
            8: "内存不足",
            26: "共享冲突",
            27: "文件关联不完整",
            31: "没有可用的文件关联",
        }
        return False, messages.get(result, f"Windows 启动错误 {result}")
    return True, ""


class ProgramTree(QTreeWidget):
    filesDropped = Signal(list)
    orderChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.model().rowsMoved.connect(lambda *_: QTimer.singleShot(0, self.orderChanged.emit))

    @staticmethod
    def _local_files(mime_data: QMimeData) -> list[str]:
        return [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and self._local_files(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasUrls():
            files = self._local_files(event.mimeData())
            if files:
                self.filesDropped.emit(files)
                event.acceptProposedAction()
            return
        super().dropEvent(event)


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data, load_warning = load_config()
        self._theme = ""
        self._rebuilding_tabs = False
        self._rebuilding_tree = False
        self._file_icon_provider = QFileIconProvider()

        self.setWindowTitle(APP_NAME)
        icon_file = resource_path("app.ico")
        if os.path.exists(icon_file):
            self.setWindowIcon(QIcon(icon_file))
        self.setMinimumSize(780, 580)
        self.resize(940, 700)
        self.setFont(QFont("Microsoft YaHei", 10))

        self._build_ui()
        self._restore_state()
        self._apply_theme(self._resolved_theme(), persist=False)
        self._refresh_tabs(select_id=self.data["last_group_id"])

        self._theme_timer = QTimer(self)
        self._theme_timer.timeout.connect(self._check_auto_theme)
        self._theme_timer.start(60_000)
        if load_warning:
            QTimer.singleShot(0, lambda: self._log(load_warning, error=True))

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("workspace")
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(214)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 20, 18, 18)
        side.setSpacing(10)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_title = QLabel("APP LAUNCHER")
        brand_title.setObjectName("brandTitle")
        brand_sub = QLabel("HS DESKTOP")
        brand_sub.setObjectName("brandSub")
        brand_text.addWidget(brand_title)
        brand_text.addWidget(brand_sub)
        side.addLayout(brand_text)
        side.addSpacing(16)

        scenes_header = QHBoxLayout()
        scene_label = QLabel("启动场景")
        scene_label.setObjectName("sectionLabel")
        scenes_header.addWidget(scene_label)
        scenes_header.addStretch()
        add_scene = QPushButton("+")
        add_scene.setObjectName("addSceneBtn")
        add_scene.setToolTip("新增场景")
        add_scene.setFixedSize(28, 28)
        add_scene.clicked.connect(self._add_group)
        scenes_header.addWidget(add_scene)
        side.addLayout(scenes_header)

        self.tabs = QListWidget()
        self.tabs.setObjectName("sceneList")
        self.tabs.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabs.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tabs.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.currentRowChanged.connect(self._on_tab_changed)
        self.tabs.model().rowsMoved.connect(self._on_scene_rows_moved)
        self.tabs.customContextMenuRequested.connect(self._tab_context_menu)
        side.addWidget(self.tabs, 1)

        appearance = QLabel("外观")
        appearance.setObjectName("sectionLabel")
        side.addWidget(appearance)
        theme_row = QHBoxLayout()
        self.auto_theme = QCheckBox("自动")
        self.auto_theme.setChecked(self.data["theme"] == "auto")
        self.auto_theme.toggled.connect(self._toggle_auto_theme)
        theme_row.addWidget(self.auto_theme)
        theme_row.addStretch()
        self.light_btn = self._button("亮", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton))
        self.dark_btn = self._button("暗", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogNoButton))
        for button, theme in ((self.light_btn, "light"), (self.dark_btn, "dark")):
            button.setObjectName("themeBtn")
            button.setFixedSize(42, 28)
            button.clicked.connect(lambda _checked=False, value=theme: self._select_theme(value))
            theme_row.addWidget(button)
        side.addLayout(theme_row)
        side.addSpacing(4)
        config_folder = self._button(
            "打开配置文件夹",
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
        )
        config_folder.setObjectName("configFolderBtn")
        config_folder.setToolTip(str(config_path().parent))
        config_folder.clicked.connect(self._open_config_folder)
        side.addWidget(config_folder)
        shell.addWidget(sidebar)

        content = QWidget()
        content.setObjectName("workspace")
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 22, 24, 20)
        main.setSpacing(12)

        page_header = QHBoxLayout()
        page_text = QVBoxLayout()
        page_text.setSpacing(2)
        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("pageSub")
        page_text.addWidget(self.page_title)
        page_text.addWidget(self.page_subtitle)
        page_header.addLayout(page_text)
        page_header.addStretch()
        self.group_label = QLabel()
        self.group_label.setObjectName("countLabel")
        page_header.addWidget(self.group_label)
        main.addLayout(page_header)

        toolbar = QHBoxLayout()
        add_program = QPushButton("添加程序")
        add_program.setObjectName("addProgramBtn")
        add_program.clicked.connect(self._browse_programs)
        toolbar.addWidget(add_program)
        toolbar.addSpacing(4)
        self.delete_program = self._button("", self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.delete_program.setObjectName("deleteBtn")
        self.delete_program.setToolTip("删除选中的程序")
        self.delete_program.setFixedSize(34, 34)
        self.delete_program.clicked.connect(self._remove_selected_programs)
        toolbar.addWidget(self.delete_program)
        self.up_program = self._button("", self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.up_program.setObjectName("toolBtn")
        self.up_program.setToolTip("上移")
        self.up_program.setFixedSize(34, 34)
        self.up_program.clicked.connect(lambda: self._move_program(-1))
        toolbar.addWidget(self.up_program)
        self.down_program = self._button("", self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.down_program.setObjectName("toolBtn")
        self.down_program.setToolTip("下移")
        self.down_program.setFixedSize(34, 34)
        self.down_program.clicked.connect(lambda: self._move_program(1))
        toolbar.addWidget(self.down_program)
        toolbar.addStretch()
        main.addLayout(toolbar)

        self.program_tree = ProgramTree()
        self.program_tree.setHeaderLabels(["启用", "程序", "路径", "管理员"])
        self.program_tree.setAlternatingRowColors(True)
        self.program_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.program_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.program_tree.setColumnWidth(0, 62)
        self.program_tree.setColumnWidth(1, 190)
        self.program_tree.setColumnWidth(2, 490)
        self.program_tree.setColumnWidth(3, 76)
        self.program_tree.header().setStretchLastSection(False)
        self.program_tree.header().setSectionResizeMode(2, self.program_tree.header().ResizeMode.Stretch)
        self.program_tree.filesDropped.connect(self._add_program_paths)
        self.program_tree.orderChanged.connect(self._sync_program_order)
        self.program_tree.itemChanged.connect(self._on_program_changed)
        self.program_tree.customContextMenuRequested.connect(self._program_context_menu)
        self.program_tree.itemDoubleClicked.connect(self._open_program_location)
        self.program_tree.itemSelectionChanged.connect(self._update_program_actions)
        main.addWidget(self.program_tree, 1)

        log_header = QHBoxLayout()
        log_title = QLabel("最近活动")
        log_title.setObjectName("sectionLabel")
        log_header.addWidget(log_title)
        log_header.addStretch()
        clear_log = self._button("", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        clear_log.setObjectName("toolBtn")
        clear_log.setToolTip("清空日志")
        clear_log.setFixedSize(30, 28)
        clear_log.clicked.connect(lambda: self.log_output.clear())
        log_header.addWidget(clear_log)
        main.addLayout(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        self.log_output.setMaximumHeight(120)
        main.addWidget(self.log_output)

        launch_bar = QFrame()
        launch_bar.setObjectName("launchBar")
        launch_row = QHBoxLayout(launch_bar)
        launch_row.setContentsMargins(16, 11, 12, 11)
        launch_text = QVBoxLayout()
        launch_text.setSpacing(1)
        launch_title = QLabel("准备启动")
        launch_title.setObjectName("launchTitle")
        self.launch_summary = QLabel()
        self.launch_summary.setObjectName("launchSummary")
        launch_text.addWidget(launch_title)
        launch_text.addWidget(self.launch_summary)
        launch_row.addLayout(launch_text)
        launch_row.addStretch()
        self.launch_btn = QPushButton("启动当前场景")
        self.launch_btn.setObjectName("launchBtn")
        self.launch_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.launch_btn.setIconSize(QSize(20, 20))
        self.launch_btn.setMinimumWidth(190)
        self.launch_btn.clicked.connect(self._launch_current_group)
        launch_row.addWidget(self.launch_btn)
        main.addWidget(launch_bar)
        shell.addWidget(content, 1)

    @staticmethod
    def _button(text: str, icon: QIcon) -> QPushButton:
        button = QPushButton(text)
        button.setIcon(icon)
        button.setIconSize(QSize(16, 16))
        return button

    def _restore_state(self) -> None:
        encoded = self.data.get("window_geometry", "")
        if encoded:
            try:
                self.restoreGeometry(QByteArray.fromBase64(encoded.encode("ascii")))
            except Exception:
                pass

    def _save(self) -> None:
        try:
            save_config(self.data)
        except OSError as exc:
            self._log(f"保存配置失败：{exc}", error=True)

    def _group(self, group_id: str | None = None) -> dict:
        target = group_id or self._current_group_id()
        return next((g for g in self.data["groups"] if g["id"] == target), self.data["groups"][0])

    def _current_group_id(self) -> str:
        item = self.tabs.currentItem()
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        return str(value or REQUIRED_GROUP_ID)

    def _refresh_tabs(self, select_id: str | None = None) -> None:
        target = select_id or self._current_group_id()
        self._rebuilding_tabs = True
        self.tabs.clear()
        selected_index = 0
        for index, group in enumerate(self.data["groups"]):
            label = f"  {group['name']}"
            if group["id"] == REQUIRED_GROUP_ID:
                label = f"★  {group['name']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, group["id"])
            item.setToolTip("每次启动都会包含此场景" if group["id"] == REQUIRED_GROUP_ID else group["name"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
            self.tabs.addItem(item)
            if group["id"] == target:
                selected_index = index
        self.tabs.setCurrentRow(selected_index)
        self._rebuilding_tabs = False
        self._refresh_programs()

    def _on_tab_changed(self, _index: int) -> None:
        if self._rebuilding_tabs:
            return
        self.data["last_group_id"] = self._current_group_id()
        self._save()
        self._refresh_programs()

    def _on_scene_rows_moved(self, *_args) -> None:
        if self._rebuilding_tabs:
            return
        QTimer.singleShot(0, self._sync_group_order)

    def _sync_group_order(self) -> None:
        current_id = self._current_group_id()
        ordered_ids = [
            str(self.tabs.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self.tabs.count())
        ]
        if not ordered_ids or ordered_ids[0] != REQUIRED_GROUP_ID:
            self._refresh_tabs(current_id)
            return
        mapping = {group["id"]: group for group in self.data["groups"]}
        if set(ordered_ids) == set(mapping):
            self.data["groups"] = [mapping[group_id] for group_id in ordered_ids]
            self._save()

    def _tab_context_menu(self, point) -> None:
        index = self.tabs.indexAt(point).row()
        if index < 0:
            return
        group_id = str(self.tabs.item(index).data(Qt.ItemDataRole.UserRole))
        is_required = group_id == REQUIRED_GROUP_ID
        menu = QMenu(self)
        rename = menu.addAction("改名")
        duplicate = menu.addAction("复制场景")
        menu.addSeparator()
        move_left = menu.addAction("上移")
        move_right = menu.addAction("下移")
        menu.addSeparator()
        delete = menu.addAction("删除场景")
        rename.setEnabled(not is_required)
        delete.setEnabled(not is_required)
        move_left.setEnabled(not is_required and index > 1)
        move_right.setEnabled(not is_required and index < self.tabs.count() - 1)
        action = menu.exec(self.tabs.viewport().mapToGlobal(point))
        if action == rename:
            self._rename_group(group_id)
        elif action == duplicate:
            self._duplicate_group(group_id)
        elif action == move_left:
            self._move_group(group_id, -1)
        elif action == move_right:
            self._move_group(group_id, 1)
        elif action == delete:
            self._delete_group(group_id)

    def _unique_group_name(self, base: str) -> str:
        names = {g["name"] for g in self.data["groups"]}
        if base not in names:
            return base
        number = 2
        while f"{base} {number}" in names:
            number += 1
        return f"{base} {number}"

    def _add_group(self) -> None:
        name, accepted = QInputDialog.getText(self, "新增场景", "场景名称：")
        name = name.strip()
        if not accepted or not name:
            return
        group = {"id": new_id(), "name": self._unique_group_name(name), "programs": []}
        self.data["groups"].append(group)
        self._save()
        self._refresh_tabs(group["id"])

    def _rename_group(self, group_id: str) -> None:
        group = self._group(group_id)
        name, accepted = QInputDialog.getText(self, "场景改名", "新名称：", text=group["name"])
        name = name.strip()
        if not accepted or not name or name == group["name"]:
            return
        group["name"] = self._unique_group_name(name)
        self._save()
        self._refresh_tabs(group_id)

    def _duplicate_group(self, group_id: str) -> None:
        source = self._group(group_id)
        copied = {
            "id": new_id(),
            "name": self._unique_group_name(f"{source['name']} 副本"),
            "programs": [{**program, "id": new_id()} for program in source["programs"]],
        }
        source_index = self.data["groups"].index(source)
        self.data["groups"].insert(source_index + 1, copied)
        self._save()
        self._refresh_tabs(copied["id"])

    def _delete_group(self, group_id: str) -> None:
        group = self._group(group_id)
        answer = QMessageBox.question(
            self,
            "删除场景",
            f"确定删除“{group['name']}”及其中的 {len(group['programs'])} 个程序吗？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        index = self.data["groups"].index(group)
        self.data["groups"].remove(group)
        next_index = min(index, len(self.data["groups"]) - 1)
        next_id = self.data["groups"][next_index]["id"]
        self.data["last_group_id"] = next_id
        self._save()
        self._refresh_tabs(next_id)

    def _move_group(self, group_id: str, offset: int) -> None:
        group = self._group(group_id)
        old_index = self.data["groups"].index(group)
        new_index = max(1, min(len(self.data["groups"]) - 1, old_index + offset))
        if old_index == new_index:
            return
        self.data["groups"].pop(old_index)
        self.data["groups"].insert(new_index, group)
        self._save()
        self._refresh_tabs(group_id)

    def _refresh_programs(self) -> None:
        group = self._group()
        self._rebuilding_tree = True
        self.program_tree.clear()
        for program in group["programs"]:
            item = QTreeWidgetItem()
            item.setData(0, Qt.ItemDataRole.UserRole, program["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled)
            item.setCheckState(0, Qt.CheckState.Checked if program["enabled"] else Qt.CheckState.Unchecked)
            item.setText(1, program["name"])
            item.setToolTip(1, program["name"])
            item.setText(2, program["path"])
            item.setToolTip(2, program["path"])
            item.setCheckState(3, Qt.CheckState.Checked if program["admin"] else Qt.CheckState.Unchecked)
            item.setTextAlignment(0, Qt.AlignmentFlag.AlignCenter)
            item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
            item.setIcon(1, self._file_icon_provider.icon(QFileInfo(program["path"])))
            if not os.path.isfile(program["path"]):
                item.setForeground(1, QColor("#dc2626" if self._theme == "light" else "#f87171"))
                item.setToolTip(1, "文件不存在")
            self.program_tree.addTopLevelItem(item)
        self._rebuilding_tree = False
        self._update_counts()
        self._update_program_actions()

    def _browse_programs(self) -> None:
        paths, _filter = QFileDialog.getOpenFileNames(
            self,
            "选择程序或快捷方式",
            "",
            "可启动文件 (*.exe *.lnk *.bat *.cmd *.com *.url *.msc);;所有文件 (*.*)",
        )
        if paths:
            self._add_program_paths(paths)

    def _add_program_paths(self, paths: list[str]) -> None:
        group = self._group()
        existing = {os.path.normcase(os.path.abspath(p["path"])) for p in group["programs"]}
        added = 0
        skipped = []
        for raw_path in paths:
            path = os.path.abspath(raw_path)
            if not os.path.isfile(path):
                skipped.append(f"{raw_path}（不是文件）")
                continue
            if Path(path).suffix.lower() not in SUPPORTED_EXTENSIONS:
                skipped.append(f"{Path(path).name}（不支持的类型）")
                continue
            key = os.path.normcase(path)
            if key in existing:
                skipped.append(f"{Path(path).name}（已存在）")
                continue
            group["programs"].append(
                {"id": new_id(), "name": Path(path).stem, "path": path, "admin": False, "enabled": True}
            )
            existing.add(key)
            added += 1
        if added:
            self._save()
            self._refresh_programs()
            self._log(f"已向“{group['name']}”添加 {added} 个程序")
        for detail in skipped:
            self._log(f"已跳过：{detail}", error=True)

    def _program_by_id(self, program_id: str) -> dict | None:
        return next((p for p in self._group()["programs"] if p["id"] == program_id), None)

    def _on_program_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._rebuilding_tree or column not in {0, 3}:
            return
        program = self._program_by_id(str(item.data(0, Qt.ItemDataRole.UserRole)))
        if not program:
            return
        program["enabled"] = item.checkState(0) == Qt.CheckState.Checked
        program["admin"] = item.checkState(3) == Qt.CheckState.Checked
        self._save()
        self._update_counts()

    def _selected_program_ids(self) -> list[str]:
        return [str(item.data(0, Qt.ItemDataRole.UserRole)) for item in self.program_tree.selectedItems()]

    def _remove_selected_programs(self) -> None:
        selected_ids = set(self._selected_program_ids())
        if not selected_ids:
            return
        group = self._group()
        group["programs"] = [p for p in group["programs"] if p["id"] not in selected_ids]
        self._save()
        self._refresh_programs()

    def _sync_program_order(self) -> None:
        if self._rebuilding_tree:
            return
        group = self._group()
        mapping = {program["id"]: program for program in group["programs"]}
        ordered = []
        for index in range(self.program_tree.topLevelItemCount()):
            program_id = str(self.program_tree.topLevelItem(index).data(0, Qt.ItemDataRole.UserRole))
            if program_id in mapping:
                ordered.append(mapping[program_id])
        if len(ordered) == len(group["programs"]):
            group["programs"] = ordered
            self._save()

    def _move_program(self, offset: int) -> None:
        selected = self.program_tree.selectedItems()
        if len(selected) != 1:
            return
        item = selected[0]
        old_index = self.program_tree.indexOfTopLevelItem(item)
        new_index = max(0, min(self.program_tree.topLevelItemCount() - 1, old_index + offset))
        if old_index == new_index:
            return
        self.program_tree.takeTopLevelItem(old_index)
        self.program_tree.insertTopLevelItem(new_index, item)
        self.program_tree.setCurrentItem(item)
        self._sync_program_order()
        self._update_program_actions()

    def _rename_program(self) -> None:
        selected = self.program_tree.selectedItems()
        if len(selected) != 1:
            return
        item = selected[0]
        program = self._program_by_id(str(item.data(0, Qt.ItemDataRole.UserRole)))
        if not program:
            return
        name, accepted = QInputDialog.getText(self, "程序改名", "显示名称：", text=program["name"])
        name = name.strip()
        if accepted and name:
            program["name"] = name
            self._save()
            self._refresh_programs()

    def _open_program_location(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        program = self._program_by_id(str(item.data(0, Qt.ItemDataRole.UserRole)))
        if not program or not os.path.exists(program["path"]):
            self._log("无法打开位置：文件不存在", error=True)
            return
        try:
            os.spawnl(os.P_NOWAIT, os.path.join(os.environ["WINDIR"], "explorer.exe"), "explorer.exe", "/select,", program["path"])
        except OSError as exc:
            self._log(f"打开文件位置失败：{exc}", error=True)

    def _open_config_folder(self) -> None:
        folder = config_path().parent
        try:
            os.startfile(str(folder))
            self._log(f"已打开配置文件夹：{folder}")
        except OSError as exc:
            self._log(f"打开配置文件夹失败：{exc}", error=True)

    def _program_context_menu(self, point) -> None:
        item = self.program_tree.itemAt(point)
        if item and not item.isSelected():
            self.program_tree.setCurrentItem(item)
        menu = QMenu(self)
        rename = menu.addAction("修改显示名称")
        open_location = menu.addAction("打开文件位置")
        menu.addSeparator()
        remove = menu.addAction("删除")
        count = len(self.program_tree.selectedItems())
        rename.setEnabled(count == 1)
        open_location.setEnabled(count == 1)
        remove.setEnabled(count > 0)
        action = menu.exec(self.program_tree.viewport().mapToGlobal(point))
        if action == rename:
            self._rename_program()
        elif action == open_location and item:
            self._open_program_location(item)
        elif action == remove:
            self._remove_selected_programs()

    def _update_program_actions(self) -> None:
        selected = self.program_tree.selectedItems()
        self.delete_program.setEnabled(bool(selected))
        one = len(selected) == 1
        if one:
            row = self.program_tree.indexOfTopLevelItem(selected[0])
            self.up_program.setEnabled(row > 0)
            self.down_program.setEnabled(row < self.program_tree.topLevelItemCount() - 1)
        else:
            self.up_program.setEnabled(False)
            self.down_program.setEnabled(False)

    def _programs_to_launch(self) -> list[dict]:
        current_id = self._current_group_id()
        source_groups = [self._group(REQUIRED_GROUP_ID)]
        if current_id != REQUIRED_GROUP_ID:
            source_groups.append(self._group(current_id))
        result = []
        seen = set()
        for group in source_groups:
            for program in group["programs"]:
                key = os.path.normcase(os.path.abspath(program["path"]))
                if program["enabled"] and key not in seen:
                    result.append(program)
                    seen.add(key)
        return result

    def _launch_current_group(self) -> None:
        programs = self._programs_to_launch()
        group = self._group()
        if not programs:
            self._log(f"“{group['name']}”没有已启用的程序", error=True)
            return
        self.launch_btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        success = 0
        try:
            self._log(f"开始启动“{group['name']}”，共 {len(programs)} 个程序")
            for program in programs:
                ok, error = launch_program(program["path"], program["admin"])
                if ok:
                    success += 1
                    suffix = "（管理员）" if program["admin"] else ""
                    self._log(f"成功：{program['name']}{suffix}")
                else:
                    self._log(f"失败：{program['name']} - {error}", error=True)
            self._log(f"启动完成：成功 {success}，失败 {len(programs) - success}")
        finally:
            QApplication.restoreOverrideCursor()
            self.launch_btn.setEnabled(True)

    def _update_counts(self) -> None:
        group = self._group()
        enabled = sum(1 for p in group["programs"] if p["enabled"])
        self.page_title.setText(group["name"])
        self.page_subtitle.setText(
            "无论选择哪个场景都会启动这些程序"
            if group["id"] == REQUIRED_GROUP_ID
            else "管理此场景需要一并启动的程序"
        )
        self.group_label.setText(f"{len(group['programs'])} 个程序")
        total = len(self._programs_to_launch())
        if group["id"] == REQUIRED_GROUP_ID:
            self.launch_summary.setText(f"本次将启动 {enabled} 个已启用程序")
        else:
            required_enabled = sum(1 for p in self._group(REQUIRED_GROUP_ID)["programs"] if p["enabled"])
            self.launch_summary.setText(f"当前 {enabled} + 必起 {required_enabled}，去重后共 {total} 个")

    def _log(self, message: str, error: bool = False) -> None:
        color = "#dc2626" if error else ("#059669" if self._theme == "light" else "#34d399")
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f'<span style="color:#64748b">[{stamp}]</span> <span style="color:{color}">{message}</span>')

    @staticmethod
    def _resolved_auto_theme() -> str:
        return "light" if 8 <= datetime.now().hour < 20 else "dark"

    def _resolved_theme(self) -> str:
        value = self.data.get("theme", "auto")
        return self._resolved_auto_theme() if value == "auto" else value

    def _select_theme(self, theme: str) -> None:
        self.auto_theme.blockSignals(True)
        self.auto_theme.setChecked(False)
        self.auto_theme.blockSignals(False)
        self.data["theme"] = theme
        self._apply_theme(theme)

    def _toggle_auto_theme(self, checked: bool) -> None:
        if checked:
            self.data["theme"] = "auto"
            self._apply_theme(self._resolved_auto_theme())
        else:
            self.data["theme"] = self._theme or self._resolved_auto_theme()
            self._save()

    def _check_auto_theme(self) -> None:
        if self.data.get("theme") == "auto":
            target = self._resolved_auto_theme()
            if target != self._theme:
                self._apply_theme(target, persist=False)

    def _apply_theme(self, theme: str, persist: bool = True) -> None:
        self._theme = theme
        QApplication.instance().setStyleSheet(LIGHT_QSS if theme == "light" else DARK_QSS)
        for button, value in ((self.light_btn, "light"), (self.dark_btn, "dark")):
            button.setProperty("active", value == theme)
            button.style().unpolish(button)
            button.style().polish(button)
        palette = self.program_tree.palette()
        highlight = QColor("#2563eb" if theme == "light" else "#06b6d4")
        highlighted_text = QColor("#ffffff" if theme == "light" else "#020617")
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
            palette.setColor(group, QPalette.ColorRole.Highlight, highlight)
            palette.setColor(group, QPalette.ColorRole.HighlightedText, highlighted_text)
        self.program_tree.setPalette(palette)
        if persist:
            self._save()
        if hasattr(self, "program_tree") and self.program_tree.topLevelItemCount():
            self._refresh_programs()

    def closeEvent(self, event) -> None:
        self.data["last_group_id"] = self._current_group_id()
        self.data["window_geometry"] = bytes(self.saveGeometry().toBase64()).decode("ascii")
        self._save()
        super().closeEvent(event)


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("HS")
    app.setWindowIcon(QIcon(resource_path("app.ico")))
    window = LauncherWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
