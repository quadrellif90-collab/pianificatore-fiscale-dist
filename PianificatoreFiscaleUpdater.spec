# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec per l'updater esterno di PianificatoreFiscale."""
import os

block_cipher = None
app_name = "PianificatoreFiscaleUpdater"

a = Analysis(
    ["updater.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=["urllib.request", "urllib.error", "json", "shutil", "certifi"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "reportlab", "tkinter", "customtkinter",
              "pandas", "openpyxl", "fastapi", "uvicorn", "pydantic",
              "torch", "scipy", "pyarrow", "tensorflow", "sklearn",
              "numpy.testing", "pandas.testing", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
