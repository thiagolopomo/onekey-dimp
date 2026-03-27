#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Controle de acesso remoto - OneKey Payments DIMP
Usa Supabase para validacao de licenca por maquina.
Logs via Resend.
"""

import json
import hashlib
import getpass
import socket
import platform
import uuid
import time
import os
import requests
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QColor, QPixmap, QFont

from resources import caminho_recurso

APP_TITLE = "OneKey Payments DIMP"
CHECK_INTERVAL_MS = 3000

SUPABASE_URL = "https://jhkqfacpobwnirioskii.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impoa3FmYWNwb2J3bmlyaW9za2lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNzU2MDEsImV4cCI6MjA4ODg1MTYwMX0.lnRnP4ESzQc54LxX-6Y-qRZsfPEv1SGg3ozd2R0N4hY"
SUPABASE_TABLE = "solicitacoes_acesso"

CACHE_DIR = Path.home() / "AppData" / "Local" / "OneKeyDIMP"
CACHE_ACESSO = CACHE_DIR / "acesso_aprovado.json"

RESEND_KEY = "re_cw1BHBPG_BhTrRb5n8mTkvQ4qkppPPdE1"
EMAIL_DESTINO = "thiagolopomo67@gmail.com"


def _salvar_aprovacao(machine_id):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "machine_id": machine_id,
        "aprovado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": getpass.getuser(),
        "maquina": socket.gethostname(),
    }
    with open(CACHE_ACESSO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _verificar_aprovacao_local(machine_id):
    if not CACHE_ACESSO.exists():
        return False
    try:
        with open(CACHE_ACESSO, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("machine_id") == machine_id
    except Exception:
        return False


def _supabase_headers():
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def gerar_machine_id():
    usuario = getpass.getuser()
    maquina = socket.gethostname()
    sistema = platform.platform()
    base = f"{usuario}|{maquina}|{sistema}|{APP_TITLE}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def consultar_status_acesso(session_id, machine_id):
    url = f"{SUPABASE_URL}/rest/v1/rpc/consultar_status_acesso"
    payload = {"p_session_id": session_id, "p_machine_id": machine_id}
    resp = requests.post(url, headers=_supabase_headers(),
                         data=json.dumps(payload), timeout=20)
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else None


def solicitar_acesso_remoto(machine_id, session_id):
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    payload = {
        "app": APP_TITLE,
        "machine_id": machine_id,
        "session_id": session_id,
        "usuario_windows": getpass.getuser(),
        "maquina": socket.gethostname(),
        "status": "pendente",
    }
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    resp = requests.post(url, headers=headers,
                         data=json.dumps(payload), timeout=20)
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else payload


def registrar_log(machine_id, acao="app_aberto", detalhes=None):
    usuario = getpass.getuser()
    maquina = socket.gethostname()

    try:
        url = f"{SUPABASE_URL}/rest/v1/rpc/registrar_log_uso"
        payload = {
            "p_app": APP_TITLE,
            "p_usuario": usuario,
            "p_maquina": maquina,
            "p_machine_id": machine_id,
            "p_acao": acao,
            "p_detalhes": json.dumps(detalhes or {}),
        }
        requests.post(url, headers=_supabase_headers(),
                       data=json.dumps(payload), timeout=10)
    except Exception:
        pass

    try:
        _enviar_email_log(usuario, maquina, machine_id, acao, detalhes)
    except Exception:
        pass


def log_async(acao, detalhes=None):
    import threading
    mid = gerar_machine_id()
    t = threading.Thread(target=registrar_log, args=(mid, acao, detalhes), daemon=True)
    t.start()


def _enviar_email_log(usuario, maquina, machine_id, acao, detalhes):
    agora = time.strftime("%d/%m/%Y %H:%M:%S")
    acao_map = {
        "app_aberto": "abriu o aplicativo",
        "acesso_negado": "teve acesso NEGADO",
        "acesso_negado_polling": "teve acesso NEGADO",
        "solicitacao_enviada": "solicitou acesso",
        "dimp_processamento_iniciado": "iniciou processamento DIMP",
        "dimp_processamento_concluido": "concluiu processamento DIMP",
        "dimp_processamento_erro": "erro no processamento DIMP",
    }
    acao_desc = acao_map.get(acao, acao)

    modo = ""
    if detalhes and isinstance(detalhes, dict):
        parts = []
        m = detalhes.get("modo", "")
        if m == "cache_local":
            parts.append("Acesso previamente aprovado")
        elif m == "aprovacao_inicial":
            parts.append("Primeira aprovacao")
        elif m == "aprovacao_polling":
            parts.append("Aprovado em tempo real")
        for k, v in detalhes.items():
            if k == "modo":
                continue
            parts.append(f"{k}: {v}")
        modo = " | ".join(parts)

    cor = "#4FB8A8" if "negado" not in acao and "erro" not in acao else "#DC2626"

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px 0;">
      <div style="border-left:4px solid {cor};padding-left:16px;margin-bottom:24px;">
        <h2 style="color:#1B2E5C;margin:0 0 2px 0;font-size:17px;">OneKey Payments DIMP</h2>
        <p style="color:#6B7E8D;margin:0;font-size:12px;">Log de uso em tempo real</p>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr>
          <td style="padding:10px 12px;color:#6B7E8D;background:#F8FAFB;width:110px;border-bottom:1px solid #EEF2F6;">Usuario</td>
          <td style="padding:10px 12px;color:#1E293B;font-weight:600;background:#F8FAFB;border-bottom:1px solid #EEF2F6;">{usuario}</td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#6B7E8D;border-bottom:1px solid #EEF2F6;">Maquina</td>
          <td style="padding:10px 12px;color:#1E293B;border-bottom:1px solid #EEF2F6;">{maquina}</td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#6B7E8D;background:#F8FAFB;border-bottom:1px solid #EEF2F6;">Acao</td>
          <td style="padding:10px 12px;color:{cor};font-weight:700;background:#F8FAFB;border-bottom:1px solid #EEF2F6;">{acao_desc}</td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#6B7E8D;border-bottom:1px solid #EEF2F6;">Data/Hora</td>
          <td style="padding:10px 12px;color:#1E293B;border-bottom:1px solid #EEF2F6;">{agora}</td>
        </tr>
        {"<tr><td style='padding:10px 12px;color:#6B7E8D;background:#F8FAFB;'>Detalhe</td><td style='padding:10px 12px;color:#1E293B;background:#F8FAFB;'>" + modo + "</td></tr>" if modo else ""}
      </table>
      <p style="color:#B0BEC5;font-size:10px;margin-top:20px;">Machine ID: {machine_id[:24]}... | OneKey DIMP v1.0.0</p>
    </div>
    """

    requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": "onboarding@resend.dev",
            "to": [EMAIL_DESTINO],
            "subject": f"[OneKey DIMP] {usuario} {acao_desc}",
            "html": html,
        },
        timeout=10,
    )


def _carregar_logo_acesso(size=64):
    path = caminho_recurso("logo_onekey.png")
    if os.path.exists(path):
        pix = QPixmap(path)
        if not pix.isNull():
            return pix.scaledToHeight(size, Qt.SmoothTransformation)
    return None


SS_ACESSO = """
QDialog {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #F8FAFC, stop:1 #F0F4F8);
}
QLabel { background: transparent; border: none; }
QFrame { border: none; }
"""


class TelaAcesso(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OneKey Payments DIMP")
        self.setModal(True)
        self.resize(620, 400)
        self.setMinimumSize(540, 360)
        self.setStyleSheet(SS_ACESSO)

        self.session_id = str(uuid.uuid4())
        self.machine_id = gerar_machine_id()
        self.usuario_windows = getpass.getuser()
        self.nome_maquina = socket.gethostname()
        self.acesso_liberado = False
        self._polling = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_status)

        self._montar_tela()

        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        QTimer.singleShot(300, self.verificar_status_inicial)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(150, self._force_focus)

    def _force_focus(self):
        self.activateWindow()
        self.raise_()
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _montar_tela(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(0)

        # Header: logo + titulo
        header = QHBoxLayout()
        header.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(2)

        eyebrow = QLabel("DIMP PROCESSOR")
        eyebrow.setFont(QFont("Segoe UI", 9, QFont.Bold))
        eyebrow.setStyleSheet("color:#4FB8A8; letter-spacing:2px;")
        left.addWidget(eyebrow)

        title = QLabel("OneKey Payments")
        title.setFont(QFont("Segoe UI", 22, QFont.ExtraBold))
        title.setStyleSheet("color:#1B2E5C;")
        left.addWidget(title)

        subtitle = QLabel("Acesso seguro ao processador DIMP")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color:#6B7E8D;")
        subtitle.setWordWrap(True)
        left.addWidget(subtitle)

        header.addLayout(left, 1)

        logo = QLabel()
        pix = _carregar_logo_acesso(56)
        if pix:
            logo.setPixmap(pix)
        header.addWidget(logo, 0, Qt.AlignTop | Qt.AlignRight)

        root.addLayout(header)
        root.addSpacing(20)

        # Linha separadora teal
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                           "stop:0 #1B2E5C, stop:0.4 #4FB8A8, stop:1 transparent);")
        root.addWidget(line)
        root.addSpacing(20)

        # Info do usuario
        info = QHBoxLayout()
        info.setSpacing(40)

        col1 = QVBoxLayout()
        col1.setSpacing(2)
        lb_user_title = QLabel("USUARIO")
        lb_user_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lb_user_title.setStyleSheet("color:#4FB8A8; letter-spacing:1px;")
        col1.addWidget(lb_user_title)

        self.lb_nome = QLabel(self.usuario_windows)
        self.lb_nome.setFont(QFont("Segoe UI", 14, QFont.DemiBold))
        self.lb_nome.setStyleSheet("color:#1E293B;")
        col1.addWidget(self.lb_nome)

        lb_machine = QLabel(self.nome_maquina)
        lb_machine.setFont(QFont("Segoe UI", 9))
        lb_machine.setStyleSheet("color:#94A3B8;")
        col1.addWidget(lb_machine)
        info.addLayout(col1, 1)

        col2 = QVBoxLayout()
        col2.setSpacing(2)
        lb_id_title = QLabel("ID DA ESTACAO")
        lb_id_title.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lb_id_title.setStyleSheet("color:#4FB8A8; letter-spacing:1px;")
        col2.addWidget(lb_id_title)

        hash_short = f"{self.machine_id[:16]}...{self.machine_id[-8:]}"
        self.lb_hash = QLabel(hash_short)
        self.lb_hash.setFont(QFont("Consolas", 10))
        self.lb_hash.setStyleSheet("color:#64748B;")
        self.lb_hash.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lb_hash.setToolTip(self.machine_id)
        col2.addWidget(self.lb_hash)

        lb_hint = QLabel("Identificador unico desta maquina")
        lb_hint.setFont(QFont("Segoe UI", 8))
        lb_hint.setStyleSheet("color:#94A3B8;")
        col2.addWidget(lb_hint)
        info.addLayout(col2, 1)

        root.addLayout(info)
        root.addSpacing(24)

        # Status
        self.lbl_status = QLabel("Verificando acesso...")
        self.lbl_status.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lbl_status.setStyleSheet("color:#475569;")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        self.lbl_detail = QLabel("Aguarde enquanto validamos sua estacao.")
        self.lbl_detail.setFont(QFont("Segoe UI", 9))
        self.lbl_detail.setStyleSheet("color:#94A3B8;")
        self.lbl_detail.setWordWrap(True)
        root.addWidget(self.lbl_detail)

        root.addStretch(1)

        # Botoes
        botoes = QHBoxLayout()
        botoes.setSpacing(10)

        self.btn_solicitar = QPushButton("Solicitar liberacao")
        self.btn_solicitar.setCursor(Qt.PointingHandCursor)
        self.btn_solicitar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_solicitar.setMinimumHeight(40)
        self.btn_solicitar.setMinimumWidth(180)
        self.btn_solicitar.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #3DA898, stop:1 #4FB8A8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 24px;
            }
            QPushButton:hover { background: #359688; }
            QPushButton:pressed { background: #2E8577; }
            QPushButton:disabled { background: #B8D4CF; color: #E0EDEA; }
        """)
        self.btn_solicitar.clicked.connect(self.solicitar_acesso)
        botoes.addWidget(self.btn_solicitar)

        self.btn_fechar = QPushButton("Fechar")
        self.btn_fechar.setCursor(Qt.PointingHandCursor)
        self.btn_fechar.setFont(QFont("Segoe UI", 10))
        self.btn_fechar.setMinimumHeight(40)
        self.btn_fechar.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 0 24px;
            }
            QPushButton:hover { background: #F1F5F9; }
        """)
        self.btn_fechar.clicked.connect(self.reject)
        botoes.addWidget(self.btn_fechar)

        botoes.addStretch()
        root.addLayout(botoes)

    def _set_status(self, texto, detalhe="", erro=False):
        cor = "#C54B68" if erro else "#475569"
        self.lbl_status.setStyleSheet(f"color:{cor};")
        self.lbl_status.setText(texto)
        if detalhe:
            self.lbl_detail.setText(detalhe)

    def verificar_status_inicial(self):
        if _verificar_aprovacao_local(self.machine_id):
            self.acesso_liberado = True
            self._set_status("Acesso validado", "Carregando aplicativo...")
            self.btn_solicitar.setVisible(False)
            registrar_log(self.machine_id, "app_aberto", {"modo": "cache_local"})
            QTimer.singleShot(400, self.accept)
            return

        try:
            registro = consultar_status_acesso(self.session_id, self.machine_id)
            if not registro:
                self._set_status(
                    "Acesso pendente",
                    "Clique em 'Solicitar liberacao' para enviar sua solicitacao."
                )
                return

            status = (registro.get("status") or "").lower()

            if status == "aprovado":
                self.acesso_liberado = True
                _salvar_aprovacao(self.machine_id)
                registrar_log(self.machine_id, "app_aberto", {"modo": "aprovacao_inicial"})
                self._set_status("Acesso aprovado", "Abrindo aplicativo...")
                QTimer.singleShot(500, self.accept)
                return
            if status == "negado":
                registrar_log(self.machine_id, "acesso_negado")
                self._set_status("Acesso negado", "Contate o administrador.", erro=True)
                return
            if status == "pendente":
                self._set_status(
                    "Solicitacao em analise",
                    "O aplicativo sera aberto automaticamente apos aprovacao."
                )
                self.iniciar_polling()
                return

        except Exception as e:
            self._set_status("Falha na verificacao", str(e), erro=True)

    def solicitar_acesso(self):
        try:
            self.btn_solicitar.setEnabled(False)
            solicitar_acesso_remoto(self.machine_id, self.session_id)
            self._set_status(
                "Solicitacao enviada",
                "Aguardando aprovacao do administrador..."
            )
            self.iniciar_polling()
        except Exception as e:
            self.btn_solicitar.setEnabled(True)
            self._set_status("Falha ao solicitar", str(e), erro=True)

    def iniciar_polling(self):
        if self._polling:
            return
        self._polling = True
        self.timer.start(CHECK_INTERVAL_MS)

    def _poll_status(self):
        try:
            registro = consultar_status_acesso(self.session_id, self.machine_id)
            status = (registro or {}).get("status", "").lower()

            if status == "aprovado":
                self.timer.stop()
                self._polling = False
                self.acesso_liberado = True
                _salvar_aprovacao(self.machine_id)
                registrar_log(self.machine_id, "app_aberto", {"modo": "aprovacao_polling"})
                self._set_status("Acesso aprovado", "Abrindo aplicativo...")
                QTimer.singleShot(500, self.accept)
                return
            if status == "negado":
                self.timer.stop()
                self._polling = False
                registrar_log(self.machine_id, "acesso_negado_polling")
                self.btn_solicitar.setEnabled(True)
                self._set_status("Acesso negado", "Contate o administrador.", erro=True)
                return

        except Exception:
            pass
