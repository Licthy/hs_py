"""
SVN Revert Tool — 按文件名模糊匹配，批量 revert + update
支持双击打开文件、右键删除
"""
import sys
import os
import json
import subprocess
import shutil
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect, QSize, QPoint
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QFileDialog, QCheckBox, QMenu,
    QLayout, QStyledItemDelegate, QStyleOptionViewItem,
)

# ── DPI ──
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

# ── 默认目录 ──
DEFAULT_SVN_DIR = r"D:\SVN\zt\策划文档\Config\xlsx"

# ── Windows subprocess 不弹黑窗 ──
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# ── SVN 状态说明 ──
STATUS_LABEL = {
    "M": "修改", "A": "新增", "D": "删除", "!": "缺失",
    "?": "未版本控制", "C": "冲突", "~": "类型变更",
}


# ══════════════════════════════════════════════════
#  QSS 主题
# ══════════════════════════════════════════════════

LIGHT_QSS = """
QWidget { background: #ffffff; color: #1a1a2e; }
QMainWindow { background: #ffffff; }
QPushButton {
    background: #ffffff; color: #2563eb;
    border: 1.5px solid #d1d5db; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}
QPushButton:hover { background: #f8fafc; border-color: #2563eb; }
QPushButton:pressed { background: #e5e7eb; }
QPushButton:disabled { background: #f3f4f6; color: #9ca3af; border-color: #e5e5e5; }
QPushButton#searchBtn { background: #2563eb; color: #ffffff; border: none; font-weight: 700; }
QPushButton#searchBtn:hover { background: #1d4ed8; }
QPushButton#searchBtn:disabled { background: #93c5fd; }
QPushButton#revertBtn {
    background: #059669; color: #ffffff; border: none;
    border-radius: 6px; padding: 4px 16px; font-weight: 600;
}
QPushButton#revertBtn:hover { background: #047857; }
QPushButton#revertBtn:disabled { background: #6ee7b7; color: #ffffff; }
QPushButton#deleteBtn {
    background: #ffffff; color: #dc2626;
    border: 1.5px solid #fca5a5; border-radius: 6px;
    padding: 4px 16px; font-weight: 600;
}
QPushButton#deleteBtn:hover { background: #fef2f2; border-color: #dc2626; }
QPushButton#themeBtn {
    background: #ffffff; color: #6b7280;
    border: 1px solid #e5e5e5; border-radius: 6px;
    padding: 6px 14px; font-weight: 600; font-size: 12px;
}
QPushButton#themeBtn:hover { background: #f3f4f6; border-color: #2563eb; color: #2563eb; }
QPushButton#themeBtn[active="true"] { background: #2563eb; color: #ffffff; border-color: #2563eb; }
QPushButton#actionBtn {
    padding: 4px 12px;
    border: 1.5px solid #d1d5db; border-radius: 6px;
}
QCheckBox { color: #6b7280; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1.5px solid #d1d5db; border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { background: #2563eb; border-color: #2563eb; }
QLineEdit {
    background: #f9fafb; border: 1.5px solid #e5e5e5; border-radius: 8px;
    padding: 8px 12px; color: #111827;
}
QLineEdit:focus { border-color: #2563eb; background: #ffffff; }
QListWidget {
    background: #f9fafb; border: 1.5px solid #e5e5e5; border-radius: 8px;
    padding: 4px; color: #111827;
}
QListWidget::item { background: transparent; padding: 5px 10px; border-radius: 3px; min-height: 22px; }
QListWidget::item:hover { background: #e5e7eb; }
QListWidget::item:selected, QListWidget::item:selected:!active {
    background: #2563eb; color: #ffffff;
}
QTextEdit {
    background: #f9fafb; border: 1.5px solid #e5e5e5; border-radius: 8px;
    padding: 10px; color: #374151;
}
QLabel#countLabel { color: #2563eb; font-weight: 600; }
QScrollBar:vertical { background: #ffffff; width: 6px; }
QScrollBar::handle:vertical { background: #d1d5db; border-radius: 3px; min-height: 20px; }
QMenu { background: #ffffff; border: 1px solid #e5e5e5; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 16px; border-radius: 4px; }
QMenu::item:selected { background: #2563eb; color: #ffffff; }
"""

DARK_QSS = """
QWidget { background: #020617; color: #cbd5e1; }
QMainWindow { background: #020617; }
QPushButton {
    background: #0f172a; color: #38bdf8;
    border: 1px solid #1e293b; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}
QPushButton:hover { background: #1e293b; border-color: #38bdf8; }
QPushButton:pressed { background: #334155; }
QPushButton:disabled { background: #0f172a; color: #475569; border-color: #1e293b; }
QPushButton#searchBtn { background: #06b6d4; color: #020617; border: none; font-weight: 700; }
QPushButton#searchBtn:hover { background: #22d3ee; }
QPushButton#searchBtn:disabled { background: #164e63; color: #475569; }
QPushButton#revertBtn {
    background: #10b981; color: #020617; border: none;
    border-radius: 6px; padding: 4px 16px; font-weight: 600;
}
QPushButton#revertBtn:hover { background: #34d399; }
QPushButton#revertBtn:disabled { background: #064e3b; color: #475569; }
QPushButton#deleteBtn {
    background: #0f172a; color: #f87171;
    border: 1px solid #7f1d1d; border-radius: 6px;
    padding: 4px 16px; font-weight: 600;
}
QPushButton#deleteBtn:hover { background: #1e0a0a; border-color: #f87171; }
QPushButton#themeBtn {
    background: #0f172a; color: #64748b;
    border: 1px solid #1e293b; border-radius: 6px;
    padding: 6px 14px; font-weight: 600; font-size: 12px;
}
QPushButton#themeBtn:hover { background: #1e293b; border-color: #38bdf8; color: #38bdf8; }
QPushButton#themeBtn[active="true"] { background: #06b6d4; color: #020617; border-color: #06b6d4; }
QPushButton#actionBtn {
    padding: 4px 12px;
    border: 1px solid #334155; border-radius: 6px;
}
QCheckBox { color: #94a3b8; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #334155; border-radius: 4px; background: #0f172a; }
QCheckBox::indicator:checked { background: #06b6d4; border-color: #06b6d4; }
QLineEdit {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
    padding: 8px 12px; color: #e2e8f0;
}
QLineEdit:focus { border-color: #38bdf8; }
QListWidget {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
    padding: 4px; color: #e2e8f0;
}
QListWidget::item { background: transparent; padding: 5px 10px; border-radius: 3px; min-height: 22px; color: #e2e8f0; }
QListWidget::item:hover { background: #1e293b; color: #e2e8f0; }
QListWidget::item:selected, QListWidget::item:selected:!active {
    background: #06b6d4; color: #020617;
}
QTextEdit {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
    padding: 10px; color: #94a3b8;
}
QLabel#countLabel { color: #38bdf8; font-weight: 600; }
QScrollBar:vertical { background: #020617; width: 6px; }
QScrollBar::handle:vertical { background: #334155; border-radius: 3px; min-height: 20px; }
QMenu { background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 16px; border-radius: 4px; }
QMenu::item:selected { background: #06b6d4; color: #020617; }
"""

THEME_QSS = {"light": LIGHT_QSS, "dark": DARK_QSS}


def get_auto_theme():
    hour = datetime.now().hour
    return "light" if 8 <= hour < 20 else "dark"


# ══════════════════════════════════════════════════
#  后台线程
# ══════════════════════════════════════════════════

class ScanWorker(QThread):
    """合并本地文件列表 + svn status"""
    # result: [(status_char|None, filename, full_path, exists_locally), ...]
    result = Signal(list)
    error = Signal(str)

    def __init__(self, workdir):
        super().__init__()
        self.workdir = workdir

    def run(self):
        # 1) 获取本地存在的文件
        local_files = set()
        try:
            for entry in os.listdir(self.workdir):
                full = os.path.join(self.workdir, entry)
                if os.path.isfile(full):
                    local_files.add(entry)
        except OSError as e:
            self.error.emit(f"读取目录失败: {e}")
            return

        # 2) svn status 获取 SVN 状态
        svn_map = {}   # filename -> status_char
        try:
            r = subprocess.run(
                ["svn", "status"], cwd=self.workdir,
                capture_output=True, text=True, timeout=30,
                encoding="gbk", errors="replace",
                creationflags=_NO_WINDOW,
            )
            if r.returncode == 0:
                for line in r.stdout.strip().split("\n"):
                    if not line.strip() or len(line) < 9:
                        continue
                    sc = line[0]
                    fn = line[8:].strip()
                    if fn:
                        svn_map[fn] = sc
        except Exception as e:
            self.error.emit(f"svn status 异常: {e}")
            return

        # 3) 合并：本地文件 ∪ svn status 中的文件
        all_filenames = local_files | set(svn_map.keys())

        entries = []
        for fn in sorted(all_filenames):
            sc = svn_map.get(fn)        # None 表示本地有但 SVN 无变更记录
            full_path = os.path.join(self.workdir, fn)
            exists = fn in local_files
            entries.append((sc, fn, full_path, exists))

        self.result.emit(entries)


class SvnWorker(QThread):
    output_line = Signal(str)
    finished = Signal()

    def __init__(self, commands, workdir):
        super().__init__()
        self.commands = commands
        self.workdir = workdir

    def run(self):
        for label, args in self.commands:
            self.output_line.emit(f"[执行] {label}")
            try:
                r = subprocess.run(
                    args, cwd=self.workdir,
                    capture_output=True, text=True, timeout=120,
                    encoding="gbk", errors="replace",
                    creationflags=_NO_WINDOW,
                )
                for line in r.stdout.strip().split("\n"):
                    if line:
                        self.output_line.emit(f"  {line}")
                if r.stderr.strip():
                    for line in r.stderr.strip().split("\n"):
                        if line:
                            self.output_line.emit(f"  [stderr] {line}")
                self.output_line.emit(f"  {'完成' if r.returncode == 0 else f'返回码 {r.returncode}'}")
            except subprocess.TimeoutExpired:
                self.output_line.emit(f"  ⏱ 超时")
            except Exception as e:
                self.output_line.emit(f"  ❌ 错误: {e}")
        self.finished.emit()


class ExportWorker(QThread):
    """后台启动 BAT，弹出独立控制台窗口"""
    export_finished = Signal(int)

    def __init__(self, bat_path):
        super().__init__()
        self.bat_path = bat_path

    def run(self):
        workdir = os.path.dirname(self.bat_path)
        try:
            r = subprocess.Popen(
                [self.bat_path], cwd=workdir,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            ret = r.wait()
            self.export_finished.emit(ret)
        except Exception as e:
            self.export_finished.emit(-1)

# ══════════════════════════════════════════════════
#  流式布局（关键词 chips 换行支持）
# ══════════════════════════════════════════════════

class FlowLayout(QLayout):
    """自动换行的流式布局，用于关键词快捷按钮区"""

    def __init__(self, parent=None, margin=0, h_spacing=4, v_spacing=4):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        if margin >= 0:
            self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.count():
            self.takeAt(0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        line_height = 0
        right_edge = rect.right() - margins.right()

        for item in self._items:
            item_size = item.sizeHint()
            space_x = self._h_spacing
            space_y = self._v_spacing

            next_x = x + item_size.width() + space_x
            # 当前行放不下 → 换行
            if next_x - space_x > right_edge and line_height > 0:
                x = rect.x() + margins.left()
                y = y + line_height + space_y
                next_x = x + item_size.width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))

            x = next_x
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y() + margins.bottom()


# ══════════════════════════════════════════════════
#  自定义 Delegate — 绕过 QSS 绘制缺失文件底色
# ══════════════════════════════════════════════════

class FileListDelegate(QStyledItemDelegate):
    """自定义绘制底色：缺失文件红色，存在文件交替灰/白"""

    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self._app = app_ref

    def paint(self, painter, option, index):
        data = index.data(Qt.ItemDataRole.UserRole)
        is_light = (self._app._current_theme == "light")

        if data is not None and not data.get("exists", True):
            bg = QColor("#fef2f2") if is_light else QColor("#2d1111")
        else:
            alt_idx = data.get("alt_idx", 0) if data else 0
            if alt_idx % 2:
                bg = QColor("#f3f4f6") if is_light else QColor("#0c1222")
            else:
                bg = QColor("#f9fafb") if is_light else QColor("#0f172a")

        painter.save()
        painter.fillRect(option.rect, bg)
        painter.restore()

        opt = QStyleOptionViewItem(option)
        opt.showDecorationSelected = True
        super().paint(painter, opt, index)


class SvnRevertApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SVN Revert Tool")
        # 窗口图标（适配 PyInstaller 打包）
        import sys as _sys
        if getattr(_sys, 'frozen', False):
            icon_dir = _sys._MEIPASS
        else:
            icon_dir = os.path.dirname(__file__)
        icon_path = os.path.join(icon_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(760, 680)
        self.resize(860, 740)
        self.setFont(QFont("Microsoft YaHei", 10))

        self._current_theme = None
        self._auto_mode = True
        self._all_entries = []       # 缓存扫描结果 [(sc, fn, full_path, exists), ...]
        self._scanning = False       # 扫描进行中标志

        self._setup_ui()
        self._apply_initial_theme()

        self._theme_timer = QTimer(self)
        self._theme_timer.timeout.connect(self._check_auto_switch)
        self._theme_timer.start(60_000)

        # 关键词实时过滤 debounce
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._apply_filter)

        if os.path.isdir(DEFAULT_SVN_DIR):
            self.dir_input.setText(DEFAULT_SVN_DIR)
            # 启动后自动首次扫描
            QTimer.singleShot(150, self._on_search)

    # ── UI ──────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setSpacing(10)
        main.setContentsMargins(16, 12, 16, 12)

        # ── 顶部 ──
        top = QHBoxLayout()
        self._title_label = QLabel("SVN Revert Tool")
        self._title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        top.addWidget(self._title_label)
        top.addStretch()
        self._auto_check = QCheckBox("自动")
        self._auto_check.setChecked(True)
        self._auto_check.stateChanged.connect(self._toggle_auto)
        top.addWidget(self._auto_check)
        for name, icon in [("light", "☀"), ("dark", "🌙")]:
            btn = QPushButton(icon)
            btn.setObjectName("themeBtn")
            btn.setFixedSize(36, 28)
            btn.clicked.connect(lambda checked, t=name: self._switch_theme(t))
            top.addWidget(btn)
            setattr(self, f"_btn_{name}", btn)
        main.addLayout(top)

        # ── 目录 ──
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("SVN 目录:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("SVN 工作目录路径...")
        self.dir_input.returnPressed.connect(self._on_search)
        dir_row.addWidget(self.dir_input, 1)
        browse = QPushButton("浏览...")
        browse.clicked.connect(self._on_browse)
        dir_row.addWidget(browse)
        open_svn_dir = QPushButton("打开")
        open_svn_dir.setToolTip("在资源管理器中打开 SVN 目录")
        open_svn_dir.clicked.connect(lambda: self._open_dir(self.dir_input.text().strip(), "SVN 目录"))
        dir_row.addWidget(open_svn_dir)
        main.addLayout(dir_row)

        # ── 导表路径 ──
        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("导表BAT:"))
        self.export_path_input = QLineEdit()
        self.export_path_input.setPlaceholderText("export.bat 路径...")
        self.export_path_input.setText(r"D:\SVN\zt\策划文档\Config\export\export.bat")
        export_row.addWidget(self.export_path_input, 1)
        browse_export = QPushButton("浏览...")
        browse_export.clicked.connect(self._on_browse_export)
        export_row.addWidget(browse_export)
        open_export_dir = QPushButton("打开")
        open_export_dir.setToolTip("在资源管理器中打开导表 BAT 所在目录")
        open_export_dir.clicked.connect(lambda: self._open_dir(os.path.dirname(self.export_path_input.text().strip()), "导表目录"))
        export_row.addWidget(open_export_dir)
        main.addLayout(export_row)

        # ── 关键词 ──
        kw_row = QHBoxLayout()
        kw_row.addWidget(QLabel("关键词:"))
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText('文件名关键词，如 "通用"（留空显示全部）...')
        self.kw_input.textChanged.connect(self._on_kw_changed)
        self.kw_input.setClearButtonEnabled(True)
        kw_row.addWidget(self.kw_input, 1)
        self.search_btn = QPushButton("🔄 刷新")
        self.search_btn.setObjectName("searchBtn")
        self.search_btn.clicked.connect(self._on_search)
        kw_row.addWidget(self.search_btn)
        main.addLayout(kw_row)

        # ── 关键词快捷按钮 ──
        self._kw_chips_layout = FlowLayout(margin=0, h_spacing=4, v_spacing=2)
        self._kw_chips = []
        main.addLayout(self._kw_chips_layout)
        self._load_keywords()
        self._refresh_chips()

        # ── 选择按钮行 ──
        select_row = QHBoxLayout()
        for label, fn in [("全选", True), ("全不选", False), ("反选", None)]:
            btn = QPushButton(label)
            btn.setObjectName("actionBtn")
            btn.setFixedHeight(32)
            btn.setFixedWidth(100)
            if fn is None:
                btn.clicked.connect(self._on_invert)
            else:
                btn.clicked.connect(lambda checked, v=fn: self._set_all_checked(v))
            select_row.addWidget(btn)
        select_row.addStretch()
        self._count_label = QLabel("文件: 0")
        self._count_label.setObjectName("countLabel")
        select_row.addWidget(self._count_label)
        main.addLayout(select_row)

        # ── 操作按钮行 ──
        action_row = QHBoxLayout()
        self.revert_btn = QPushButton("SVN Revert + Update")
        self.revert_btn.setObjectName("actionBtn")
        self.revert_btn.setFixedHeight(32)
        self.revert_btn.setStyleSheet("QPushButton { background: #059669; color: #ffffff; border-color: #059669; } QPushButton:hover { background: #047857; } QPushButton:disabled { background: #6ee7b7; }")
        self.revert_btn.clicked.connect(self._on_revert)
        action_row.addWidget(self.revert_btn)

        self.commit_btn = QPushButton("SVN 提交")
        self.commit_btn.setObjectName("actionBtn")
        self.commit_btn.setFixedHeight(32)
        self.commit_btn.setStyleSheet("QPushButton { background: #d97706; color: #ffffff; border-color: #d97706; } QPushButton:hover { background: #b45309; } QPushButton:disabled { background: #fcd34d; }")
        self.commit_btn.clicked.connect(self._on_commit)
        action_row.addWidget(self.commit_btn)

        self.export_btn = QPushButton("导表")
        self.export_btn.setObjectName("actionBtn")
        self.export_btn.setFixedHeight(32)
        self.export_btn.setStyleSheet("QPushButton { background: #7c3aed; color: #ffffff; border-color: #7c3aed; } QPushButton:hover { background: #6d28d9; }")
        self.export_btn.clicked.connect(self._on_export)
        action_row.addWidget(self.export_btn)

        action_row.addStretch()

        self.delete_btn = QPushButton("删除选中文件")
        self.delete_btn.setObjectName("actionBtn")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.setStyleSheet("QPushButton { color: #dc2626; border-color: #fca5a5; } QPushButton:hover { background: #fef2f2; border-color: #dc2626; }")
        self.delete_btn.clicked.connect(self._on_delete)
        action_row.addWidget(self.delete_btn)
        main.addLayout(action_row)
        self.file_list = QListWidget()
        self.file_list.setItemDelegate(FileListDelegate(self))
        # QPalette 保证失焦时选中项也保持高亮
        self._file_list_palette = self.file_list.palette()
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._on_context_menu)
        self.file_list.itemDoubleClicked.connect(self._on_double_click)
        self.file_list.itemClicked.connect(self._on_item_clicked)
        main.addWidget(self.file_list, 1)

        # ── 日志 ──
        self._log_label = QLabel("执行日志:")
        main.addWidget(self._log_label)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        self.log_output.setMinimumHeight(110)
        main.addWidget(self.log_output)

    # ── 主题 ────────────────────────────────────────

    def _apply_initial_theme(self):
        theme = get_auto_theme() if self._auto_mode else "light"
        self._current_theme = theme
        app = QApplication.instance()
        if app:
            app.setStyleSheet(THEME_QSS[theme])
        self._update_theme_buttons()
        self._update_inline_styles()
        self._update_file_list_palette(theme)

    def _check_auto_switch(self):
        if not self._auto_mode:
            return
        target = get_auto_theme()
        if self._current_theme != target:
            self._switch_theme(target)

    def _switch_theme(self, theme):
        if self._current_theme == theme:
            return
        self._current_theme = theme
        app = QApplication.instance()
        if app:
            app.setStyleSheet(THEME_QSS[theme])
        self._update_theme_buttons()
        self._update_inline_styles()
        self._update_file_list_palette(theme)
        self.file_list.viewport().update()
        self._refresh_chips()

    def _update_theme_buttons(self):
        for name in ("light", "dark"):
            btn = getattr(self, f"_btn_{name}")
            active = (name == self._current_theme)
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_inline_styles(self):
        title_c = "#2563eb" if self._current_theme == "light" else "#38bdf8"
        sub_c = "#6b7280" if self._current_theme == "light" else "#64748b"
        self._title_label.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {title_c};")
        self._log_label.setStyleSheet(f"color: {sub_c};")

    def _update_file_list_palette(self, theme):
        """QPalette 保证失焦时选中项也保持主题高亮"""
        if theme == "light":
            hl, hl_text = QColor("#2563eb"), QColor("#ffffff")
        else:
            hl, hl_text = QColor("#06b6d4"), QColor("#020617")
        p = self._file_list_palette
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
            p.setColor(group, QPalette.ColorRole.Highlight, hl)
            p.setColor(group, QPalette.ColorRole.HighlightedText, hl_text)
        self.file_list.setPalette(p)

    def _toggle_auto(self, state):
        self._auto_mode = bool(state)

    # ── 目录 ────────────────────────────────────────

    def _on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择 SVN 工作目录", self.dir_input.text())
        if d:
            self.dir_input.setText(d)
            self._on_search()

    def _open_dir(self, path, desc=""):
        """在资源管理器中打开目录"""
        if path and os.path.isdir(path):
            try:
                os.startfile(path)
                self._log(f"📂 打开目录: {path}")
            except Exception as e:
                self._log(f"❌ 打开失败: {e}")
        else:
            self._log(f"⚠ 目录不存在: {path or desc or '(空)'}")

    def _on_browse_export(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择导表 BAT", self.export_path_input.text(),
            "BAT 文件 (*.bat);;所有文件 (*.*)",
        )
        if path:
            self.export_path_input.setText(path)

    def _on_export(self):
        bat_path = self.export_path_input.text().strip()
        if not bat_path or not os.path.isfile(bat_path):
            self._log(f"⚠ BAT 文件不存在: {bat_path}")
            return
        self._log(f"▶ 执行导表: {bat_path}")
        self.export_btn.setEnabled(False)

        self._export_worker = ExportWorker(bat_path)
        self._export_worker.export_finished.connect(self._on_export_done)
        self._export_worker.start()

    def _on_export_done(self, ret):
        icon = "✅" if ret == 0 else f"❌ 返回码 {ret}"
        self._log(f"🏁 导表结束  {icon}")
        self.export_btn.setEnabled(True)

    # ── 搜索 / 实时过滤 ─────────────────────────────

    def _on_kw_changed(self, text):
        """关键词输入变化 → debounce 后实时过滤"""
        if self._all_entries:
            self._debounce_timer.start(250)   # 250ms 防抖
        else:
            # 还没扫描过，自动触发首次扫描
            self._debounce_timer.start(250)

    def _apply_filter(self):
        """debounce 超时后执行过滤"""
        if not self._all_entries:
            if not self._scanning:
                self._on_search()
            return
        keyword = self.kw_input.text().strip()
        self._filter_and_display(keyword)

    def _filter_and_display(self, keyword):
        """从缓存 self._all_entries 中过滤并显示"""
        kw_lower = keyword.lower()
        if kw_lower:
            matches = [e for e in self._all_entries if kw_lower in e[1].lower()]
            self._add_keyword(keyword)   # 自动记录常用关键词
        else:
            matches = self._all_entries

        svn_count = sum(1 for sc, _, _, _ in matches if sc is not None)
        self._log(f"🔎 关键词: '{keyword or '(全部)'}' → 匹配 {len(matches)} 个文件 (SVN变更: {svn_count})")
        self._populate_list(matches)

    def _on_search(self):
        """完整重新扫描（刷新按钮 / 首次扫描）"""
        workdir = self.dir_input.text().strip()
        if not workdir or not os.path.isdir(workdir):
            self._log("⚠ 请先输入有效的目录")
            return

        self._log(f"🔄 扫描目录: {workdir}")
        self._log("⏳ 正在扫描本地文件 + svn status ...")
        self._scanning = True
        self.search_btn.setEnabled(False)
        self.revert_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.commit_btn.setEnabled(False)
        self._count_label.setText("文件: …")

        self._scan_worker = ScanWorker(workdir)
        self._scan_worker.result.connect(self._on_scan_done)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_scan_done(self, entries):
        # entries: [(status_char|None, filename, full_path, exists_locally), ...]
        svn_count = sum(1 for sc, _, _, _ in entries if sc is not None)
        local_count = sum(1 for _, _, _, e in entries if e)
        self._log(f"📂 扫描完成: {len(entries)} 个文件 (SVN 有变更: {svn_count}, 本地存在: {local_count})")

        # 缓存结果
        self._all_entries = entries
        self._scanning = False

        # 根据当前关键词过滤显示
        keyword = self.kw_input.text().strip()
        self._filter_and_display(keyword)

    def _on_scan_error(self, err):
        self._log(f"❌ {err}")
        self._count_label.setText("文件: 0")
        self._scanning = False
        self.search_btn.setEnabled(True)

    # ── 选择 ────────────────────────────────────────

    def _set_all_checked(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(state)

    def _on_invert(self):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            new = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(new)

    # ── 右键菜单 & 双击 ─────────────────────────────

    def _on_context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        if not item:
            return
        item.setSelected(True)
        self.file_list.setCurrentItem(item)
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)
        if data["exists"]:
            open_action = menu.addAction("打开文件")
            open_action.triggered.connect(lambda: self._open_file(data["full_path"]))
        else:
            menu.addAction("(文件不存在)").setEnabled(False)

        menu.addSeparator()
        revert_action = menu.addAction("SVN Revert + Update")
        revert_action.triggered.connect(lambda: self._revert_single(data["filename"]))

        commit_action = menu.addAction("SVN 提交")
        commit_action.triggered.connect(lambda: self._commit_single(data["filename"]))

        menu.addSeparator()
        log_action = menu.addAction("SVN 日志")
        log_action.triggered.connect(lambda: self._svn_log_single(data["filename"]))

        cleanup_action = menu.addAction("SVN 清理")
        cleanup_action.triggered.connect(lambda: self._svn_cleanup_single(data["filename"]))

        update_action = menu.addAction("SVN 更新")
        update_action.triggered.connect(lambda: self._svn_update_single(data["filename"]))

        menu.addSeparator()
        del_action = menu.addAction("删除文件")
        del_action.triggered.connect(lambda: self._delete_single(data["full_path"], data["filename"]))

        menu.exec(self.file_list.viewport().mapToGlobal(pos))

    def _on_double_click(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and data["exists"]:
            self._open_file(data["full_path"])
        elif data:
            new = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(new)

    def _on_item_clicked(self, item):
        """单击整行 → 切换勾选"""
        new = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
        item.setCheckState(new)

    def _open_file(self, full_path):
        try:
            os.startfile(full_path)
            self._log(f"📂 打开: {full_path}")
        except Exception as e:
            self._log(f"❌ 打开失败: {e}")

    # ── 删除 ────────────────────────────────────────

    def _delete_single(self, full_path, filename):
        try:
            os.remove(full_path)
            self._log(f"🗑 已删除: {filename}")
        except Exception as e:
            self._log(f"❌ 删除失败: {e}")
        self._on_search()

    def _on_delete(self):
        """批量删除选中的本地存在文件"""
        to_delete = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            d = item.data(Qt.ItemDataRole.UserRole)
            if d and d["exists"]:
                to_delete.append((d["full_path"], d["filename"]))

        if not to_delete:
            self._log("⚠ 没有可删除的本地文件（只删除了不存在的文件，或选中文件无可删除项）")
            return

        self._log(f"🗑 删除 {len(to_delete)} 个文件 ...")
        deleted = 0
        for full_path, fn in to_delete:
            try:
                os.remove(full_path)
                self._log(f"🗑 已删除: {fn}")
                deleted += 1
            except Exception as e:
                self._log(f"❌ 删除失败 ({fn}): {e}")

        self._log(f"🏁 删除完成: {deleted}/{len(to_delete)} 个文件")
        # 刷新列表
        self._on_search()

    # ── revert ──────────────────────────────────────

    def _revert_single(self, filename):
        """右键菜单：勾选单文件后复用 _on_revert"""
        # 取消所有勾选
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        # 只勾选目标
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            d = item.data(Qt.ItemDataRole.UserRole)
            if d and d["filename"] == filename:
                item.setCheckState(Qt.CheckState.Checked)
                break
        self._on_revert()

    def _on_revert(self):
        workdir = self.dir_input.text().strip()
        selected = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            d = item.data(Qt.ItemDataRole.UserRole)
            if d:
                selected.append(d["filename"])

        if not selected:
            self._log("没有选中任何文件")
            return

        self._log(f"对 {len(selected)} 个文件执行 revert + update ...")
        self.revert_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.commit_btn.setEnabled(False)

        commands = []
        for fn in selected:
            commands.append((f"{fn} (revert)", ["svn", "revert", fn]))
            commands.append((f"{fn} (update)", ["svn", "update", fn]))

        self._svn_worker = SvnWorker(commands, workdir)
        self._svn_worker.output_line.connect(self._log)
        self._svn_worker.finished.connect(self._on_revert_done)
        self._svn_worker.start()

    def _on_revert_done(self):
        self._log("全部操作结束")
        self.revert_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.commit_btn.setEnabled(True)
        # 清缓存，触发关键词 debounce → 自动重新扫描（避开直接在线程回调中起 worker）
        self._all_entries = []
        self._on_kw_changed(self.kw_input.text())

    # ── commit ──────────────────────────────────────

    def _commit_single(self, filename):
        """右键菜单：勾选单文件后复用 _on_commit"""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            d = item.data(Qt.ItemDataRole.UserRole)
            if d and d["filename"] == filename:
                item.setCheckState(Qt.CheckState.Checked)
                break
        self._on_commit()

    def _svn_log_single(self, filename):
        """呼出 TortoiseSVN 日志窗口（回退到命令行）"""
        workdir = self.dir_input.text().strip()
        self._log(f"📜 SVN 日志: {filename}")
        full_path = os.path.join(workdir, filename)
        tortoise = shutil.which("TortoiseProc.exe")
        if tortoise:
            try:
                subprocess.Popen(
                    [tortoise, "/command:log", f"/path:{full_path}"],
                    cwd=workdir,
                    creationflags=_NO_WINDOW,
                )
                self._log("  已呼出 TortoiseSVN 日志窗口")
            except Exception as e:
                self._log(f"❌ 打开日志失败: {e}")
        else:
            try:
                subprocess.Popen(
                    ["svn", "log", filename],
                    cwd=workdir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            except Exception as e:
                self._log(f"❌ 打开日志失败: {e}")

    def _svn_cleanup_single(self, _filename):
        """SVN 清理（作用于整个工作目录）"""
        workdir = self.dir_input.text().strip()
        self._log(f"🧹 SVN 清理: {workdir}")
        try:
            r = subprocess.run(
                ["svn", "cleanup"], cwd=workdir,
                capture_output=True, text=True, timeout=60,
                encoding="gbk", errors="replace",
                creationflags=_NO_WINDOW,
            )
            if r.returncode == 0:
                self._log(f"  清理完成")
            else:
                self._log(f"  清理返回码 {r.returncode}")
            if r.stderr.strip():
                for line in r.stderr.strip().split("\n"):
                    if line:
                        self._log(f"  [stderr] {line}")
        except Exception as e:
            self._log(f"❌ 清理失败: {e}")

    def _svn_update_single(self, filename):
        """SVN 更新单个文件"""
        workdir = self.dir_input.text().strip()
        self._log(f"⬇ SVN 更新: {filename}")
        try:
            r = subprocess.run(
                ["svn", "update", filename], cwd=workdir,
                capture_output=True, text=True, timeout=120,
                encoding="gbk", errors="replace",
                creationflags=_NO_WINDOW,
            )
            for line in r.stdout.strip().split("\n"):
                if line:
                    self._log(f"  {line}")
            if r.stderr.strip():
                for line in r.stderr.strip().split("\n"):
                    if line:
                        self._log(f"  [stderr] {line}")
            self._log(f"  {'更新完成' if r.returncode == 0 else f'返回码 {r.returncode}'}")
            # 刷新文件列表以反映最新状态
            self._on_search()
        except subprocess.TimeoutExpired:
            self._log("  ⏱ 超时")
        except Exception as e:
            self._log(f"❌ 更新失败: {e}")

    def _on_commit(self):
        """对选中的文件呼出 SVN 提交界面"""
        workdir = self.dir_input.text().strip()
        selected = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            d = item.data(Qt.ItemDataRole.UserRole)
            if d:
                selected.append(d["filename"])

        if not selected:
            self._log("没有选中任何文件")
            return

        self._log(f"📝 对 {len(selected)} 个文件呼出 SVN 提交界面 ...")
        self.commit_btn.setEnabled(False)

        # 优先尝试 TortoiseSVN
        tortoise = shutil.which("TortoiseProc.exe")
        if tortoise:
            paths = "*".join(os.path.join(workdir, fn) for fn in selected)
            try:
                subprocess.Popen(
                    [tortoise, "/command:commit", f"/path:{paths}"],
                    cwd=workdir,
                    creationflags=_NO_WINDOW,
                )
                self._log("✅ 已呼出 TortoiseSVN 提交界面")
            except Exception as e:
                self._log(f"❌ TortoiseSVN 启动失败: {e}")
        else:
            # 备用：命令行 svn commit（弹出新控制台）
            try:
                subprocess.Popen(
                    ["svn", "commit"] + selected,
                    cwd=workdir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self._log("✅ 已启动命令行 svn commit（在弹出控制台中输入提交信息）")
            except Exception as e:
                self._log(f"❌ svn commit 启动失败: {e}")

        self.commit_btn.setEnabled(True)

    def _populate_list(self, entries):
        """填充文件列表（从 _on_scan_done 中抽出来复用）"""
        self.file_list.clear()
        # 排序：存在的文件在上，不存在的在下
        sorted_entries = sorted(entries, key=lambda e: (not e[3], e[1].lower()))
        alt_idx = 0
        for sc, fn, full_path, exists in sorted_entries:
            if sc:
                label = STATUS_LABEL.get(sc, sc)
                display = f"[{label}]  {fn}"
            else:
                display = f"         {fn}"
            item = QListWidgetItem(display)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, {
                "filename": fn, "full_path": full_path,
                "status": sc, "exists": exists,
                "alt_idx": alt_idx,
            })
            if exists:
                alt_idx += 1
            self.file_list.addItem(item)
        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)
            self.file_list.scrollToItem(self.file_list.item(0), QListWidget.ScrollHint.PositionAtTop)
        self._count_label.setText(f"文件: {len(entries)}")
        self.search_btn.setEnabled(True)
        self.revert_btn.setEnabled(len(entries) > 0)
        self.delete_btn.setEnabled(len(entries) > 0)
        self.commit_btn.setEnabled(len(entries) > 0)

    # ── 关键词快捷管理 ──────────────────────────────

    def _kw_file(self):
        return os.path.join(os.path.dirname(__file__), "keywords.json")

    def _load_keywords(self):
        try:
            with open(self._kw_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
            # 兼容旧格式（纯字符串列表）→ 转为 {kw, count} dict
            normalized = []
            for item in data:
                if isinstance(item, str):
                    normalized.append({"kw": item, "count": 1})
                else:
                    normalized.append(item)
            self._kw_chips[:] = normalized
        except Exception:
            self._kw_chips[:] = []

    def _save_keywords(self):
        try:
            with open(self._kw_file(), "w", encoding="utf-8") as f:
                json.dump(self._kw_chips, f, ensure_ascii=False)
        except Exception:
            pass

    def _add_keyword(self, kw):
        """记录关键词使用，按使用频率排序，最多保留 20 个（约两行）"""
        kw = kw.strip()
        if not kw:
            return
        # 查找已存在的条目，递增计数
        found = False
        for entry in self._kw_chips:
            if entry["kw"] == kw:
                entry["count"] += 1
                found = True
                break
        if not found:
            self._kw_chips.insert(0, {"kw": kw, "count": 1})
        # 按 count 降序排列
        self._kw_chips.sort(key=lambda x: x["count"], reverse=True)
        # 最多保留 20 个
        if len(self._kw_chips) > 20:
            self._kw_chips[:] = self._kw_chips[:20]
        self._save_keywords()
        self._refresh_chips()

    def _remove_keyword(self, kw):
        for entry in self._kw_chips:
            if entry["kw"] == kw:
                self._kw_chips.remove(entry)
                self._save_keywords()
                self._refresh_chips()
                return

    def _refresh_chips(self):
        # 清空已有
        while self._kw_chips_layout.count():
            item = self._kw_chips_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        # 主题判定
        is_light = (self._current_theme == "light")
        fg = "#6b7280" if is_light else "#94a3b8"
        count_fg = "#9ca3af" if is_light else "#64748b"
        # 重建
        for entry in self._kw_chips:
            kw = entry["kw"]
            count = entry.get("count", 0)
            chip = QWidget()
            row = QHBoxLayout(chip)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            # 按钮文本: "关键词 (使用次数)"
            btn_text = f"{kw} ({count})" if count > 1 else kw
            kw_btn = QPushButton(btn_text)
            kw_btn.setObjectName("actionBtn")
            kw_btn.setFixedHeight(24)
            kw_btn.setStyleSheet(f"color: {fg}; border-right: none; border-top-right-radius: 0; border-bottom-right-radius: 0;")
            kw_btn.clicked.connect(lambda checked, k=kw: self.kw_input.setText(k))
            row.addWidget(kw_btn)
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(22, 24)
            close_btn.setObjectName("actionBtn")
            close_btn.setStyleSheet(
                f"QPushButton {{ color: {count_fg}; "
                f"border-left: none; border-radius: 0 6px 6px 0; "
                f"padding: 0; font-size: 11px; }}"
            )
            close_btn.clicked.connect(lambda checked, k=kw: self._remove_keyword(k))
            row.addWidget(close_btn)
            self._kw_chips_layout.addWidget(chip)

    def _log(self, msg):
        self.log_output.append(msg)
        bar = self.log_output.verticalScrollBar()
        bar.setValue(bar.maximum())


def main():
    app = QApplication(sys.argv)
    window = SvnRevertApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
