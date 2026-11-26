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
INNO = next(
    (p for p in (
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    ) if os.path.exists(p)),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
)

SUPABASE_URL = "https://jhkqfacpobwnirioskii.supabase.co"
MANIFEST_KEY = "dimp_update_manifest"
# A chave publica (anon) nao grava mais em app_config (supabase/01_protege_manifest_e_acessos.sql).
# Publicar exige a chave secreta, que fica so na variavel de ambiente, nunca no codigo.
ENV_CHAVE_SECRETA = "SUPABASE_SERVICE_ROLE_KEY"


def _papel_da_chave(chave):
    """'service_role', 'anon' ou '' (desconhecido)."""
    if chave.startswith("sb_secret_"):
        return "service_role"
    if chave.startswith("sb_publishable_"):
        return "anon"
    try:
        import base64
        payload = chave.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("role", "")
    except Exception:
        return ""


def _headers_admin(chave):
    # Chave nova (sb_secret_...) vai so no header apikey; a legada (JWT) vai nos dois
    h = {"apikey": chave, "Content-Type": "application/json"}
    if not chave.startswith("sb_"):
        h["Authorization"] = f"Bearer {chave}"
    return h


def _chave_do_ambiente():
    """Variavel do processo; se faltar, le a salva com setx (HKCU\\Environment).
    Programas abertos antes do setx (ex.: o terminal dentro do app do Claude)
    so enxergam a variavel nova depois de reiniciar."""
    chave = os.environ.get(ENV_CHAVE_SECRETA, "").strip()
    if chave or os.name != "nt":
        return chave
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return str(winreg.QueryValueEx(k, ENV_CHAVE_SECRETA)[0]).strip()
    except OSError:
        return ""


def ler_chave_secreta():
    """Le e valida a chave secreta ANTES de buildar/publicar qualquer coisa."""
    import requests
    chave = _chave_do_ambiente()
    if not chave:
        print(f"ERRO: variavel de ambiente {ENV_CHAVE_SECRETA} nao definida.")
        print("  Pegue a chave em: Supabase > Project Settings > API Keys > service_role (ou Secret key)")
        print(f'  Rode uma vez:  setx {ENV_CHAVE_SECRETA} "<chave>"   e abra um terminal novo.')
        sys.exit(1)
    if _papel_da_chave(chave) != "service_role":
        print(f"ERRO: {ENV_CHAVE_SECRETA} nao e a chave secreta (service_role). Nao use a chave anon/publica.")
        sys.exit(1)
    r = requests.get(f"{SUPABASE_URL}/rest/v1/app_config?key=eq.{MANIFEST_KEY}&select=key",
                     headers=_headers_admin(chave), timeout=20)
    if r.status_code != 200:
        print(f"ERRO: a chave secreta foi recusada pelo Supabase (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(1)
    return chave


def gravar_manifest(manifest, chave):
    """Grava o manifest de update e confere lendo de volta."""
    import requests
    h = _headers_admin(chave)
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/app_config",
        headers={**h, "Prefer": "resolution=merge-duplicates,return=representation"},
        json={"key": MANIFEST_KEY, "value": json.dumps(manifest)},
        timeout=20,
    )
    if r.status_code >= 300:
        print(f"  ERRO Supabase HTTP {r.status_code}: {r.text[:300]}")
        return False
    g = requests.get(f"{SUPABASE_URL}/rest/v1/app_config?key=eq.{MANIFEST_KEY}&select=value",
                     headers=h, timeout=20)
    rows = g.json() if g.ok else []
    lido = json.loads(rows[0]["value"]) if rows else None
    if lido != manifest:
        print(f"  ERRO: manifest lido de volta nao confere: {lido}")
        return False
    print(f"  Supabase: manifest v{manifest['version']} gravado e conferido")
    return True


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

    # Checa a chave secreta antes de tudo: sem ela o manifest nao pode ser gravado
    chave_secreta = ler_chave_secreta()

    # 1. Versao
    print(f"\n[1/8] Atualizando versao para {version}...")
    ver_file = BASE_DIR / "app_version.json"
    ver_file.write_text(json.dumps({"version": version}), encoding="utf-8")
    # Versao que aparece na tela (selo do topo e rodape). Bytes para nao mexer nas quebras de linha.
    shell_py = BASE_DIR / "shell.py"
    txt = shell_py.read_bytes().decode("utf-8")
    novo = re.sub(r'(QLabel\("v)\d+\.\d+\.\d+("\))', rf"\g<1>{version}\g<2>", txt)
    novo = re.sub(r'(QLabel\("OneKey Payments DIMP v)\d+\.\d+\.\d+("\))', rf"\g<1>{version}\g<2>", novo)
    if novo.count(f"v{version}") < 2:
        print("ERRO: nao achei os 2 textos de versao em shell.py")
        sys.exit(1)
    shell_py.write_bytes(novo.encode("utf-8"))

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
    iss_content = re.sub(
        r'VersionInfoVersion=[\d.]+',
        f'VersionInfoVersion={version}.0',
        iss_content
    )
    iss_path.write_text(iss_content, encoding="utf-8")
    if not run(f'"{INNO}" "{iss_path}"'):
        print("INSTALADOR FALHOU!")
        sys.exit(1)

    # Assinar o instalador (sem assinatura o Smart App Control bloqueia o update)
    from build_release import assinar
    if not assinar(BASE_DIR / "release_build" / "installer" / f"OneKeyDIMP_Setup_v{version}.exe"):
        print("ASSINATURA DO INSTALADOR FALHOU!")
        sys.exit(1)

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
    run('git add app_dimp/app_version.json app_dimp/installer.iss app_dimp/shell.py')
    run(f'git commit -m "release: v{version} - {notes}"')
    if not run('git push origin main'):
        print("PUSH FALHOU! Nada foi publicado ainda (sem release e sem manifest).")
        sys.exit(1)

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
    if not run(release_cmd):
        print("RELEASE FALHOU! O manifest NAO foi alterado (os apps continuam na versao anterior).")
        sys.exit(1)

    # 7. Supabase manifest
    print(f"\n[7/8] Atualizando Supabase...")
    download_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/{tag}/{zip_name}"
    # So aponta os apps para o release depois de confirmar que o ZIP baixa
    import requests
    with requests.get(download_url, stream=True, allow_redirects=True, timeout=60) as d:
        tamanho = int(d.headers.get("content-length", 0))
        if d.status_code != 200 or tamanho != zip_path.stat().st_size:
            print(f"DOWNLOAD DO RELEASE NAO CONFERE (HTTP {d.status_code}, {tamanho} bytes). Manifest NAO alterado.")
            sys.exit(1)
    print(f"  Download do release OK ({tamanho // 1024 // 1024} MB)")

    manifest = {
        "version": version,
        "notes": notes,
        "mandatory": mandatory,
        "url": download_url,
        "sha256": zip_sha,
    }

    if not gravar_manifest(manifest, chave_secreta):
        print("MANIFEST NAO FOI ATUALIZADO! O release existe, mas os apps nao vao ver o update.")
        sys.exit(1)

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
