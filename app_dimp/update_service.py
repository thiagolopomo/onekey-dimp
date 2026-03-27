#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Servico de atualizacao - OneKey Payments DIMP."""

import os
import sys
import json
import hashlib
import tempfile
import zipfile
import requests
from pathlib import Path

SUPABASE_URL = "https://jhkqfacpobwnirioskii.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impoa3FmYWNwb2J3bmlyaW9za2lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNzU2MDEsImV4cCI6MjA4ODg1MTYwMX0.lnRnP4ESzQc54LxX-6Y-qRZsfPEv1SGg3ozd2R0N4hY"
UPDATE_MANIFEST_KEY = "dimp_update_manifest"


def parse_version(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)


def get_local_version():
    try:
        appdata = Path.home() / "AppData" / "Local" / "OneKeyDIMP" / "app_version.json"
        if appdata.exists():
            return json.loads(appdata.read_text(encoding="utf-8-sig")).get("version", "0.0.0")
    except Exception:
        pass
    try:
        p = Path(__file__).with_name("app_version.json")
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8-sig")).get("version", "0.0.0")
    except Exception:
        pass
    return "0.0.0"


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def check_for_update(timeout=10):
    """Retorna dict {version, notes, url, sha256, mandatory} ou None."""
    try:
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        }
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/app_config?key=eq.{UPDATE_MANIFEST_KEY}&select=value",
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None

        data = json.loads(rows[0]["value"])
        remote_ver = data.get("version", "0.0.0")
        local_ver = get_local_version()

        if parse_version(remote_ver) > parse_version(local_ver):
            return {
                "version": remote_ver,
                "current": local_ver,
                "notes": data.get("notes", ""),
                "url": data.get("url", ""),
                "sha256": data.get("sha256", ""),
                "mandatory": data.get("mandatory", False),
            }
    except Exception:
        pass
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_update_package(url, progress_callback=None):
    tmp = tempfile.mkdtemp(prefix="dimp_update_")
    dest = os.path.join(tmp, "update.zip")

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    pct = int((downloaded / total) * 100)
                    progress_callback(pct, f"Baixando... {downloaded // 1024 // 1024}MB")

    return dest


def extract_update_package(zip_path, progress_callback=None):
    extract_dir = os.path.join(os.path.dirname(zip_path), "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.namelist()
        total = len(members)
        for i, member in enumerate(members):
            zf.extract(member, extract_dir)
            if progress_callback and total > 0:
                pct = int(((i + 1) / total) * 100)
                progress_callback(pct, f"Extraindo... {i + 1}/{total}")

    pkg = os.path.join(extract_dir, "package")
    if os.path.isdir(pkg):
        return pkg
    return extract_dir
