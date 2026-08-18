# -*- coding: utf-8 -*-
"""
费用统计 一键打包脚本（由 打包.bat 调用）
- 检查/安装 PyInstaller
- 从 PNG 生成 ICO（若缺少）
- 清理旧产物并以 onedir 模式打包 exe
- 复制配套文件到发布目录
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

APP_NAME = "费用统计"
ICON_PNG = BASE_DIR / "费用统计ico.png"
ICON_ICO = BASE_DIR / "费用统计ico.ico"
SUPPORT_FILES = ["input.txt", "num_name.txt", "使用说明.txt"]


def run(args: list, check: bool = True) -> int:
    """运行命令并打印"""
    print(">", " ".join(str(a) for a in args))
    r = subprocess.run([str(a) for a in args])
    if check and r.returncode != 0:
        sys.exit(r.returncode)
    return r.returncode


def ensure_pyinstaller():
    """检查 PyInstaller，缺失则安装"""
    r = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        print("[提示] 未检测到 PyInstaller，正在安装...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])


def prepare_icon() -> list:
    """准备图标，返回 PyInstaller 的 --icon 参数列表"""
    if ICON_ICO.exists():
        return ["--icon", str(ICON_ICO)]
    if ICON_PNG.exists():
        print(f"[提示] 未找到 {ICON_ICO.name}，正在从 {ICON_PNG.name} 生成...")
        from PIL import Image
        Image.open(ICON_PNG).save(
            ICON_ICO, format="ICO",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        return ["--icon", str(ICON_ICO)]
    print("[提示] 未找到图标文件，将使用默认图标。")
    return []


def clean_old_artifacts():
    """清理旧的打包产物"""
    for name in ["dist", "build", f"{APP_NAME}.spec"]:
        p = BASE_DIR / name
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()


def backup_old_config() -> str | None:
    """备份旧打包目录 _internal 中的 config.json（防止重打包丢失用户设置）"""
    old = BASE_DIR / "dist" / APP_NAME / "_internal" / "config.json"
    try:
        if old.exists():
            return old.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


def build():
    """执行打包"""
    print("=" * 44)
    print(f"  {APP_NAME} 一键打包")
    print("=" * 44)
    print()

    old_config = backup_old_config()
    ensure_pyinstaller()
    icon_arg = prepare_icon()
    clean_old_artifacts()

    print("[打包] 正在打包，请稍候（约 1-2 分钟）...")
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--windowed",
        *icon_arg,
        "--name", APP_NAME,
        f"{APP_NAME}.py",
    ])

    out_dir = BASE_DIR / "dist" / APP_NAME
    for f in SUPPORT_FILES:
        src = BASE_DIR / f
        if src.exists():
            shutil.copy2(src, out_dir / f)

    exe = out_dir / f"{APP_NAME}.exe"
    if not exe.exists():
        print("[错误] 未找到生成的 exe 文件，打包可能失败。")
        sys.exit(1)

    # 恢复旧配置（保留用户的小数位数选择）
    if old_config:
        cfg_dir = out_dir / "_internal"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "config.json").write_text(old_config, encoding="utf-8")
        print("[提示] 已保留上次的小数位数设置 (config.json)")

    print()
    print("=" * 44)
    print("  打包完成！")
    print(f"  程序位置: {exe}")
    print("=" * 44)

    # 清理打包中间目录
    shutil.rmtree(BASE_DIR / "build", ignore_errors=True)

    # 打开输出目录
    try:
        os.startfile(str(out_dir))
    except Exception:
        pass


if __name__ == "__main__":
    build()
