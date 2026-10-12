"""A tiny QThread wrapper: run a callable off the UI thread, stream progress lines back."""
from __future__ import annotations

import traceback
from typing import Callable

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable, *args, parent=None, **kwargs):
        super().__init__(parent)
        self._fn, self._args, self._kwargs = fn, args, kwargs

    def run(self):
        try:
            result = self._fn(*self._args, progress=self.progress.emit, **self._kwargs)
        except Exception as e:  # surfaced to the UI as one line plus the type
            self.failed.emit(f"{type(e).__name__}: {e}")
            traceback.print_exc()
            return
        self.finished_ok.emit(result)
