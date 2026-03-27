#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Resources OneKey Payments DIMP - Logo + icone vetorial + fontes."""

import os
import sys

from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import (
    QIcon, QPixmap, QFontDatabase, QPainter, QFont,
    QColor, QLinearGradient, QPen, QBrush, QPainterPath,
)

_BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
_ICON_CACHE = None
_LOGO_CACHE = {}
_FONT_FAMILY_CACHE = None


def caminho_recurso(*partes) -> str:
    return os.path.join(_BASE_DIR, *partes)


def _gerar_icone_okp(size: int) -> QPixmap:
    """Gera icone vetorial 'OKP' com QPainter - nitido em qualquer resolucao."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)

    margin = size * 0.08
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    radius = size * 0.22

    # Fundo: gradiente navy -> teal escuro
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#0F2027"))
    grad.setColorAt(0.5, QColor("#163A3F"))
    grad.setColorAt(1.0, QColor("#1B6B5F"))

    # Desenhar retangulo arredondado
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    p.fillPath(path, QBrush(grad))

    # Borda sutil
    p.setPen(QPen(QColor(255, 255, 255, 30), size * 0.015))
    p.drawPath(path)

    # Texto "OKP"
    font_size = size * 0.30
    font = QFont("Segoe UI", int(font_size))
    font.setWeight(QFont.Bold)
    font.setLetterSpacing(QFont.AbsoluteSpacing, size * 0.02)
    p.setFont(font)

    # Sombra do texto
    p.setPen(QColor(0, 0, 0, 60))
    shadow_rect = QRectF(rect.x() + 1, rect.y() + 2, rect.width(), rect.height())
    p.drawText(shadow_rect, Qt.AlignCenter, "OKP")

    # Texto principal: branco brilhante
    p.setPen(QColor(255, 255, 255, 240))
    p.drawText(rect, Qt.AlignCenter, "OKP")

    # Linha decorativa teal na base
    line_y = rect.bottom() - size * 0.14
    line_x1 = rect.center().x() - size * 0.22
    line_x2 = rect.center().x() + size * 0.22
    pen = QPen(QColor("#4FB8A8"), max(1.5, size * 0.025))
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(int(line_x1), int(line_y), int(line_x2), int(line_y))

    p.end()
    return pix


def obter_icone() -> QIcon:
    """Retorna QIcon vetorial multi-resolucao (16, 24, 32, 48, 64, 128, 256)."""
    global _ICON_CACHE
    if _ICON_CACHE is not None:
        return _ICON_CACHE

    icon = QIcon()
    for sz in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_gerar_icone_okp(sz))

    _ICON_CACHE = icon
    return _ICON_CACHE


def carregar_logo(altura: int = 120):
    key = f"logo_{altura}"
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    for nome in ("logo_onekey.png",):
        caminho = caminho_recurso(nome)
        if os.path.exists(caminho):
            pix = QPixmap(caminho)
            if not pix.isNull():
                result = pix.scaledToHeight(altura, Qt.SmoothTransformation)
                _LOGO_CACHE[key] = result
                return result
    return None


def carregar_fontes_app() -> str:
    global _FONT_FAMILY_CACHE
    if _FONT_FAMILY_CACHE:
        return _FONT_FAMILY_CACHE

    fonts_dir = caminho_recurso("assets", "fonts")
    familia = "Segoe UI"

    if os.path.isdir(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith((".ttf", ".otf")):
                fid = QFontDatabase.addApplicationFont(os.path.join(fonts_dir, f))
                if fid >= 0:
                    families = QFontDatabase.applicationFontFamilies(fid)
                    if families and "Inter" in families[0]:
                        familia = families[0]

    _FONT_FAMILY_CACHE = familia
    return familia
