#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import multiprocessing
import ctypes

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "OneKeyPayments.DIMP.1.0"
    )
except Exception:
    pass

from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PySide6.QtCore import QTimer, Qt

from resources import obter_icone, carregar_fontes_app
from theme import build_app_qss
from splash import SplashScreen
from access import TelaAcesso
from shell import MainShell


def verificar_atualizacao(shell):
    """Verifica se ha update disponivel e oferece ao usuario."""
    try:
        from update_service import check_for_update, download_update_package, extract_update_package
        from update_dialog import UpdateDialog

        info = check_for_update()
        if not info:
            return

        dlg = UpdateDialog(info, shell)
        dlg.setWindowIcon(shell.windowIcon())
        result = dlg.exec()

        if result == UpdateDialog.Accepted and dlg._accepted:
            url = info.get("url", "")
            if not url:
                QMessageBox.warning(shell, "Erro", "URL de download nao disponivel.")
                return

            progress = QProgressDialog("Baixando atualizacao...", "Cancelar", 0, 100, shell)
            progress.setWindowTitle("Atualizando")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            def on_progress(pct, msg):
                progress.setValue(pct)
                progress.setLabelText(msg)
                QApplication.processEvents()

            zip_path = download_update_package(url, progress_callback=on_progress)

            progress.setLabelText("Extraindo...")
            source_dir = extract_update_package(zip_path, progress_callback=on_progress)
            progress.close()

            expected_sha = info.get("sha256", "")
            if expected_sha:
                from update_service import sha256_file
                actual_sha = sha256_file(zip_path)
                if actual_sha != expected_sha:
                    QMessageBox.critical(shell, "Erro",
                        "Hash do pacote nao confere. Download corrompido.")
                    return

            try:
                import subprocess
                from pathlib import Path as _Path
                import json as _json

                setup_exe = None
                for f in _Path(source_dir).rglob("*.exe"):
                    if "Setup" in f.name or "OneKey" in f.name:
                        setup_exe = str(f)
                        break

                if not setup_exe:
                    QMessageBox.warning(shell, "Erro", "Setup nao encontrado no pacote.")
                    return

                appdata = _Path.home() / "AppData" / "Local" / "OneKeyDIMP"
                appdata.mkdir(parents=True, exist_ok=True)
                (appdata / "app_version.json").write_text(
                    _json.dumps({"version": info["version"]}), encoding="utf-8"
                )

                install_dir = _Path(r"C:\Program Files\OneKey DIMP")
                installed_exe = install_dir / "OneKey DIMP.exe"

                log_file = appdata / "update_log.txt"
                bat_path = appdata / "update_and_restart.bat"
                bat_content = f'''@echo off
echo [%date% %time%] Update iniciado >> "{log_file}"
timeout /t 5 /nobreak >nul
echo Executando instalador: {setup_exe} >> "{log_file}"
"{setup_exe}" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /DIR="{install_dir}"
echo Instalador finalizado com codigo: %errorlevel% >> "{log_file}"
timeout /t 3 /nobreak >nul
if exist "{installed_exe}" (
    echo Reabrindo app... >> "{log_file}"
    start "" "{installed_exe}"
) else (
    echo EXE NAO ENCONTRADO >> "{log_file}"
)
del "%~f0"
'''
                bat_path.write_text(bat_content, encoding="utf-8")

                subprocess.Popen(
                    ["cmd", "/c", str(bat_path)],
                    creationflags=0x08000000,
                    close_fds=True
                )

                QApplication.quit()

            except Exception as e:
                QMessageBox.warning(shell, "Aviso",
                    f"Atualizacao sera aplicada no proximo inicio.\n{e}")

    except Exception as e:
        print(f"[UPDATE] Erro: {e}")


def main():
    app = QApplication(sys.argv)

    familia = carregar_fontes_app()
    app.setStyleSheet(build_app_qss(familia))

    icone = obter_icone()
    app.setWindowIcon(icone)

    splash = SplashScreen()

    shell = None

    def abrir_fluxo():
        nonlocal shell

        acesso = TelaAcesso()
        acesso.setWindowIcon(icone)
        result = acesso.exec()

        if result == TelaAcesso.Accepted and acesso.acesso_liberado:
            shell = MainShell()
            shell.setWindowIcon(icone)
            shell.show()

            # Verificar updates 1s depois de abrir
            QTimer.singleShot(1000, lambda: verificar_atualizacao(shell))
        else:
            app.quit()

    splash.iniciar(abrir_fluxo)

    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
