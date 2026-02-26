"""Drag-drop + browse file input widget."""

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)


class FileDropWidget(QWidget):
    """File input supporting drag-drop and browse dialog."""

    file_selected = pyqtSignal(str)

    def __init__(self, label="Drop a file here or click Browse", filters="Video files (*.mp4 *.mkv *.webm *.avi *.mov *.flv *.ts *.m4v);;All files (*)", parent=None):
        super().__init__(parent)
        self._filters = filters
        self.setAcceptDrops(True)

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setObjectName("subheading")
        self._label.setWordWrap(True)

        self._file_label = QLabel("")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse = QPushButton("Browse")
        browse.setFixedWidth(100)
        browse.clicked.connect(self._browse)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(browse)
        btn_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.addStretch()
        layout.addWidget(self._label)
        layout.addWidget(self._file_label)
        layout.addSpacing(8)
        layout.addLayout(btn_row)
        layout.addStretch()

        self.setStyleSheet(
            "FileDropWidget { border: 2px dashed #6272a4; border-radius: 12px; }"
        )
        self.setMinimumHeight(120)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", self._filters)
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        name = Path(path).name
        self._file_label.setText(name)
        self._label.setText("Selected:")
        self.file_selected.emit(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self._set_file(path)

    def reset(self):
        self._label.setText("Drop a file here or click Browse")
        self._file_label.setText("")
