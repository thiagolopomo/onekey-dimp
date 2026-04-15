#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shell Premium - OneKey Payments DIMP
Interface moderna com header elegante, cards animados, icones vetoriais.
"""

import os
import getpass
import glob
from pathlib import Path

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QSize,
    QPoint, QParallelAnimationGroup, QSequentialAnimationGroup,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QTextEdit, QProgressBar,
    QGraphicsDropShadowEffect, QLineEdit, QGraphicsOpacityEffect,
    QScrollArea, QSizePolicy,
)
from PySide6.QtGui import (
    QFont, QColor, QPixmap, QPainter, QPainterPath, QLinearGradient,
    QPen, QBrush, QIcon,
)

from resources import carregar_logo, caminho_recurso
from dimp_worker import DimpWorker
from dimp_logic import CLIENTES_EXCLUIR
from access import log_async


# ════════════════════════════════════════
# VECTOR ICONS (desenhados programaticamente)
# ════════════════════════════════════════

def _icon_folder(size=20, color="#4FB8A8"):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.5)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = size
    # Folder shape
    path = QPainterPath()
    path.moveTo(s*0.1, s*0.25)
    path.lineTo(s*0.1, s*0.8)
    path.lineTo(s*0.9, s*0.8)
    path.lineTo(s*0.9, s*0.35)
    path.lineTo(s*0.5, s*0.35)
    path.lineTo(s*0.42, s*0.25)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pix


def _icon_chart(size=20, color="#4FB8A8"):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    p.setPen(pen)
    s = size
    # Bar chart
    p.drawLine(int(s*0.15), int(s*0.85), int(s*0.85), int(s*0.85))
    p.drawLine(int(s*0.15), int(s*0.15), int(s*0.15), int(s*0.85))
    # Bars
    bar_color = QColor(color)
    bar_color.setAlpha(180)
    p.setBrush(bar_color)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(int(s*0.22), int(s*0.55), int(s*0.12), int(s*0.28), 2, 2)
    p.drawRoundedRect(int(s*0.40), int(s*0.35), int(s*0.12), int(s*0.48), 2, 2)
    p.drawRoundedRect(int(s*0.58), int(s*0.50), int(s*0.12), int(s*0.33), 2, 2)
    p.drawRoundedRect(int(s*0.76), int(s*0.25), int(s*0.12), int(s*0.58), 2, 2)
    p.end()
    return pix


def _icon_check(size=20, color="#4FB8A8"):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    s = size
    # Circle
    p.drawEllipse(int(s*0.1), int(s*0.1), int(s*0.8), int(s*0.8))
    # Checkmark
    path = QPainterPath()
    path.moveTo(s*0.28, s*0.52)
    path.lineTo(s*0.44, s*0.68)
    path.lineTo(s*0.72, s*0.35)
    p.drawPath(path)
    p.end()
    return pix


def _icon_lightning(size=20, color="#F59E0B"):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    s = size
    path = QPainterPath()
    path.moveTo(s*0.55, s*0.08)
    path.lineTo(s*0.25, s*0.50)
    path.lineTo(s*0.45, s*0.50)
    path.lineTo(s*0.40, s*0.92)
    path.lineTo(s*0.75, s*0.42)
    path.lineTo(s*0.55, s*0.42)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pix


def _icon_database(size=20, color="#1B2E5C"):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.5)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    s = size
    # Top ellipse
    p.drawEllipse(int(s*0.15), int(s*0.12), int(s*0.7), int(s*0.2))
    # Sides
    p.drawLine(int(s*0.15), int(s*0.22), int(s*0.15), int(s*0.78))
    p.drawLine(int(s*0.85), int(s*0.22), int(s*0.85), int(s*0.78))
    # Bottom ellipse
    p.drawArc(int(s*0.15), int(s*0.68), int(s*0.7), int(s*0.2), 0, -180*16)
    # Middle line
    p.drawArc(int(s*0.15), int(s*0.40), int(s*0.7), int(s*0.2), 0, -180*16)
    p.end()
    return pix


def _icon_sparkle(size=18, color="#4FB8A8"):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    s = size
    # 4-point star
    path = QPainterPath()
    path.moveTo(s*0.5, s*0.05)
    path.cubicTo(s*0.52, s*0.35, s*0.65, s*0.48, s*0.95, s*0.5)
    path.cubicTo(s*0.65, s*0.52, s*0.52, s*0.65, s*0.5, s*0.95)
    path.cubicTo(s*0.48, s*0.65, s*0.35, s*0.52, s*0.05, s*0.5)
    path.cubicTo(s*0.35, s*0.48, s*0.48, s*0.35, s*0.5, s*0.05)
    p.drawPath(path)
    p.end()
    return pix


def _create_avatar(initials: str, size: int = 36):
    """Cria avatar circular com iniciais."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    # Circle gradient
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor("#4FB8A8"))
    grad.setColorAt(1, QColor("#3DA898"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, size, size)
    # Initials
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", int(size * 0.35), QFont.DemiBold))
    p.drawText(pix.rect(), Qt.AlignCenter, initials.upper()[:2])
    p.end()
    return pix


# ════════════════════════════════════════
# METRIC CARD ANIMADO
# ════════════════════════════════════════

class MetricCard(QFrame):
    def __init__(self, icon_pix, label, value="--", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setFixedHeight(80)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(icon_pix)
        icon_label.setFixedSize(24, 24)
        icon_label.setStyleSheet("background: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.lb_label = QLabel(label)
        self.lb_label.setFont(QFont("Segoe UI", 8, QFont.Normal))
        self.lb_label.setStyleSheet("color: #94A3B8; background: transparent;")
        text_col.addWidget(self.lb_label)

        self.lb_value = QLabel(value)
        self.lb_value.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lb_value.setStyleSheet("color: #1E293B; background: transparent;")
        self.lb_value.setWordWrap(False)
        self.lb_value.setMinimumWidth(160)
        text_col.addWidget(self.lb_value)

        # Tamanho fixo do card
        self.setFixedHeight(68)
        self.setMinimumWidth(200)

        layout.addLayout(text_col, 1)

    def set_value(self, val: str, color: str = "#1E293B"):
        self.lb_value.setText(val)
        self.lb_value.setStyleSheet(f"color: {color}; background: transparent;")

    def set_label(self, text: str):
        self.lb_label.setText(text)


# ════════════════════════════════════════
# MAIN SHELL
# ════════════════════════════════════════

class MainShell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OneKey Payments - DIMP Processor")
        self.setObjectName("ShellWindow")
        self.setFixedSize(920, 700)

        self._worker = None
        self._pasta_saida = None
        self._montar_ui()

        # Animar entrada
        QTimer.singleShot(100, self._animar_entrada)

    def _montar_ui(self):
        central = QWidget()
        central.setObjectName("ShellWindow")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ══════════════════════════════
        # TOP BAR PREMIUM
        # ══════════════════════════════
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(56)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(22, 0, 22, 0)
        tb.setSpacing(14)

        # Logo
        logo_label = QLabel()
        pix = carregar_logo(28)
        if pix:
            logo_label.setPixmap(pix)
        logo_label.setStyleSheet("background: transparent;")
        tb.addWidget(logo_label)

        # Separador vertical sutil
        sep_v = QFrame()
        sep_v.setFixedSize(1, 24)
        sep_v.setStyleSheet("background: rgba(255,255,255,0.12);")
        tb.addWidget(sep_v)

        # Titulo
        title = QLabel("DIMP Processor")
        title.setFont(QFont("Segoe UI", 13, QFont.Normal))
        title.setStyleSheet("color: rgba(255,255,255,0.9); background: transparent; letter-spacing: 0.5px;")
        tb.addWidget(title)

        # Sparkle icon
        sparkle = QLabel()
        sparkle.setPixmap(_icon_sparkle(14, "#4FB8A8"))
        sparkle.setStyleSheet("background: transparent;")
        tb.addWidget(sparkle)

        tb.addStretch()

        # Versao badge
        ver_badge = QLabel("v1.1.2")
        ver_badge.setFont(QFont("Segoe UI", 8, QFont.Normal))
        ver_badge.setStyleSheet("""
            color: rgba(255,255,255,0.5);
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 3px 10px;
        """)
        tb.addWidget(ver_badge)

        tb.addSpacing(8)

        # Separador
        sep_v2 = QFrame()
        sep_v2.setFixedSize(1, 24)
        sep_v2.setStyleSheet("background: rgba(255,255,255,0.08);")
        tb.addWidget(sep_v2)

        tb.addSpacing(8)

        # User info
        username = getpass.getuser()
        initials = username[:2] if len(username) >= 2 else username[0] + "."

        avatar = QLabel()
        avatar.setPixmap(_create_avatar(initials, 30))
        avatar.setFixedSize(30, 30)
        avatar.setStyleSheet("background: transparent;")
        tb.addWidget(avatar)

        user_col = QVBoxLayout()
        user_col.setSpacing(0)
        user_col.setContentsMargins(0, 0, 0, 0)

        user_name = QLabel(username.title())
        user_name.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        user_name.setStyleSheet("color: rgba(255,255,255,0.9); background: transparent;")
        user_col.addWidget(user_name)

        user_role = QLabel("Operador")
        user_role.setFont(QFont("Segoe UI", 8))
        user_role.setStyleSheet("color: rgba(255,255,255,0.4); background: transparent;")
        user_col.addWidget(user_role)

        tb.addLayout(user_col)

        root.addWidget(topbar)

        # ══════════════════════════════
        # SCROLL AREA
        # ══════════════════════════════
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(24, 20, 24, 16)
        content_layout.setSpacing(16)

        # ── Metric cards row ──
        self.metrics_frame = QFrame()
        self.metrics_frame.setStyleSheet("background: transparent; border: none;")
        metrics_row = QHBoxLayout(self.metrics_frame)
        metrics_row.setContentsMargins(0, 0, 0, 0)
        metrics_row.setSpacing(12)

        self.card_original = MetricCard(_icon_database(20, "#1B2E5C"), "Total Original CSVs", "--")
        self.card_sem_dup = MetricCard(_icon_check(20, "#4FB8A8"), "Principais (sem dup.)", "--")
        self.card_duplicatas = MetricCard(_icon_chart(20, "#F59E0B"), "Clientes Apartados", "--")
        self.card_consistencia = MetricCard(_icon_lightning(20, "#4FB8A8"), "Consistência", "--")

        metrics_row.addWidget(self.card_original)
        metrics_row.addWidget(self.card_sem_dup)
        metrics_row.addWidget(self.card_duplicatas)
        metrics_row.addWidget(self.card_consistencia)

        content_layout.addWidget(self.metrics_frame)

        # ── Card principal ──
        card = QFrame()
        card.setObjectName("MainCard")
        self._main_card = card

        # Sem QGraphicsDropShadowEffect - causa rendering bugado em child widgets

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        # Header do card
        card_header = QHBoxLayout()
        card_header.setSpacing(10)

        folder_icon = QLabel()
        folder_icon.setPixmap(_icon_folder(22, "#4FB8A8"))
        folder_icon.setStyleSheet("background: transparent;")
        card_header.addWidget(folder_icon)

        card_title = QLabel("Processamento DIMP")
        card_title.setFont(QFont("Segoe UI", 15, QFont.DemiBold))
        card_title.setStyleSheet("color: #1B2E5C; background: transparent;")
        card_header.addWidget(card_title)

        card_header.addStretch()

        # Status badge
        self.status_badge = QLabel("")
        self.status_badge.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        self.status_badge.setStyleSheet("""
            color: #94A3B8;
            background: rgba(148, 163, 184, 0.1);
            border-radius: 10px;
            padding: 4px 12px;
        """)
        self.status_badge.setVisible(False)
        card_header.addWidget(self.status_badge)

        card_layout.addLayout(card_header)

        card_desc = QLabel(
            "Selecione a pasta com os arquivos OPERATIONS_BY_RECEIPT_*.csv"
        )
        card_desc.setFont(QFont("Segoe UI", 10))
        card_desc.setStyleSheet("color: #94A3B8; background: transparent;")
        card_layout.addWidget(card_desc)

        # Separador com gradiente
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 rgba(79,184,168,0.3), stop:0.5 rgba(229,234,240,0.5), stop:1 transparent);
        """)
        card_layout.addWidget(sep)

        # Path row
        path_row = QHBoxLayout()
        path_row.setSpacing(10)

        path_icon = QLabel()
        path_icon.setPixmap(_icon_folder(18, "#94A3B8"))
        path_icon.setStyleSheet("background: transparent;")
        path_icon.setFixedWidth(20)
        path_row.addWidget(path_icon)

        self.path_input = QLineEdit()
        self.path_input.setObjectName("PathInput")
        self.path_input.setPlaceholderText("Caminho da pasta com os CSVs...")
        self.path_input.setFont(QFont("Segoe UI", 10))
        self.path_input.setFixedHeight(40)
        path_row.addWidget(self.path_input)

        btn_browse = QPushButton("Selecionar")
        btn_browse.setObjectName("BtnSecondary")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        btn_browse.setFixedHeight(40)
        btn_browse.clicked.connect(self._selecionar_pasta)
        path_row.addWidget(btn_browse)

        card_layout.addLayout(path_row)

        # Botoes
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_processar = QPushButton("  Processar DIMP")
        self.btn_processar.setCursor(Qt.PointingHandCursor)
        self.btn_processar.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.btn_processar.setFixedHeight(46)
        self.btn_processar.setMinimumWidth(200)
        self.btn_processar.setIcon(QIcon(_icon_lightning(18, "#FFFFFF")))
        self.btn_processar.setIconSize(QSize(18, 18))
        self.btn_processar.setStyleSheet("""
            QPushButton {
                background-color: #1B6B5F;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 10px 32px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #155A50;
            }
            QPushButton:pressed {
                background-color: #104A42;
            }
            QPushButton:disabled {
                background-color: #A0C4BE;
                color: rgba(255,255,255,0.8);
            }
        """)
        self.btn_processar.clicked.connect(self._iniciar_processamento)
        btn_row.addWidget(self.btn_processar)

        self.btn_abrir = QPushButton("  Abrir Pasta de Saida")
        self.btn_abrir.setObjectName("BtnOpen")
        self.btn_abrir.setCursor(Qt.PointingHandCursor)
        self.btn_abrir.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.btn_abrir.setFixedHeight(44)
        self.btn_abrir.setIcon(QIcon(_icon_folder(16, "#1B2E5C")))
        self.btn_abrir.setIconSize(QSize(16, 16))
        self.btn_abrir.setVisible(False)
        self.btn_abrir.clicked.connect(self._abrir_pasta_saida)
        btn_row.addWidget(self.btn_abrir)

        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(10)
        self.progress.setVisible(False)
        card_layout.addWidget(self.progress)

        content_layout.addWidget(card)

        # ── Log area ──
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Cascadia Code", 10))
        self.log_area.setMinimumHeight(140)
        self.log_area.setPlaceholderText("Os logs do processamento aparecerao aqui...")
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #E8ECF1;
                border: none;
                border-radius: 14px;
                padding: 16px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
                selection-background-color: rgba(79, 184, 168, 0.3);
            }
        """)

        content_layout.addWidget(self.log_area, 1)

        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        # ── Footer ──
        footer = QFrame()
        footer.setObjectName("Footer")
        footer.setFixedHeight(34)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)

        ft_left = QLabel("OneKey Payments DIMP v1.1.2")
        ft_left.setFont(QFont("Segoe UI", 9))
        fl.addWidget(ft_left)

        fl.addStretch()

        # Dot separator
        dot = QLabel("  ·  ")
        dot.setStyleSheet("color: #CBD5E1; background: transparent;")
        dot.setFont(QFont("Segoe UI", 9))

        ft_right = QLabel("Powered by Andersen")
        ft_right.setFont(QFont("Segoe UI", 9))
        fl.addWidget(ft_right)
        fl.addWidget(dot)

        ft_dev = QLabel("Thiago Lopomo")
        ft_dev.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        ft_dev.setStyleSheet("color: #64748B; background: transparent;")
        fl.addWidget(ft_dev)

        root.addWidget(footer)

    # ════════════════════════════════════════
    # ANIMACOES
    # ════════════════════════════════════════

    def _animar_entrada(self):
        """Anima a entrada dos metric cards com fade (sem tocar no main card)."""
        metric_cards = [
            self.card_original,
            self.card_sem_dup,
            self.card_duplicatas,
            self.card_consistencia,
        ]

        for i, w in enumerate(metric_cards):
            opacity = QGraphicsOpacityEffect(w)
            opacity.setOpacity(0.0)
            w.setGraphicsEffect(opacity)

            anim_fade = QPropertyAnimation(opacity, b"opacity")
            anim_fade.setDuration(450)
            anim_fade.setStartValue(0.0)
            anim_fade.setEndValue(1.0)
            anim_fade.setEasingCurve(QEasingCurve.OutCubic)

            QTimer.singleShot(100 * i, anim_fade.start)

            w._anim_fade = anim_fade
            w._opacity_fx = opacity

    def _animar_valor_card(self, card: MetricCard, valor_final: float,
                           prefix: str = "R$ ", color: str = "#1E293B"):
        """Anima o valor do card de 0 ate o valor final (counter effect)."""
        steps = 25
        interval = 30  # ms
        valor_atual = [0.0]
        step_val = valor_final / steps if steps > 0 else valor_final

        def _step():
            valor_atual[0] += step_val
            if valor_atual[0] >= valor_final:
                valor_atual[0] = valor_final
                card.set_value(f"{prefix}{valor_atual[0]:,.2f}", color)
                return
            card.set_value(f"{prefix}{valor_atual[0]:,.2f}", color)
            QTimer.singleShot(interval, _step)

        _step()

    def _animar_cards_resultado(self, result: dict):
        """Anima os cards com os resultados do processamento."""
        total = result.get("TOTAL_GERAL", 0)
        excluindo = result.get("TOTAL_EXCLUINDO", 0)
        somente = result.get("TOTAL_SOMENTE_EXCL", 0)

        # Card 1: Total original
        self.card_original.set_label("Total Original CSVs")
        QTimer.singleShot(100, lambda: self._animar_valor_card(
            self.card_original, total, "R$ ", "#1B2E5C"))

        # Card 2: Sem duplicatas (principais)
        self.card_sem_dup.set_label("Principais (sem dup.)")
        QTimer.singleShot(250, lambda: self._animar_valor_card(
            self.card_sem_dup, excluindo, "R$ ", "#4FB8A8"))

        # Card 3: Apartados
        self.card_duplicatas.set_label("Clientes Apartados")
        QTimer.singleShot(400, lambda: self._animar_valor_card(
            self.card_duplicatas, somente, "R$ ", "#F59E0B"))

        # Card 4: Consistencia
        diff = abs(total - (excluindo + somente))
        QTimer.singleShot(550, lambda: self._set_consistencia(diff, total, excluindo, somente))

    def _set_consistencia(self, diff, total, excl, somente):
        if diff < 0.01:
            self.card_consistencia.set_value("OK", "#4FB8A8")
            self.card_consistencia.set_label("Consistencia verificada")
        else:
            self.card_consistencia.set_value(f"Diff: {diff:,.2f}", "#EF4444")
            self.card_consistencia.set_label("Inconsistencia!")

    # ════════════════════════════════════════
    # ACOES
    # ════════════════════════════════════════

    def _selecionar_pasta(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta com os CSVs DIMP",
            str(Path.home() / "Downloads")
        )
        if folder:
            self.path_input.setText(folder)

    def _iniciar_processamento(self):
        pasta = self.path_input.text().strip()
        if not pasta or not os.path.isdir(pasta):
            self._set_status("Selecione uma pasta valida", "error")
            return

        csvs = glob.glob(os.path.join(pasta, "OPERATIONS_BY_RECEIPT_*.csv"))
        if not csvs:
            self._set_status("Nenhum CSV encontrado", "error")
            return

        # Reset
        self.log_area.clear()
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.btn_processar.setEnabled(False)
        self.btn_abrir.setVisible(False)
        self._set_status("Processando...", "pending")

        # Reset cards
        for c in [self.card_original, self.card_sem_dup, self.card_duplicatas, self.card_consistencia]:
            c.set_value("--")

        log_async("dimp_processamento_iniciado", {"pasta": pasta, "csvs": len(csvs)})

        self._worker = DimpWorker(pasta)
        self._worker.log_signal.connect(self._on_log)
        self._worker.progress_signal.connect(self._on_progress)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _set_status(self, text, tipo="info"):
        colors = {
            "info": ("#94A3B8", "rgba(148, 163, 184, 0.1)"),
            "pending": ("#F59E0B", "rgba(245, 158, 11, 0.1)"),
            "ok": ("#4FB8A8", "rgba(79, 184, 168, 0.1)"),
            "error": ("#EF4444", "rgba(239, 68, 68, 0.1)"),
        }
        cor, bg = colors.get(tipo, colors["info"])
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(f"""
            color: {cor};
            background: {bg};
            border-radius: 10px;
            padding: 4px 12px;
        """)
        self.status_badge.setVisible(True)

    def _on_log(self, msg):
        self.log_area.append(msg)
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_progress(self, pct):
        self.progress.setValue(pct)

    def _on_finished(self, result):
        self.btn_processar.setEnabled(True)
        self.progress.setValue(100)
        self._set_status("Concluido", "ok")

        self._pasta_saida = result.get("pasta_saida", "")
        if self._pasta_saida:
            self.btn_abrir.setVisible(True)

        # Animar cards com resultado
        self._animar_cards_resultado(result)

        log_async("dimp_processamento_concluido", {
            "total_geral": result.get("TOTAL_GERAL", 0),
            "total_excluindo": result.get("TOTAL_EXCLUINDO", 0),
            "total_somente_excl": result.get("TOTAL_SOMENTE_EXCL", 0),
        })

        self._worker = None

    def _on_error(self, msg):
        self.btn_processar.setEnabled(True)
        self.progress.setVisible(False)
        self._set_status("Erro", "error")
        self._on_log(f"\nERRO: {msg}")

        log_async("dimp_processamento_erro", {"erro": msg[:200]})
        self._worker = None

    def _abrir_pasta_saida(self):
        if self._pasta_saida and os.path.isdir(self._pasta_saida):
            os.startfile(self._pasta_saida)
