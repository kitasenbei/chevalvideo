"""Displays ffprobe summary in a formatted layout."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget


class MediaInfoWidget(QWidget):
    """Shows probe info as a grid of key-value labels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(4)
        self._labels: list[tuple[QLabel, QLabel]] = []

    def set_info(self, summary: dict):
        """Populate with a probe summary dict."""
        self._clear()
        display_keys = [
            ("format", "Format"),
            ("resolution", "Resolution"),
            ("duration", "Duration"),
            ("size", "Size"),
            ("video_codec", "Video"),
            ("audio_codec", "Audio"),
            ("fps", "FPS"),
            ("bitrate", "Bitrate"),
            ("sample_rate", "Sample Rate"),
            ("channels", "Channels"),
        ]
        row = 0
        for key, label in display_keys:
            val = summary.get(key)
            if not val:
                continue
            k = QLabel(f"{label}:")
            k.setObjectName("subheading")
            k.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            v = QLabel(str(val))
            self._grid.addWidget(k, row, 0)
            self._grid.addWidget(v, row, 1)
            self._labels.append((k, v))
            row += 1

    def _clear(self):
        for k, v in self._labels:
            self._grid.removeWidget(k)
            self._grid.removeWidget(v)
            k.deleteLater()
            v.deleteLater()
        self._labels.clear()
