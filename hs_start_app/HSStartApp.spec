# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for HS App Launcher."""

from pathlib import Path

BASE_DIR = Path(SPECPATH)

a = Analysis(
    [str(BASE_DIR / "hs_start_app.py")],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=[(str(BASE_DIR / "app.ico"), ".")],
    hiddenimports=["PySide6", "PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "scipy", "pandas", "numpy", "pytest",
        "setuptools", "pip", "PIL", "cv2", "cryptography",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HSStartApp",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(BASE_DIR / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="HSStartApp",
)
