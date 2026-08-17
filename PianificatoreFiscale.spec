# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec per PianificatoreFiscale (Windows, onefile)."""
import os

block_cipher = None

app_name = "PianificatoreFiscale"
icon_path = os.path.join("resources", "app_icon.png")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("resources/app_icon.png", "resources"),
        ("engine/fiscale/TaxRules", "engine/fiscale/TaxRules"),
        ("version.txt", "."),
    ],
    hiddenimports=[
        "models", "views", "engine",
        "models.theme", "models.config", "models.profilo",
        "views.main_window", "views.fiscale_view", "views.widgets",
        "engine.fiscale",
        "engine.fiscale.benefici", "engine.fiscale.confronto", "engine.fiscale.crediti",
        "engine.fiscale.cuneo", "engine.fiscale.detrazioni", "engine.fiscale.forfettario",
        "engine.fiscale.irpef", "engine.fiscale.iva", "engine.fiscale.models",
        "engine.fiscale.money", "engine.fiscale.ottimizzazione", "engine.fiscale.regimi",
        "engine.fiscale.rules", "engine.fiscale.scadenzario", "engine.fiscale.simulazione",
        "engine.fiscale.societa", "engine.fiscale.strumenti",
        "appinfo", "updater",
        "urllib.request", "urllib.error", "certifi",
        "customtkinter", "tzdata",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "reportlab", "tkinter.test", "unittest", "pydoc",
        "doctest", "sqlite3.test",
        "torch", "torchvision", "scipy", "pyarrow", "tensorflow",
        "sklearn", "numpy.testing", "pandas.testing", "pytest",
        "fastapi", "uvicorn", "pydantic",
    ],
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
    icon=icon_path if os.path.isfile(icon_path) else None,
)
