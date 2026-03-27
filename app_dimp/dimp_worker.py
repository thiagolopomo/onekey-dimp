#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Worker thread para processamento DIMP."""

from PySide6.QtCore import QThread, Signal
from dimp_logic import processar_dimp, CLIENTES_EXCLUIR, ANO


class DimpWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, base_path: str, ano: str = ANO,
                 clientes_excluir: list = None):
        super().__init__()
        self.base_path = base_path
        self.ano = ano
        self.clientes_excluir = clientes_excluir or CLIENTES_EXCLUIR

    def run(self):
        try:
            result = processar_dimp(
                base_path=self.base_path,
                ano=self.ano,
                clientes_excluir=self.clientes_excluir,
                callback_log=self.log_signal.emit,
                callback_progress=self.progress_signal.emit,
            )
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))
