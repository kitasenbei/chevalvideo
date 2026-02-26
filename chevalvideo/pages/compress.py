"""Smart compression page."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

PRESETS = [
    {"value": "18", "label": "High", "description": "CRF 18 — near lossless"},
    {"value": "23", "label": "Medium", "description": "CRF 23 — balanced"},
    {"value": "28", "label": "Low", "description": "CRF 28 — smaller file"},
    {"value": "target", "label": "Target Size", "description": "Specify file size"},
]

CODECS = [
    {"value": "libx264", "label": "H.264", "description": "Fast, compatible"},
    {"value": "libx265", "label": "H.265", "description": "Better compression"},
    {"value": "libsvtav1", "label": "AV1", "description": "Best compression"},
]


class CompressPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._probe_info = {}
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Compress")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        layout.addWidget(QLabel("Quality preset:"))
        self._preset_grid = OptionGrid(columns=4)
        self._preset_grid.set_options(PRESETS)
        self._preset_grid.selection_changed.connect(self._on_preset)
        layout.addWidget(self._preset_grid)

        # Target size input (hidden by default)
        self._target_row = QHBoxLayout()
        self._target_row_widget = QWidget()
        tr = QHBoxLayout(self._target_row_widget)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.addWidget(QLabel("Target size (MB):"))
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("e.g. 25")
        self._target_input.setFixedWidth(120)
        tr.addWidget(self._target_input)
        tr.addStretch()
        self._target_row_widget.hide()
        layout.addWidget(self._target_row_widget)

        layout.addWidget(QLabel("Codec:"))
        self._codec_grid = OptionGrid(columns=3)
        self._codec_grid.set_options(CODECS)
        layout.addWidget(self._codec_grid)

        self._go_btn = QPushButton("Compress")
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

        self._preset_grid.select("23")
        self._codec_grid.select("libx264")

    def _on_file(self, path: str):
        self._input_path = path
        try:
            self._probe_info = probe(path)
            self._duration = get_duration_secs(self._probe_info)
            self._info.set_info(summarize(self._probe_info))
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._go_btn.setEnabled(True)

    def _on_preset(self, sel):
        self._target_row_widget.setVisible(sel == ["target"])

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        preset_sel = self._preset_grid.selected()
        codec_sel = self._codec_grid.selected()
        if not preset_sel or not codec_sel:
            return

        codec = codec_sel[0]
        preset = preset_sel[0]

        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_compressed.mp4")

        if preset == "target" and self._target_input.text().strip():
            # Two-pass for target size
            target_mb = float(self._target_input.text().strip())
            target_kbps = int((target_mb * 8192) / self._duration) if self._duration > 0 else 2000
            cmd = [
                "ffmpeg", "-y", "-i", self._input_path,
                "-c:v", codec, "-b:v", f"{target_kbps}k",
                "-c:a", "aac", "-b:a", "128k",
                "-progress", "pipe:1", out_path,
            ]
        else:
            crf = preset if preset != "target" else "23"
            cmd = [
                "ffmpeg", "-y", "-i", self._input_path,
                "-c:v", codec, "-crf", crf, "-preset", "medium",
                "-c:a", "aac", "-b:a", "128k",
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
