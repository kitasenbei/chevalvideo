"""Extract audio track page."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

FORMATS = [
    {"value": "mp3", "label": "MP3", "description": "Universal"},
    {"value": "flac", "label": "FLAC", "description": "Lossless"},
    {"value": "wav", "label": "WAV", "description": "Uncompressed"},
    {"value": "aac", "label": "AAC", "description": "Apple/web"},
]

CODEC_MAP = {
    "mp3": "libmp3lame",
    "flac": "flac",
    "wav": "pcm_s16le",
    "aac": "aac",
    "opus": "libopus",
}


class ExtractAudioPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Extract Audio")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        layout.addWidget(QLabel("Audio format:"))
        self._fmt_grid = OptionGrid(columns=4)
        self._fmt_grid.set_options(FORMATS)
        layout.addWidget(self._fmt_grid)

        # Quality (bitrate for lossy)
        row = QHBoxLayout()
        row.addWidget(QLabel("Quality (kbps):"))
        self._quality_slider = QSlider(Qt.Orientation.Horizontal)
        self._quality_slider.setRange(64, 320)
        self._quality_slider.setValue(192)
        self._quality_slider.setSingleStep(32)
        self._quality_label = QLabel("192")
        self._quality_slider.valueChanged.connect(lambda v: self._quality_label.setText(str(v)))
        row.addWidget(self._quality_slider, 1)
        row.addWidget(self._quality_label)
        layout.addLayout(row)

        self._go_btn = QPushButton("Extract")
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
        self._fmt_grid.select("mp3")

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
        fmt_sel = self._fmt_grid.selected()
        if not fmt_sel:
            return

        fmt = fmt_sel[0]
        codec = CODEC_MAP.get(fmt, fmt)
        bitrate = self._quality_slider.value()
        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}.{fmt}")

        cmd = ["ffmpeg", "-y", "-i", self._input_path, "-vn", "-c:a", codec]
        if fmt not in ("flac", "wav"):
            cmd += ["-b:a", f"{bitrate}k"]
        cmd += ["-progress", "pipe:1", out_path]

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
