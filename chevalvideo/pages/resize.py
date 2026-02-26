"""Resolution scaling page."""

import os
from pathlib import Path

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

PRESETS = [
    {"value": "3840:-2", "label": "4K", "description": "3840px wide"},
    {"value": "1920:-2", "label": "1080p", "description": "1920px wide"},
    {"value": "1280:-2", "label": "720p", "description": "1280px wide"},
    {"value": "854:-2", "label": "480p", "description": "854px wide"},
]


class ResizePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Resize")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        layout.addWidget(QLabel("Resolution:"))
        self._preset_grid = OptionGrid(columns=4)
        self._preset_grid.set_options(PRESETS)
        layout.addWidget(self._preset_grid)

        # Custom
        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Custom scale:"))
        self._custom_input = QLineEdit()
        self._custom_input.setPlaceholderText("e.g. 640:-2")
        self._custom_input.setFixedWidth(160)
        custom_row.addWidget(self._custom_input)
        custom_row.addStretch()
        layout.addLayout(custom_row)

        self._go_btn = QPushButton("Resize")
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
        self._preset_grid.select("1920:-2")

    def _on_file(self, path):
        self._input_path = path
        try:
            info = probe(path)
            self._duration = get_duration_secs(info)
            self._info.set_info(summarize(info))
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._go_btn.setEnabled(True)

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        custom = self._custom_input.text().strip()
        preset_sel = self._preset_grid.selected()
        scale = custom if custom else (preset_sel[0] if preset_sel else "1920:-2")

        ext = Path(self._input_path).suffix
        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_resized{ext}")

        cmd = [
            "ffmpeg", "-y", "-i", self._input_path,
            "-vf", f"scale={scale}",
            "-c:a", "copy",
            "-progress", "pipe:1", out_path,
        ]

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
