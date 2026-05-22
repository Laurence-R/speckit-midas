# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Midas — 台股盤後投研
# Usage: pyinstaller build.spec

from pathlib import Path

ROOT = Path(SPECPATH)
VENV_SITE = ROOT / ".venv" / "Lib" / "site-packages"

a = Analysis(
    [str(ROOT / "src" / "midas" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        # customtkinter assets (themes, images)
        (str(VENV_SITE / "customtkinter"), "customtkinter"),
    ],
    hiddenimports=[
        # google-genai transitive imports not auto-detected
        "google.genai",
        "google.auth",
        "google.auth.transport.requests",
        # sqlite3 is stdlib but ensure included on some build environments
        "sqlite3",
        # platformdirs needed at runtime
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter.test",
        "unittest",
        "xmlrpc",
        "doctest",
        "pydoc",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Midas",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # Windows GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/midas.ico",  # uncomment when icon is available
)
