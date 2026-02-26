"""Frame extraction / thumbnail page."""

import os
from pathlib import Path

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from chevalvideo.probe import probe, summarize
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

IMG_FORMATS = [
    {"value": "png", "label": "PNG", "description": "Lossless"},
    {"value": "jpg", "label": "JPG", "description": "Smaller file"},
]


class ThumbnailPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Thumbnail")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # Timestamp
        ts_row = QHBoxLayout()
        ts_row.addWidget(QLabel("Timestamp:"))
        self._ts_input = QLineEdit()
        self._ts_input.setPlaceholderText("00:00:05")
        self._ts_input.setFixedWidth(120)
        ts_row.addWidget(self._ts_input)
        ts_row.addStretch()
        layout.addLayout(ts_row)

        layout.addWidget(QLabel("Image format:"))
        self._fmt_grid = OptionGrid(columns=2)
        self._fmt_grid.set_options(IMG_FORMATS)
        layout.addWidget(self._fmt_grid)

        self._go_btn = QPushButton("Extract Frame")
        self._go_btn.clicked.connect(self._run)
        self._go_btn.setEnabled(False)
        layout.addWidget(self._go_btn)

        self._progress = ProgressWidget()
        self._progress.cancel_button.clicked.connect(self._runner.cancel)
        layout.addWidget(self._progress)

        self._runner.progress.connect(self._progress.set_progress)
        self._runner.output.connect(self._progress.append_log)
        self._runner.finished.connect(self._on_done)

        layout.addStretch()
        self._fmt_grid.select("png")

    def _on_file(self, path):
        self._input_path = path
        try:
            info = probe(path)
            self._info.set_info(summarize(info))
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._go_btn.setEnabled(True)

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        ts = self._ts_input.text().strip() or "00:00:00"
        fmt_sel = self._fmt_grid.selected()
        fmt = fmt_sel[0] if fmt_sel else "png"

        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_thumb.{fmt}")

        cmd = [
            "ffmpeg", "-y", "-ss", ts, "-i", self._input_path,
            "-frames:v", "1",
            out_path,
        ]

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd)

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
