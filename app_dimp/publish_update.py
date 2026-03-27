#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Publicar update do OneKey DIMP.

Uso:
  python publish_update.py 1.0.1 "Corrigido bug X, adicionado Y"
  python publish_update.py 1.0.1 "Descricao" --mandatory

Pipeline:
  1. Atualiza app_version.json
  2. Build (PyInstaller)
  3. Compila instalador Inno Setup
  4. Cria ZIP do instalador
  5. Git commit + push
  6. Cria GitHub Release com ZIP
  7. Atualiza Supabase (manifest)
  8. Push final
"""

import os
import sys
import json
import subprocess
import hashlib
import re
from pathlib import Path

REPO_OWNER = "thiagolopomo"
REPO_NAME = "onekey-dimp"
BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent
INNO = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

SUPABASE_URL = "https://jhkqfacpobwnirioskii.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impoa3FmYWNwb2J3bmlyaW9za2lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNzU2MDEsImV4cCI6MjA4ODg1MTYwMX0.lnRnP4ESzQc54LxX-6Y-qRZsfPEv1SGg3ozd2R0N4hY"


def run(cmd, check=True):
    print(f"  > {cmd[:120]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.stdout.strip():
        for line in r.stdout.strip().split("\n")[-3:]:
            print(f"    {line}")
    if check and r.returncode != 0:
        print(f"  ERRO: {r.stderr[:300]}")
        return False
    return True


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) < 3:
        print("Uso: python publish_update.py <versao> <notas> [--mandatory]")
        print('Ex:  python publish_update.py 1.0.1 "Bug fix no processamento"')
        sys.exit(1)

    version = sys.argv[1]
    notes = sys.argv[2]
    mandatory = "--mandatory" in sys.argv

    print("=" * 60)
    print(f"  PUBLISH UPDATE - OneKey DIMP v{version}")
    print("=" * 60)

    # 1. Versao
    print(f"\n[1/8] Atualizando versao para {version}...")
    ver_file = BASE_DIR / "app_version.json"
    ver_file.write_text(json.dumps({"version": version}), encoding="utf-8")

    # 2. Build
    print(f"\n[2/8] Build (PyInstaller)...")
    os.chdir(BASE_DIR)
    if not run(f"{sys.executable} build_release.py"):
        print("BUILD FALHOU!")
        sys.exit(1)

    # 3. Instalador Inno Setup
    print(f"\n[3/8] Compilando instalador...")
    iss_path = BASE_DIR / "installer.iss"
    iss_content = iss_path.read_text(encoding="utf-8")
    iss_content = re.sub(
        r'#define MyAppVersion ".*?"',
        f'#define MyAppVersion "{version}"',
        iss_content
    )
    iss_path.write_text(iss_content, encoding="utf-8")
    run(f'"{INNO}" "{iss_path}"')

    # 4. ZIP
    print(f"\n[4/8] Criando ZIP...")
    import zipfile
    setup_path = BASE_DIR / "release_build" / "installer" / f"OneKeyDIMP_Setup_v{version}.exe"
    zip_name = f"OneKeyDIMP_v{version}.zip"
    zip_path = BASE_DIR / "release_build" / "installer" / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        if setup_path.exists():
            zf.write(setup_path, setup_path.name)

    zip_size = zip_path.stat().st_size / (1024 * 1024)
    zip_sha = sha256_file(zip_path)
    print(f"  {zip_name} ({zip_size:.0f} MB) SHA256: {zip_sha[:16]}...")

    # 5. Git commit + push
    print(f"\n[5/8] Commit + push...")
    os.chdir(ROOT_DIR)
    run('git add app_dimp/app_version.json app_dimp/installer.iss')
    run(f'git commit -m "release: v{version} - {notes}"')
    run('git push origin main')

    # 6. GitHub Release
    print(f"\n[6/8] Criando GitHub Release v{version}...")
    tag = f"v{version}"
    release_cmd = (
        f'gh release create {tag} '
        f'"{zip_path}" '
        f'--title "OneKey DIMP {tag}" '
        f'--notes "{notes}" '
        f'--repo {REPO_OWNER}/{REPO_NAME}'
    )
    run(release_cmd)

    # 7. Supabase manifest
    print(f"\n[7/8] Atualizando Supabase...")
    download_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{tag}/{zip_name}"

    manifest = {
        "version": version,
        "notes": notes,
        "mandatory": mandatory,
        "url": download_url,
        "sha256": zip_sha,
    }

    import requests as req
    sb_headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    r = req.post(
        f"{SUPABASE_URL}/rest/v1/app_config",
        headers=sb_headers,
        json={"key": "dimp_update_manifest", "value": json.dumps(manifest)},
        timeout=10,
    )
    print(f"  Supabase: {r.status_code}")

    manifest_path = ROOT_DIR / "version.json"
    manifest_path.write_text(json.dumps(manifest, indent=4, ensure_ascii=False), encoding="utf-8")

    # 8. Push final
    print(f"\n[8/8] Push final...")
    run('git add version.json')
    run(f'git commit -m "update manifest: v{version}"')
    run('git push origin main')

    print()
    print("=" * 60)
    print(f"  UPDATE v{version} PUBLICADO COM SUCESSO!")
    print(f"  Release: https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/tag/{tag}")
    print("=" * 60)


if __name__ == "__main__":
    main()
