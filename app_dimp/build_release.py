#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build release - OneKey DIMP
PyInstaller packaging (sem PyArmor para simplificar).
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
STAGE_DIR = BASE_DIR / "release_build" / "stage"
OUTPUT_DIR = BASE_DIR / "release_build" / "output"
APP_NAME = "OneKey DIMP"

MAIN_MODULES = [
    "main.py", "shell.py", "theme.py", "resources.py", "splash.py",
    "access.py", "dimp_logic.py", "update_service.py", "update_dialog.py",
    "app_version.json",
]

ASSETS = ["logo_onekey.png"]

HIDDEN_IMPORTS = [
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "polars", "pandas", "openpyxl",
    "requests", "urllib3", "certifi", "idna", "charset_normalizer",
    "json", "hashlib", "uuid", "getpass", "socket", "platform",
]


def main():
    print("=" * 50)
    print(f"  BUILD: {APP_NAME}")
    print("=" * 50)

    # 1. Staging
    print("\n[1/3] Staging...")
    if STAGE_DIR.exists():
        shutil.rmtree(STAGE_DIR)
    STAGE_DIR.mkdir(parents=True)

    for m in MAIN_MODULES:
        src = BASE_DIR / m
        if src.exists():
            shutil.copy2(src, STAGE_DIR / m)
            print(f"  {m}")

    for a in ASSETS:
        src = BASE_DIR / a
        if src.exists():
            shutil.copy2(src, STAGE_DIR / a)
            print(f"  {a}")

    # Fonts
    fonts_src = BASE_DIR / "assets" / "fonts"
    fonts_dst = STAGE_DIR / "assets" / "fonts"
    if fonts_src.exists():
        shutil.copytree(fonts_src, fonts_dst)
        print("  assets/fonts/")

    # 2. PyInstaller
    print("\n[2/3] PyInstaller...")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    hidden = " ".join(f"--hidden-import={h}" for h in HIDDEN_IMPORTS)
    data_files = f'--add-data "{STAGE_DIR / "app_version.json"};."'
    data_files += f' --add-data "{STAGE_DIR / "logo_onekey.png"};."'

    if fonts_dst.exists():
        data_files += f' --add-data "{fonts_dst};assets/fonts"'

    cmd = (
        f'"{sys.executable}" -m PyInstaller '
        f'--name "{APP_NAME}" '
        f'--onedir --windowed --noconfirm '
        f'--distpath "{OUTPUT_DIR}" '
        f'{hidden} '
        f'--collect-all polars '
        f'--collect-all charset_normalizer '
        f'--collect-all certifi '
        f'{data_files} '
        f'"{STAGE_DIR / "main.py"}"'
    )

    print(f"  > pyinstaller ...")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(STAGE_DIR))
    if r.returncode != 0:
        print(f"  ERRO: {r.stderr[-500:]}")
        sys.exit(1)

    # 3. Copiar assets para output
    print("\n[3/3] Finalizando...")
    app_dir = OUTPUT_DIR / APP_NAME
    for a in ASSETS:
        src = STAGE_DIR / a
        if src.exists():
            shutil.copy2(src, app_dir / a)

    ver_src = STAGE_DIR / "app_version.json"
    if ver_src.exists():
        shutil.copy2(ver_src, app_dir / "app_version.json")

    print(f"\n  BUILD COMPLETO: {app_dir}")
    print(f"  Arquivos: {sum(1 for _ in app_dir.rglob('*') if _.is_file())}")


if __name__ == "__main__":
    main()
