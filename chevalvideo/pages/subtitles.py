"""Subtitle operations page — burn in, embed, or extract subtitles."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

MODES = [
    {"value": "burn", "label": "Burn In", "description": "Hardcode subtitles into video"},
    {"value": "embed", "label": "Embed", "description": "Add as soft subtitle track"},
    {"value": "extract", "label": "Extract", "description": "Rip subtitle track from video"},
]

POSITIONS = [
    {"value": "bottom", "label": "Bottom", "description": "Default position"},
    {"value": "top", "label": "Top", "description": "Upper area"},
]

EXTRACT_FORMATS = [
    {"value": "srt", "label": "SRT", "description": "SubRip Text"},
    {"value": "ass", "label": "ASS", "description": "Advanced SubStation"},
    {"value": "vtt", "label": "VTT", "description": "WebVTT"},
]

SUB_FILE_FILTERS = "Subtitle files (*.srt *.ass *.vtt *.ssa *.sub);;All files (*)"


class SubtitlesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._sub_path = ""
        self._probe_info = {}
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Subtitles")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        # -- Video input --
        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # -- Mode selection --
        layout.addWidget(QLabel("Mode:"))
        self._mode_grid = OptionGrid(columns=3)
        self._mode_grid.set_options(MODES)
        self._mode_grid.selection_changed.connect(self._on_mode)
        layout.addWidget(self._mode_grid)

        # =====================================================================
        # BURN IN options
        # =====================================================================
        self._burn_group = QWidget()
        burn_lay = QVBoxLayout(self._burn_group)
        burn_lay.setContentsMargins(0, 0, 0, 0)
        burn_lay.setSpacing(8)

        # Subtitle file picker
        sub_row = QHBoxLayout()
        sub_row.addWidget(QLabel("Subtitle file:"))
        self._burn_sub_label = QLabel("(none)")
        self._burn_sub_label.setMinimumWidth(200)
        sub_row.addWidget(self._burn_sub_label, 1)
        burn_browse = QPushButton("Browse")
        burn_browse.setFixedWidth(100)
        burn_browse.clicked.connect(self._browse_sub_burn)
        sub_row.addWidget(burn_browse)
        burn_lay.addLayout(sub_row)

        # Font size
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Font size:"))
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 120)
        self._font_size.setValue(24)
        size_row.addWidget(self._font_size)
        size_row.addStretch()
        burn_lay.addLayout(size_row)

        # Font color
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Font color (hex):"))
        self._font_color = QLineEdit("#ffffff")
        self._font_color.setFixedWidth(100)
        color_row.addWidget(self._font_color)
        color_row.addStretch()
        burn_lay.addLayout(color_row)

        # Outline / shadow
        self._outline_check = QCheckBox("Outline / shadow")
        self._outline_check.setChecked(True)
        burn_lay.addWidget(self._outline_check)

        # Vertical position
        burn_lay.addWidget(QLabel("Vertical position:"))
        self._pos_grid = OptionGrid(columns=3)
        self._pos_grid.set_options(POSITIONS)
        burn_lay.addWidget(self._pos_grid)

        layout.addWidget(self._burn_group)

        # =====================================================================
        # EMBED options
        # =====================================================================
        self._embed_group = QWidget()
        embed_lay = QVBoxLayout(self._embed_group)
        embed_lay.setContentsMargins(0, 0, 0, 0)
        embed_lay.setSpacing(8)

        # Subtitle file picker
        esub_row = QHBoxLayout()
        esub_row.addWidget(QLabel("Subtitle file:"))
        self._embed_sub_label = QLabel("(none)")
        self._embed_sub_label.setMinimumWidth(200)
        esub_row.addWidget(self._embed_sub_label, 1)
        embed_browse = QPushButton("Browse")
        embed_browse.setFixedWidth(100)
        embed_browse.clicked.connect(self._browse_sub_embed)
        esub_row.addWidget(embed_browse)
        embed_lay.addLayout(esub_row)

        # Language code
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Language code:"))
        self._lang_input = QLineEdit("eng")
        self._lang_input.setFixedWidth(80)
        lang_row.addWidget(self._lang_input)
        lang_row.addStretch()
        embed_lay.addLayout(lang_row)

        # Default track
        self._default_track_check = QCheckBox("Default track")
        embed_lay.addWidget(self._default_track_check)

        layout.addWidget(self._embed_group)

        # =====================================================================
        # EXTRACT options
        # =====================================================================
        self._extract_group = QWidget()
        extract_lay = QVBoxLayout(self._extract_group)
        extract_lay.setContentsMargins(0, 0, 0, 0)
        extract_lay.setSpacing(8)

        # Track index
        idx_row = QHBoxLayout()
        idx_row.addWidget(QLabel("Track index:"))
        self._track_index = QSpinBox()
        self._track_index.setRange(0, 99)
        self._track_index.setValue(0)
        idx_row.addWidget(self._track_index)
        idx_row.addStretch()
        extract_lay.addLayout(idx_row)

        # Output format
        extract_lay.addWidget(QLabel("Output format:"))
        self._extract_fmt_grid = OptionGrid(columns=3)
        self._extract_fmt_grid.set_options(EXTRACT_FORMATS)
        extract_lay.addWidget(self._extract_fmt_grid)

        layout.addWidget(self._extract_group)

        # =====================================================================
        # Go button + progress
        # =====================================================================
        self._go_btn = QPushButton("Run")
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

        # Defaults
        self._mode_grid.select("burn")
        self._pos_grid.select("bottom")
        self._extract_fmt_grid.select("srt")
        self._on_mode(["burn"])

    # --------------------------------------------------------------------- #
    # File handling
    # --------------------------------------------------------------------- #

    def _on_file(self, path: str):
        self._input_path = path
        try:
            self._probe_info = probe(path)
            self._duration = get_duration_secs(self._probe_info)
            self._info.set_info(summarize(self._probe_info))
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._go_btn.setEnabled(True)

    def _browse_sub_burn(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select subtitle file", "", SUB_FILE_FILTERS)
        if path:
            self._sub_path = path
            self._burn_sub_label.setText(Path(path).name)

    def _browse_sub_embed(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select subtitle file", "", SUB_FILE_FILTERS)
        if path:
            self._sub_path = path
            self._embed_sub_label.setText(Path(path).name)

    # --------------------------------------------------------------------- #
    # Mode switching
    # --------------------------------------------------------------------- #

    def _on_mode(self, sel: list[str]):
        mode = sel[0] if sel else "burn"
        self._burn_group.setVisible(mode == "burn")
        self._embed_group.setVisible(mode == "embed")
        self._extract_group.setVisible(mode == "extract")

    # --------------------------------------------------------------------- #
    # Build and run commands
    # --------------------------------------------------------------------- #

    def _current_mode(self) -> str:
        sel = self._mode_grid.selected()
        return sel[0] if sel else "burn"

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        mode = self._current_mode()
        if mode == "burn":
            cmd = self._build_burn_cmd()
        elif mode == "embed":
            cmd = self._build_embed_cmd()
        elif mode == "extract":
            cmd = self._build_extract_cmd()
        else:
            return

        if cmd is None:
            return

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _build_burn_cmd(self) -> list[str] | None:
        if not self._sub_path:
            self._progress.append_log("Error: no subtitle file selected.")
            return None

        font_size = self._font_size.value()
        font_color = self._font_color.text().strip().lstrip("#")

        # Convert hex color to ASS &HBBGGRR& format
        if len(font_color) == 6:
            r, g, b = font_color[0:2], font_color[2:4], font_color[4:6]
            ass_color = f"&H00{b}{g}{r}&"
        else:
            ass_color = "&H00FFFFFF&"

        # Build force_style
        style_parts = [f"FontSize={font_size}", f"PrimaryColour={ass_color}"]

        if self._outline_check.isChecked():
            style_parts.append("OutlineColour=&H00000000&")
            style_parts.append("Outline=2")
            style_parts.append("Shadow=1")
        else:
            style_parts.append("Outline=0")
            style_parts.append("Shadow=0")

        # Vertical position
        pos_sel = self._pos_grid.selected()
        position = pos_sel[0] if pos_sel else "bottom"
        if position == "top":
            style_parts.append("Alignment=8")  # ASS top-center
            style_parts.append("MarginV=20")
        else:
            style_parts.append("Alignment=2")  # ASS bottom-center
            style_parts.append("MarginV=20")

        force_style = ",".join(style_parts)

        # Escape the subtitle path for the filtergraph: colons and backslashes
        escaped_sub = self._sub_path.replace("\\", "/").replace(":", "\\:")
        vf = f"subtitles={escaped_sub}:force_style='{force_style}'"

        stem = Path(self._input_path).stem
        ext = Path(self._input_path).suffix
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_burned{ext}")

        return [
            "ffmpeg", "-y", "-i", self._input_path,
            "-vf", vf,
            "-c:a", "copy",
            "-progress", "pipe:1",
            out_path,
        ]

    def _build_embed_cmd(self) -> list[str] | None:
        if not self._sub_path:
            self._progress.append_log("Error: no subtitle file selected.")
            return None

        stem = Path(self._input_path).stem
        ext = Path(self._input_path).suffix.lower()
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_subs{ext}")

        lang = self._lang_input.text().strip() or "und"

        # Choose subtitle codec based on container
        if ext in (".mp4", ".m4v", ".mov"):
            sub_codec = "mov_text"
        else:
            sub_codec = "srt"

        cmd = [
            "ffmpeg", "-y",
            "-i", self._input_path,
            "-i", self._sub_path,
            "-c", "copy",
            "-c:s", sub_codec,
            "-metadata:s:s:0", f"language={lang}",
        ]

        if self._default_track_check.isChecked():
            cmd += ["-disposition:s:0", "default"]
        else:
            cmd += ["-disposition:s:0", "0"]

        cmd += ["-progress", "pipe:1", out_path]
        return cmd

    def _build_extract_cmd(self) -> list[str] | None:
        fmt_sel = self._extract_fmt_grid.selected()
        if not fmt_sel:
            self._progress.append_log("Error: no output format selected.")
            return None

        fmt = fmt_sel[0]
        idx = self._track_index.value()

        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_sub{idx}.{fmt}")

        return [
            "ffmpeg", "-y",
            "-i", self._input_path,
            "-map", f"0:s:{idx}",
            "-progress", "pipe:1",
            out_path,
        ]

    # --------------------------------------------------------------------- #
    # Finished
    # --------------------------------------------------------------------- #

    def _on_done(self, ok: bool, msg: str):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
