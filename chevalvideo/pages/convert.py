"""Format/codec conversion page."""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

FORMATS = [
    {"value": "mp4", "label": "MP4", "description": "Most compatible"},
    {"value": "mkv", "label": "MKV", "description": "Feature-rich container"},
    {"value": "webm", "label": "WebM", "description": "Web-optimized"},
    {"value": "avi", "label": "AVI", "description": "Legacy format"},
]

VIDEO_CODECS = {
    "mp4": [
        {"value": "libx264", "label": "H.264", "description": "Fast, compatible"},
        {"value": "libx265", "label": "H.265", "description": "Better compression"},
        {"value": "copy", "label": "Copy", "description": "No re-encode"},
    ],
    "mkv": [
        {"value": "libx264", "label": "H.264", "description": "Fast, compatible"},
        {"value": "libx265", "label": "H.265", "description": "Better compression"},
        {"value": "libsvtav1", "label": "AV1", "description": "Best compression"},
        {"value": "copy", "label": "Copy", "description": "No re-encode"},
    ],
    "webm": [
        {"value": "libvpx-vp9", "label": "VP9", "description": "Good compression"},
        {"value": "libsvtav1", "label": "AV1", "description": "Best compression"},
    ],
    "avi": [
        {"value": "libx264", "label": "H.264", "description": "Fast, compatible"},
        {"value": "copy", "label": "Copy", "description": "No re-encode"},
    ],
}

AUDIO_CODECS = {
    "mp4": [
        {"value": "aac", "label": "AAC"},
        {"value": "copy", "label": "Copy"},
    ],
    "mkv": [
        {"value": "aac", "label": "AAC"},
        {"value": "libopus", "label": "Opus"},
        {"value": "flac", "label": "FLAC"},
        {"value": "copy", "label": "Copy"},
    ],
    "webm": [
        {"value": "libopus", "label": "Opus"},
        {"value": "libvorbis", "label": "Vorbis"},
    ],
    "avi": [
        {"value": "mp3", "label": "MP3"},
        {"value": "copy", "label": "Copy"},
    ],
}


class ConvertPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._probe_info = {}
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Convert")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # Format
        layout.addWidget(QLabel("Output format:"))
        self._fmt_grid = OptionGrid(columns=4)
        self._fmt_grid.set_options(FORMATS)
        self._fmt_grid.selection_changed.connect(self._on_format)
        layout.addWidget(self._fmt_grid)

        # Video codec
        layout.addWidget(QLabel("Video codec:"))
        self._vcodec_grid = OptionGrid(columns=4)
        layout.addWidget(self._vcodec_grid)

        # Audio codec
        layout.addWidget(QLabel("Audio codec:"))
        self._acodec_grid = OptionGrid(columns=4)
        layout.addWidget(self._acodec_grid)

        # CRF
        crf_row = QHBoxLayout()
        crf_row.addWidget(QLabel("Quality (CRF):"))
        self._crf_slider = QSlider(Qt.Orientation.Horizontal)
        self._crf_slider.setRange(0, 51)
        self._crf_slider.setValue(23)
        self._crf_label = QLabel("23")
        self._crf_slider.valueChanged.connect(lambda v: self._crf_label.setText(str(v)))
        crf_row.addWidget(self._crf_slider, 1)
        crf_row.addWidget(self._crf_label)
        layout.addLayout(crf_row)

        # Go
        from PyQt6.QtWidgets import QPushButton
        self._go_btn = QPushButton("Convert")
        self._go_btn.clicked.connect(self._run)
        self._go_btn.setEnabled(False)
        layout.addWidget(self._go_btn)

        # Progress
        self._progress = ProgressWidget()
        self._progress.cancel_button.clicked.connect(self._runner.cancel)
        layout.addWidget(self._progress)

        self._runner.progress.connect(self._progress.set_progress)
        self._runner.output.connect(self._progress.append_log)
        self._runner.finished.connect(self._on_done)

        layout.addStretch()

        # Default format selection
        self._fmt_grid.select("mp4")
        self._on_format(["mp4"])

    def _on_file(self, path: str):
        self._input_path = path
        try:
            self._probe_info = probe(path)
            self._duration = get_duration_secs(self._probe_info)
            self._info.set_info(summarize(self._probe_info))
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._go_btn.setEnabled(True)

    def _on_format(self, sel: list[str]):
        if not sel:
            return
        fmt = sel[0]
        self._vcodec_grid.set_options(VIDEO_CODECS.get(fmt, []))
        self._acodec_grid.set_options(AUDIO_CODECS.get(fmt, []))
        vcodecs = VIDEO_CODECS.get(fmt, [])
        if vcodecs:
            self._vcodec_grid.select(vcodecs[0]["value"])
        acodecs = AUDIO_CODECS.get(fmt, [])
        if acodecs:
            self._acodec_grid.select(acodecs[0]["value"])

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        fmt_sel = self._fmt_grid.selected()
        vcodec_sel = self._vcodec_grid.selected()
        acodec_sel = self._acodec_grid.selected()
        if not fmt_sel:
            return

        fmt = fmt_sel[0]
        vcodec = vcodec_sel[0] if vcodec_sel else "copy"
        acodec = acodec_sel[0] if acodec_sel else "copy"
        crf = self._crf_slider.value()

        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_converted.{fmt}")

        cmd = ["ffmpeg", "-y", "-i", self._input_path]
        if vcodec == "copy":
            cmd += ["-c:v", "copy"]
        else:
            cmd += ["-c:v", vcodec, "-crf", str(crf)]
        cmd += ["-c:a", acodec]
        cmd += ["-progress", "pipe:1", out_path]

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _on_done(self, ok: bool, msg: str):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
