"""Batch processing page — apply the same operation to multiple files."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.progress import ProgressWidget

VIDEO_EXTENSIONS = (
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".wmv", ".m4v",
    ".mpg", ".mpeg", ".3gp", ".ts", ".mts", ".m2ts", ".vob", ".ogv",
)

OPERATIONS = [
    "Convert",
    "Compress",
    "Extract Audio",
    "Resize",
    "Strip Metadata",
    "Normalize Audio",
    "Generate Thumbnails",
]

CONVERT_FORMATS = ["mp4", "mkv", "webm"]
CONVERT_CODECS = ["libx264", "libx265", "libsvtav1"]

COMPRESS_CODECS = ["libx264", "libx265", "libsvtav1"]

AUDIO_FORMATS = ["mp3", "flac", "wav", "aac"]
AUDIO_CODEC_MAP = {
    "mp3": "libmp3lame",
    "flac": "flac",
    "wav": "pcm_s16le",
    "aac": "aac",
}

RESOLUTION_PRESETS = {
    "4K (3840)": "3840:-2",
    "1080p (1920)": "1920:-2",
    "720p (1280)": "1280:-2",
    "480p (854)": "854:-2",
    "Custom": "",
}

THUMB_FORMATS = ["png", "jpg"]


class BatchPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending: list[str] = []
        self._current_file = ""
        self._current_duration = 0.0
        self._total_files = 0
        self._processed_count = 0
        self._stop_requested = False
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Batch Process")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        # ── File list ────────────────────────────────────────────────
        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._file_list)

        file_btn_row = QHBoxLayout()
        self._add_files_btn = QPushButton("Add Files")
        self._add_files_btn.clicked.connect(self._add_files)
        file_btn_row.addWidget(self._add_files_btn)

        self._add_folder_btn = QPushButton("Add Folder")
        self._add_folder_btn.clicked.connect(self._add_folder)
        file_btn_row.addWidget(self._add_folder_btn)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._remove_selected)
        file_btn_row.addWidget(self._remove_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._clear_files)
        file_btn_row.addWidget(self._clear_btn)

        file_btn_row.addStretch()
        layout.addLayout(file_btn_row)

        self._file_count_label = QLabel("0 files loaded")
        layout.addWidget(self._file_count_label)

        # ── Operation selection ──────────────────────────────────────
        op_row = QHBoxLayout()
        op_row.addWidget(QLabel("Operation:"))
        self._op_combo = QComboBox()
        self._op_combo.addItems(OPERATIONS)
        self._op_combo.currentIndexChanged.connect(self._on_operation_changed)
        op_row.addWidget(self._op_combo, 1)
        layout.addLayout(op_row)

        # ── Per-operation option panels ──────────────────────────────
        # Convert options
        self._convert_widget = QWidget()
        cl = QVBoxLayout(self._convert_widget)
        cl.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout()
        r.addWidget(QLabel("Format:"))
        self._convert_fmt = QComboBox()
        self._convert_fmt.addItems(CONVERT_FORMATS)
        r.addWidget(self._convert_fmt)
        r.addWidget(QLabel("Codec:"))
        self._convert_codec = QComboBox()
        self._convert_codec.addItems(CONVERT_CODECS)
        r.addWidget(self._convert_codec)
        r.addStretch()
        cl.addLayout(r)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("CRF:"))
        self._convert_crf = QSlider(Qt.Orientation.Horizontal)
        self._convert_crf.setRange(0, 51)
        self._convert_crf.setValue(23)
        self._convert_crf_label = QLabel("23")
        self._convert_crf.valueChanged.connect(
            lambda v: self._convert_crf_label.setText(str(v))
        )
        r2.addWidget(self._convert_crf, 1)
        r2.addWidget(self._convert_crf_label)
        cl.addLayout(r2)
        layout.addWidget(self._convert_widget)

        # Compress options
        self._compress_widget = QWidget()
        cml = QVBoxLayout(self._compress_widget)
        cml.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout()
        r.addWidget(QLabel("CRF:"))
        self._compress_crf = QSlider(Qt.Orientation.Horizontal)
        self._compress_crf.setRange(0, 51)
        self._compress_crf.setValue(23)
        self._compress_crf_label = QLabel("23")
        self._compress_crf.valueChanged.connect(
            lambda v: self._compress_crf_label.setText(str(v))
        )
        r.addWidget(self._compress_crf, 1)
        r.addWidget(self._compress_crf_label)
        cml.addLayout(r)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Codec:"))
        self._compress_codec = QComboBox()
        self._compress_codec.addItems(COMPRESS_CODECS)
        r2.addWidget(self._compress_codec)
        r2.addStretch()
        cml.addLayout(r2)
        layout.addWidget(self._compress_widget)

        # Extract Audio options
        self._audio_widget = QWidget()
        al = QVBoxLayout(self._audio_widget)
        al.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout()
        r.addWidget(QLabel("Format:"))
        self._audio_fmt = QComboBox()
        self._audio_fmt.addItems(AUDIO_FORMATS)
        r.addWidget(self._audio_fmt)
        r.addStretch()
        al.addLayout(r)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Bitrate (kbps):"))
        self._audio_bitrate = QSlider(Qt.Orientation.Horizontal)
        self._audio_bitrate.setRange(64, 320)
        self._audio_bitrate.setValue(192)
        self._audio_bitrate.setSingleStep(32)
        self._audio_bitrate_label = QLabel("192")
        self._audio_bitrate.valueChanged.connect(
            lambda v: self._audio_bitrate_label.setText(str(v))
        )
        r2.addWidget(self._audio_bitrate, 1)
        r2.addWidget(self._audio_bitrate_label)
        al.addLayout(r2)
        layout.addWidget(self._audio_widget)

        # Resize options
        self._resize_widget = QWidget()
        rl = QVBoxLayout(self._resize_widget)
        rl.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout()
        r.addWidget(QLabel("Resolution:"))
        self._resize_combo = QComboBox()
        self._resize_combo.addItems(list(RESOLUTION_PRESETS.keys()))
        r.addWidget(self._resize_combo)
        r.addWidget(QLabel("Custom:"))
        self._resize_custom = QLineEdit()
        self._resize_custom.setPlaceholderText("e.g. 640:-2")
        self._resize_custom.setFixedWidth(120)
        r.addWidget(self._resize_custom)
        r.addStretch()
        rl.addLayout(r)
        layout.addWidget(self._resize_widget)

        # Strip Metadata — no extra options
        self._strip_widget = QWidget()
        sl = QVBoxLayout(self._strip_widget)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.addWidget(QLabel("No additional options required."))
        layout.addWidget(self._strip_widget)

        # Normalize Audio options
        self._normalize_widget = QWidget()
        nl = QVBoxLayout(self._normalize_widget)
        nl.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout()
        r.addWidget(QLabel("Target LUFS:"))
        self._lufs_spin = QDoubleSpinBox()
        self._lufs_spin.setRange(-70.0, -5.0)
        self._lufs_spin.setValue(-23.0)
        self._lufs_spin.setSingleStep(0.5)
        self._lufs_spin.setDecimals(1)
        r.addWidget(self._lufs_spin)
        r.addStretch()
        nl.addLayout(r)
        layout.addWidget(self._normalize_widget)

        # Thumbnail options
        self._thumb_widget = QWidget()
        tl = QVBoxLayout(self._thumb_widget)
        tl.setContentsMargins(0, 0, 0, 0)
        r = QHBoxLayout()
        r.addWidget(QLabel("Timestamp:"))
        self._thumb_ts = QLineEdit()
        self._thumb_ts.setPlaceholderText("00:00:05")
        self._thumb_ts.setFixedWidth(120)
        r.addWidget(self._thumb_ts)
        r.addWidget(QLabel("Format:"))
        self._thumb_fmt = QComboBox()
        self._thumb_fmt.addItems(THUMB_FORMATS)
        r.addWidget(self._thumb_fmt)
        r.addStretch()
        tl.addLayout(r)
        layout.addWidget(self._thumb_widget)

        self._option_panels = [
            self._convert_widget,
            self._compress_widget,
            self._audio_widget,
            self._resize_widget,
            self._strip_widget,
            self._normalize_widget,
            self._thumb_widget,
        ]

        # ── Output settings ──────────────────────────────────────────
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output:"))
        self._output_combo = QComboBox()
        self._output_combo.addItems(["Same folder", "Custom folder"])
        self._output_combo.currentIndexChanged.connect(self._on_output_changed)
        out_row.addWidget(self._output_combo)
        self._output_dir_btn = QPushButton("Browse...")
        self._output_dir_btn.clicked.connect(self._pick_output_dir)
        self._output_dir_btn.hide()
        out_row.addWidget(self._output_dir_btn)
        self._output_dir_label = QLabel("")
        self._output_dir_label.hide()
        out_row.addWidget(self._output_dir_label, 1)
        out_row.addStretch()
        layout.addLayout(out_row)

        self._custom_output_dir = ""

        suffix_row = QHBoxLayout()
        suffix_row.addWidget(QLabel("Suffix:"))
        self._suffix_input = QLineEdit("_processed")
        self._suffix_input.setFixedWidth(160)
        suffix_row.addWidget(self._suffix_input)
        suffix_row.addStretch()
        layout.addLayout(suffix_row)

        # ── Go / Stop ────────────────────────────────────────────────
        action_row = QHBoxLayout()
        self._go_btn = QPushButton("Go")
        self._go_btn.clicked.connect(self._start_batch)
        self._go_btn.setEnabled(False)
        action_row.addWidget(self._go_btn)

        self._stop_btn = QPushButton("Stop after current")
        self._stop_btn.clicked.connect(self._request_stop)
        self._stop_btn.setEnabled(False)
        action_row.addWidget(self._stop_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        # ── Progress ─────────────────────────────────────────────────
        self._overall_label = QLabel("")
        layout.addWidget(self._overall_label)

        self._progress = ProgressWidget()
        self._progress.cancel_button.clicked.connect(self._runner.cancel)
        layout.addWidget(self._progress)

        self._runner.progress.connect(self._progress.set_progress)
        self._runner.output.connect(self._progress.append_log)
        self._runner.finished.connect(self._on_file_done)

        layout.addStretch()

        # Show the first operation panel
        self._on_operation_changed(0)

    # ── File management ──────────────────────────────────────────────

    def _add_files(self):
        ext_filter = " ".join(f"*{e}" for e in VIDEO_EXTENSIONS)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select video files", "",
            f"Video files ({ext_filter});;All files (*)",
        )
        for p in paths:
            if p and not self._has_file(p):
                self._file_list.addItem(p)
        self._update_count()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if not folder:
            return
        for entry in sorted(Path(folder).rglob("*")):
            if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                path = str(entry)
                if not self._has_file(path):
                    self._file_list.addItem(path)
        self._update_count()

    def _remove_selected(self):
        for item in reversed(self._file_list.selectedItems()):
            self._file_list.takeItem(self._file_list.row(item))
        self._update_count()

    def _clear_files(self):
        self._file_list.clear()
        self._update_count()

    def _has_file(self, path: str) -> bool:
        for i in range(self._file_list.count()):
            if self._file_list.item(i).text() == path:
                return True
        return False

    def _update_count(self):
        n = self._file_list.count()
        self._file_count_label.setText(f"{n} files loaded")
        self._go_btn.setEnabled(n > 0 and not self._runner.is_running())

    # ── Operation switching ──────────────────────────────────────────

    def _on_operation_changed(self, index: int):
        for i, panel in enumerate(self._option_panels):
            panel.setVisible(i == index)

    # ── Output settings ──────────────────────────────────────────────

    def _on_output_changed(self, index: int):
        custom = index == 1
        self._output_dir_btn.setVisible(custom)
        self._output_dir_label.setVisible(custom)

    def _pick_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self._custom_output_dir = folder
            self._output_dir_label.setText(folder)

    def _get_output_dir(self, input_path: str) -> str:
        if self._output_combo.currentIndex() == 1 and self._custom_output_dir:
            return self._custom_output_dir
        return str(Path(input_path).parent)

    # ── Batch execution ──────────────────────────────────────────────

    def _start_batch(self):
        if self._runner.is_running():
            return
        n = self._file_list.count()
        if n == 0:
            return

        self._pending = [
            self._file_list.item(i).text() for i in range(n)
        ]
        self._total_files = len(self._pending)
        self._processed_count = 0
        self._stop_requested = False

        self._progress.reset()
        self._go_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._set_controls_enabled(False)

        self._process_next()

    def _request_stop(self):
        self._stop_requested = True
        self._stop_btn.setEnabled(False)
        self._progress.append_log("Will stop after the current file finishes.")

    def _process_next(self):
        if not self._pending or self._stop_requested:
            self._finish_batch()
            return

        self._current_file = self._pending.pop(0)
        self._processed_count += 1
        self._overall_label.setText(
            f"File {self._processed_count} of {self._total_files}: "
            f"{Path(self._current_file).name}"
        )

        # Probe duration for progress tracking
        self._current_duration = 0.0
        try:
            info = probe(self._current_file)
            self._current_duration = get_duration_secs(info)
        except Exception:
            pass

        cmd = self._build_command(self._current_file)
        if cmd is None:
            self._progress.append_log(f"Skipped (no command): {self._current_file}")
            self._process_next()
            return

        self._progress.set_progress(0)
        self._progress.set_running(True)
        self._progress.append_log(
            f"--- [{self._processed_count}/{self._total_files}] "
            f"{Path(self._current_file).name} ---"
        )
        self._runner.run(cmd, duration=self._current_duration)

    def _on_file_done(self, ok: bool, msg: str):
        self._progress.set_running(False)
        self._progress.append_log(msg)
        self._process_next()

    def _finish_batch(self):
        self._go_btn.setEnabled(self._file_list.count() > 0)
        self._stop_btn.setEnabled(False)
        self._set_controls_enabled(True)
        if self._stop_requested:
            self._overall_label.setText(
                f"Stopped. Processed {self._processed_count - 1} of {self._total_files} files."
            )
        else:
            self._overall_label.setText(
                f"Done. Processed {self._processed_count} of {self._total_files} files."
            )
        self._progress.append_log("=== Batch complete ===")

    def _set_controls_enabled(self, enabled: bool):
        self._add_files_btn.setEnabled(enabled)
        self._add_folder_btn.setEnabled(enabled)
        self._remove_btn.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)
        self._op_combo.setEnabled(enabled)
        self._output_combo.setEnabled(enabled)
        self._suffix_input.setEnabled(enabled)

    # ── Command building ─────────────────────────────────────────────

    def _build_command(self, input_path: str) -> list[str] | None:
        op = self._op_combo.currentText()
        stem = Path(input_path).stem
        ext = Path(input_path).suffix
        suffix = self._suffix_input.text()
        out_dir = self._get_output_dir(input_path)

        if op == "Convert":
            return self._cmd_convert(input_path, stem, out_dir, suffix)
        elif op == "Compress":
            return self._cmd_compress(input_path, stem, ext, out_dir, suffix)
        elif op == "Extract Audio":
            return self._cmd_extract_audio(input_path, stem, out_dir, suffix)
        elif op == "Resize":
            return self._cmd_resize(input_path, stem, ext, out_dir, suffix)
        elif op == "Strip Metadata":
            return self._cmd_strip_meta(input_path, stem, ext, out_dir, suffix)
        elif op == "Normalize Audio":
            return self._cmd_normalize(input_path, stem, ext, out_dir, suffix)
        elif op == "Generate Thumbnails":
            return self._cmd_thumbnail(input_path, stem, out_dir, suffix)
        return None

    def _cmd_convert(self, inp, stem, out_dir, suffix):
        fmt = self._convert_fmt.currentText()
        codec = self._convert_codec.currentText()
        crf = self._convert_crf.value()
        out = os.path.join(out_dir, f"{stem}{suffix}.{fmt}")
        cmd = ["ffmpeg", "-y", "-i", inp, "-c:v", codec, "-crf", str(crf)]
        cmd += ["-c:a", "aac", "-progress", "pipe:1", out]
        return cmd

    def _cmd_compress(self, inp, stem, ext, out_dir, suffix):
        codec = self._compress_codec.currentText()
        crf = self._compress_crf.value()
        out = os.path.join(out_dir, f"{stem}{suffix}{ext}")
        return [
            "ffmpeg", "-y", "-i", inp,
            "-c:v", codec, "-crf", str(crf), "-preset", "medium",
            "-c:a", "aac", "-b:a", "128k",
            "-progress", "pipe:1", out,
        ]

    def _cmd_extract_audio(self, inp, stem, out_dir, suffix):
        fmt = self._audio_fmt.currentText()
        codec = AUDIO_CODEC_MAP.get(fmt, fmt)
        bitrate = self._audio_bitrate.value()
        out = os.path.join(out_dir, f"{stem}{suffix}.{fmt}")
        cmd = ["ffmpeg", "-y", "-i", inp, "-vn", "-c:a", codec]
        if fmt not in ("flac", "wav"):
            cmd += ["-b:a", f"{bitrate}k"]
        cmd += ["-progress", "pipe:1", out]
        return cmd

    def _cmd_resize(self, inp, stem, ext, out_dir, suffix):
        custom = self._resize_custom.text().strip()
        if custom:
            scale = custom
        else:
            preset_key = self._resize_combo.currentText()
            scale = RESOLUTION_PRESETS.get(preset_key, "1920:-2")
            if not scale:
                scale = "1920:-2"
        out = os.path.join(out_dir, f"{stem}{suffix}{ext}")
        return [
            "ffmpeg", "-y", "-i", inp,
            "-vf", f"scale={scale}",
            "-c:a", "copy",
            "-progress", "pipe:1", out,
        ]

    def _cmd_strip_meta(self, inp, stem, ext, out_dir, suffix):
        out = os.path.join(out_dir, f"{stem}{suffix}{ext}")
        return [
            "ffmpeg", "-y", "-i", inp,
            "-map_metadata", "-1", "-c", "copy",
            "-progress", "pipe:1", out,
        ]

    def _cmd_normalize(self, inp, stem, ext, out_dir, suffix):
        lufs = self._lufs_spin.value()
        out = os.path.join(out_dir, f"{stem}{suffix}{ext}")
        return [
            "ffmpeg", "-y", "-i", inp,
            "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11",
            "-c:v", "copy",
            "-progress", "pipe:1", out,
        ]

    def _cmd_thumbnail(self, inp, stem, out_dir, suffix):
        ts = self._thumb_ts.text().strip() or "00:00:00"
        fmt = self._thumb_fmt.currentText()
        out = os.path.join(out_dir, f"{stem}{suffix}.{fmt}")
        return [
            "ffmpeg", "-y", "-ss", ts, "-i", inp,
            "-frames:v", "1",
            out,
        ]
