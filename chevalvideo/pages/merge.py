"""Merge/concatenate multiple video files page."""

import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel,
    QPushButton, QSlider, QVBoxLayout, QWidget, QListWidget, QListWidgetItem,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

MODES = [
    {"value": "concat", "label": "Concat Demuxer", "description": "Fast, same codec"},
    {"value": "reencode", "label": "Re-encode", "description": "Slower, mixed codecs"},
]

FORMATS = [
    {"value": "mp4", "label": "MP4", "description": "Most compatible"},
    {"value": "mkv", "label": "MKV", "description": "Feature-rich container"},
    {"value": "webm", "label": "WebM", "description": "Web-optimized"},
]

CODECS = [
    {"value": "libx264", "label": "H.264", "description": "Fast, compatible"},
    {"value": "libx265", "label": "H.265", "description": "Better compression"},
    {"value": "libsvtav1", "label": "AV1", "description": "Best compression"},
]

TRANSITIONS = [
    {"value": "none", "label": "None", "description": "Simple join"},
    {"value": "crossfade", "label": "Crossfade", "description": "Fade between clips"},
]


class MergePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_paths: list[str] = []
        self._total_duration = 0.0
        self._runner = CommandRunner(self)
        self._temp_list_file = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Merge")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        # --- File list ---
        self._file_list = QListWidget()
        self._file_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._file_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._file_list.setMinimumHeight(140)
        self._file_list.model().rowsMoved.connect(self._on_reorder)
        layout.addWidget(self._file_list)

        # File buttons row
        file_btn_row = QHBoxLayout()
        self._add_btn = QPushButton("Add Files")
        self._add_btn.clicked.connect(self._add_files)
        file_btn_row.addWidget(self._add_btn)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._remove_selected)
        file_btn_row.addWidget(self._remove_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._clear_files)
        file_btn_row.addWidget(self._clear_btn)

        file_btn_row.addSpacing(16)

        self._up_btn = QPushButton("Move Up")
        self._up_btn.clicked.connect(self._move_up)
        file_btn_row.addWidget(self._up_btn)

        self._down_btn = QPushButton("Move Down")
        self._down_btn.clicked.connect(self._move_down)
        file_btn_row.addWidget(self._down_btn)

        file_btn_row.addStretch()
        layout.addLayout(file_btn_row)

        # --- Mode ---
        layout.addWidget(QLabel("Mode:"))
        self._mode_grid = OptionGrid(columns=2)
        self._mode_grid.set_options(MODES)
        self._mode_grid.selection_changed.connect(self._on_mode_changed)
        layout.addWidget(self._mode_grid)

        # --- Re-encode options (hidden when concat mode) ---
        self._reencode_widget = QWidget()
        re_layout = QVBoxLayout(self._reencode_widget)
        re_layout.setContentsMargins(0, 0, 0, 0)
        re_layout.setSpacing(8)

        re_layout.addWidget(QLabel("Video codec:"))
        self._codec_grid = OptionGrid(columns=3)
        self._codec_grid.set_options(CODECS)
        re_layout.addWidget(self._codec_grid)

        crf_row = QHBoxLayout()
        crf_row.addWidget(QLabel("Quality (CRF):"))
        self._crf_slider = QSlider(Qt.Orientation.Horizontal)
        self._crf_slider.setRange(0, 51)
        self._crf_slider.setValue(23)
        self._crf_label = QLabel("23")
        self._crf_slider.valueChanged.connect(lambda v: self._crf_label.setText(str(v)))
        crf_row.addWidget(self._crf_slider, 1)
        crf_row.addWidget(self._crf_label)
        re_layout.addLayout(crf_row)

        self._reencode_widget.hide()
        layout.addWidget(self._reencode_widget)

        # --- Output format ---
        layout.addWidget(QLabel("Output format:"))
        self._fmt_grid = OptionGrid(columns=3)
        self._fmt_grid.set_options(FORMATS)
        layout.addWidget(self._fmt_grid)

        # --- Transition ---
        layout.addWidget(QLabel("Transition:"))
        self._transition_grid = OptionGrid(columns=2)
        self._transition_grid.set_options(TRANSITIONS)
        self._transition_grid.selection_changed.connect(self._on_transition_changed)
        layout.addWidget(self._transition_grid)

        # Crossfade duration (hidden by default)
        self._crossfade_widget = QWidget()
        cf_layout = QHBoxLayout(self._crossfade_widget)
        cf_layout.setContentsMargins(0, 0, 0, 0)
        cf_layout.addWidget(QLabel("Crossfade duration (s):"))
        self._crossfade_spin = QDoubleSpinBox()
        self._crossfade_spin.setRange(0.1, 10.0)
        self._crossfade_spin.setValue(1.0)
        self._crossfade_spin.setSingleStep(0.1)
        self._crossfade_spin.setDecimals(1)
        self._crossfade_spin.setFixedWidth(100)
        cf_layout.addWidget(self._crossfade_spin)
        cf_layout.addStretch()
        self._crossfade_widget.hide()
        layout.addWidget(self._crossfade_widget)

        # --- Go button ---
        self._go_btn = QPushButton("Merge")
        self._go_btn.clicked.connect(self._run)
        self._go_btn.setEnabled(False)
        layout.addWidget(self._go_btn)

        # --- Progress ---
        self._progress = ProgressWidget()
        self._progress.cancel_button.clicked.connect(self._runner.cancel)
        layout.addWidget(self._progress)

        self._runner.progress.connect(self._progress.set_progress)
        self._runner.output.connect(self._progress.append_log)
        self._runner.finished.connect(self._on_done)

        layout.addStretch()

        # Defaults
        self._mode_grid.select("concat")
        self._fmt_grid.select("mp4")
        self._codec_grid.select("libx264")
        self._transition_grid.select("none")

    # ---- File management ----

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select video files", "",
            "Video files (*.mp4 *.mkv *.webm *.avi *.mov *.flv *.ts *.m4v);;All files (*)",
        )
        for p in paths:
            if p not in self._file_paths:
                self._file_paths.append(p)
                item = QListWidgetItem(Path(p).name)
                item.setData(Qt.ItemDataRole.UserRole, p)
                self._file_list.addItem(item)
        self._update_state()

    def _remove_selected(self):
        row = self._file_list.currentRow()
        if row < 0:
            return
        item = self._file_list.takeItem(row)
        path = item.data(Qt.ItemDataRole.UserRole)
        if path in self._file_paths:
            self._file_paths.remove(path)
        self._update_state()

    def _clear_files(self):
        self._file_list.clear()
        self._file_paths.clear()
        self._update_state()

    def _move_up(self):
        row = self._file_list.currentRow()
        if row <= 0:
            return
        item = self._file_list.takeItem(row)
        self._file_list.insertItem(row - 1, item)
        self._file_list.setCurrentRow(row - 1)
        self._sync_paths_from_list()

    def _move_down(self):
        row = self._file_list.currentRow()
        if row < 0 or row >= self._file_list.count() - 1:
            return
        item = self._file_list.takeItem(row)
        self._file_list.insertItem(row + 1, item)
        self._file_list.setCurrentRow(row + 1)
        self._sync_paths_from_list()

    def _on_reorder(self):
        self._sync_paths_from_list()

    def _sync_paths_from_list(self):
        self._file_paths = []
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            self._file_paths.append(item.data(Qt.ItemDataRole.UserRole))

    def _update_state(self):
        has_files = len(self._file_paths) >= 2
        self._go_btn.setEnabled(has_files)

    # ---- Mode / transition toggles ----

    def _on_mode_changed(self, sel: list[str]):
        is_reencode = sel == ["reencode"]
        self._reencode_widget.setVisible(is_reencode)
        # Crossfade requires re-encode
        if not is_reencode:
            self._transition_grid.select("none")
            self._crossfade_widget.hide()

    def _on_transition_changed(self, sel: list[str]):
        is_crossfade = sel == ["crossfade"]
        self._crossfade_widget.setVisible(is_crossfade)
        # Crossfade forces re-encode mode
        if is_crossfade:
            self._mode_grid.select("reencode")
            self._reencode_widget.show()

    # ---- Probe total duration ----

    def _probe_total_duration(self) -> float:
        total = 0.0
        for p in self._file_paths:
            try:
                info = probe(p)
                total += get_duration_secs(info)
            except Exception:
                pass
        return total

    # ---- Run ----

    def _run(self):
        if len(self._file_paths) < 2 or self._runner.is_running():
            return

        mode_sel = self._mode_grid.selected()
        fmt_sel = self._fmt_grid.selected()
        transition_sel = self._transition_grid.selected()
        if not mode_sel or not fmt_sel:
            return

        mode = mode_sel[0]
        fmt = fmt_sel[0]
        transition = transition_sel[0] if transition_sel else "none"

        # Build output path based on first file
        first = Path(self._file_paths[0])
        out_dir = str(first.parent)
        out_path = os.path.join(out_dir, f"{first.stem}_merged.{fmt}")

        # Estimate total duration for progress
        self._total_duration = self._probe_total_duration()

        if transition == "crossfade":
            cmd = self._build_xfade_cmd(fmt, out_path)
        elif mode == "concat":
            cmd = self._build_concat_demuxer_cmd(out_path)
        else:
            cmd = self._build_reencode_cmd(fmt, out_path)

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._total_duration)

    def _build_concat_demuxer_cmd(self, out_path: str) -> list[str]:
        # Write temp file list
        self._temp_list_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False,
        )
        for p in self._file_paths:
            safe = p.replace("'", "'\\''")
            self._temp_list_file.write(f"file '{safe}'\n")
        self._temp_list_file.flush()
        self._temp_list_file.close()

        return [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", self._temp_list_file.name,
            "-c", "copy",
            "-progress", "pipe:1",
            out_path,
        ]

    def _build_reencode_cmd(self, fmt: str, out_path: str) -> list[str]:
        codec_sel = self._codec_grid.selected()
        codec = codec_sel[0] if codec_sel else "libx264"
        crf = self._crf_slider.value()

        n = len(self._file_paths)
        cmd = ["ffmpeg", "-y"]
        for p in self._file_paths:
            cmd += ["-i", p]

        # Build concat filter
        filter_parts = []
        for i in range(n):
            filter_parts.append(f"[{i}:v:0][{i}:a:0]")
        filter_str = "".join(filter_parts) + f"concat=n={n}:v=1:a=1[outv][outa]"

        cmd += [
            "-filter_complex", filter_str,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", codec, "-crf", str(crf),
            "-c:a", "aac", "-b:a", "128k",
            "-progress", "pipe:1",
            out_path,
        ]
        return cmd

    def _build_xfade_cmd(self, fmt: str, out_path: str) -> list[str]:
        codec_sel = self._codec_grid.selected()
        codec = codec_sel[0] if codec_sel else "libx264"
        crf = self._crf_slider.value()
        fade_dur = self._crossfade_spin.value()

        n = len(self._file_paths)
        cmd = ["ffmpeg", "-y"]
        for p in self._file_paths:
            cmd += ["-i", p]

        # Probe individual durations for offset calculation
        durations = []
        for p in self._file_paths:
            try:
                info = probe(p)
                durations.append(get_duration_secs(info))
            except Exception:
                durations.append(0.0)

        if n == 2:
            # Simple two-input xfade
            offset = max(0, durations[0] - fade_dur)
            vfilter = f"[0:v][1:v]xfade=transition=fade:duration={fade_dur}:offset={offset}[outv]"
            afilter = f"[0:a][1:a]acrossfade=d={fade_dur}[outa]"
            filter_str = f"{vfilter};{afilter}"
        else:
            # Chain xfade for multiple inputs
            vparts = []
            aparts = []
            cumulative_offset = 0.0

            # First xfade: [0:v][1:v] -> [xv0]
            cumulative_offset = durations[0] - fade_dur
            vparts.append(
                f"[0:v][1:v]xfade=transition=fade:duration={fade_dur}:offset={max(0, cumulative_offset)}[xv0]"
            )
            aparts.append(f"[0:a][1:a]acrossfade=d={fade_dur}[xa0]")

            # Subsequent xfades chain from previous output
            for i in range(2, n):
                prev_v = f"[xv{i - 2}]"
                prev_a = f"[xa{i - 2}]"
                out_v = f"[xv{i - 1}]" if i < n - 1 else "[outv]"
                out_a = f"[xa{i - 1}]" if i < n - 1 else "[outa]"

                # The accumulated duration of the merged stream so far
                cumulative_offset += durations[i - 1] - fade_dur
                vparts.append(
                    f"{prev_v}[{i}:v]xfade=transition=fade:duration={fade_dur}:offset={max(0, cumulative_offset)}{out_v}"
                )
                aparts.append(f"{prev_a}[{i}:a]acrossfade=d={fade_dur}{out_a}")

            if n == 2:
                pass  # already handled above
            else:
                # Rename last outputs to [outv]/[outa] if not already
                if n > 2:
                    # Last outputs are already named [outv]/[outa] in the loop
                    pass

            filter_str = ";".join(vparts + aparts)

        cmd += [
            "-filter_complex", filter_str,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", codec, "-crf", str(crf),
            "-c:a", "aac", "-b:a", "128k",
            "-progress", "pipe:1",
            out_path,
        ]
        return cmd

    def _on_done(self, ok: bool, msg: str):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
        # Clean up temp file
        if self._temp_list_file is not None:
            try:
                os.unlink(self._temp_list_file.name)
            except OSError:
                pass
            self._temp_list_file = None
