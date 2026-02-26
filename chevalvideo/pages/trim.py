"""Trim/cut video segments page."""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.progress import ProgressWidget


class TrimPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Trim")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # Time inputs
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Start:"))
        self._start_input = QLineEdit()
        self._start_input.setPlaceholderText("00:00:00")
        self._start_input.setFixedWidth(120)
        time_row.addWidget(self._start_input)
        time_row.addSpacing(16)
        time_row.addWidget(QLabel("End:"))
        self._end_input = QLineEdit()
        self._end_input.setPlaceholderText("00:01:30")
        self._end_input.setFixedWidth(120)
        time_row.addWidget(self._end_input)
        time_row.addStretch()
        layout.addLayout(time_row)

        self._copy_check = QCheckBox("Stream copy (no re-encode, fast but less precise)")
        self._copy_check.setChecked(True)
        layout.addWidget(self._copy_check)

        self._go_btn = QPushButton("Trim")
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

        start = self._start_input.text().strip() or "00:00:00"
        end = self._end_input.text().strip()
        copy = self._copy_check.isChecked()

        ext = Path(self._input_path).suffix
        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_trimmed{ext}")

        cmd = ["ffmpeg", "-y", "-ss", start, "-i", self._input_path]
        if end:
            cmd += ["-to", end]
        if copy:
            cmd += ["-c", "copy"]
        cmd += ["-progress", "pipe:1", out_path]

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
