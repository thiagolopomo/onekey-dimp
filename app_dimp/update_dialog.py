#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dialogo de atualizacao - OneKey Payments DIMP."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QFont


class UpdateDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Atualizacao disponivel")
        self.setModal(True)
        self.resize(480, 300)
        self.setMinimumSize(400, 250)

        self.info = info
        self._accepted = False

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(0)

        eyebrow = QLabel("ATUALIZACAO DISPONIVEL")
        eyebrow.setFont(QFont("Segoe UI", 9, QFont.Bold))
        eyebrow.setStyleSheet("color:#1B6B5F;letter-spacing:2px;background:transparent;")
        root.addWidget(eyebrow)

        title = QLabel("OneKey Payments - DIMP")
        title.setFont(QFont("Segoe UI", 18, QFont.ExtraBold))
        title.setStyleSheet("color:#1B2E5C;background:transparent;")
        root.addWidget(title)
        root.addSpacing(16)

        ver_row = QHBoxLayout()
        ver_row.setSpacing(24)

        col1 = QVBoxLayout()
        col1.setSpacing(2)
        lb1 = QLabel("VERSAO ATUAL")
        lb1.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lb1.setStyleSheet("color:#94A3B8;letter-spacing:1px;background:transparent;")
        col1.addWidget(lb1)
        v1 = QLabel(info.get("current", "?"))
        v1.setFont(QFont("Consolas", 16, QFont.Bold))
        v1.setStyleSheet("color:#64748B;background:transparent;")
        col1.addWidget(v1)
        ver_row.addLayout(col1)

        arrow = QLabel("->")
        arrow.setFont(QFont("Segoe UI", 16))
        arrow.setStyleSheet("color:#CBD5E1;background:transparent;")
        ver_row.addWidget(arrow, 0, Qt.AlignCenter)

        col2 = QVBoxLayout()
        col2.setSpacing(2)
        lb2 = QLabel("NOVA VERSAO")
        lb2.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lb2.setStyleSheet("color:#1B6B5F;letter-spacing:1px;background:transparent;")
        col2.addWidget(lb2)
        v2 = QLabel(info.get("version", "?"))
        v2.setFont(QFont("Consolas", 16, QFont.Bold))
        v2.setStyleSheet("color:#1B6B5F;background:transparent;")
        col2.addWidget(v2)
        ver_row.addLayout(col2)

        ver_row.addStretch()
        root.addLayout(ver_row)
        root.addSpacing(16)

        notes = info.get("notes", "")
        if notes:
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet("background:#E2E8F0;")
            root.addWidget(line)
            root.addSpacing(10)

            nl = QLabel("O QUE MUDOU")
            nl.setFont(QFont("Segoe UI", 8, QFont.Bold))
            nl.setStyleSheet("color:#94A3B8;letter-spacing:1px;background:transparent;")
            root.addWidget(nl)

            nt = QLabel(notes)
            nt.setFont(QFont("Segoe UI", 10))
            nt.setStyleSheet("color:#475569;background:transparent;")
            nt.setWordWrap(True)
            root.addWidget(nt)

        root.addStretch()

        btns = QHBoxLayout()
        btns.setSpacing(10)

        self.btn_install = QPushButton("Instalar agora")
        self.btn_install.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_install.setMinimumHeight(38)
        self.btn_install.setCursor(Qt.PointingHandCursor)
        self.btn_install.setStyleSheet(
            "QPushButton{background:#1B6B5F;color:white;border:none;"
            "border-radius:8px;padding:0 24px;}"
            "QPushButton:hover{background:#155A50;}"
        )
        self.btn_install.clicked.connect(self._on_install)
        btns.addWidget(self.btn_install)

        self.btn_later = QPushButton("Depois")
        self.btn_later.setFont(QFont("Segoe UI", 10))
        self.btn_later.setMinimumHeight(38)
        self.btn_later.setCursor(Qt.PointingHandCursor)
        self.btn_later.setStyleSheet(
            "QPushButton{background:transparent;color:#64748B;"
            "border:1px solid #CBD5E1;border-radius:8px;padding:0 24px;}"
            "QPushButton:hover{background:#F1F5F9;}"
        )
        self.btn_later.clicked.connect(self.reject)
        btns.addWidget(self.btn_later)

        if info.get("mandatory"):
            self.btn_later.setVisible(False)

        btns.addStretch()
        root.addLayout(btns)

    def _on_install(self):
        self._accepted = True
        self.accept()
