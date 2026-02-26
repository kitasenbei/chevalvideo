"""Progress bar + log output + cancel button."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)


class ProgressWidget(QWidget):
    """Shows a progress bar, scrolling log, and cancel button."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setFixedWidth(100)
        self._cancel_btn.setEnabled(False)

        bar_row = QHBoxLayout()
        bar_row.addWidget(self._bar, 1)
        bar_row.addWidget(self._cancel_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar_row)
        layout.addWidget(self._log)

    @property
    def cancel_button(self):
        return self._cancel_btn

    def set_progress(self, pct: float):
        self._bar.setValue(int(pct))

    def append_log(self, text: str):
        self._log.appendPlainText(text)

    def reset(self):
        self._bar.setValue(0)
        self._log.clear()

    def set_running(self, running: bool):
        self._cancel_btn.setEnabled(running)
