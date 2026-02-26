"""Watermark overlay page — image or text watermark on video."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

POSITIONS = [
    {"value": "top-left", "label": "Top Left", "description": ""},
    {"value": "top-right", "label": "Top Right", "description": ""},
    {"value": "center", "label": "Center", "description": ""},
    {"value": "bottom-left", "label": "Bottom Left", "description": ""},
    {"value": "bottom-right", "label": "Bottom Right", "description": ""},
]


class WatermarkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._watermark_path = ""
        self._probe_info = {}
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Watermark")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        # --- Video input ---
        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # --- Mode toggle ---
        layout.addWidget(QLabel("Mode:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Image watermark", "Text watermark"])
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self._mode_combo)

        # --- Image mode controls ---
        self._image_group = QWidget()
        ig = QVBoxLayout(self._image_group)
        ig.setContentsMargins(0, 0, 0, 0)
        ig.setSpacing(8)

        self._wm_file_drop = FileDropWidget(
            label="Drop watermark image or click Browse",
            filters="Image files (*.png *.jpg *.jpeg *.svg *.bmp);;All files (*)",
        )
        self._wm_file_drop.file_selected.connect(self._on_watermark_file)
        ig.addWidget(self._wm_file_drop)

        # Scale slider
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Scale (% of video width):"))
        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(10, 100)
        self._scale_slider.setValue(25)
        self._scale_slider.setTickInterval(10)
        self._scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._scale_label = QLabel("25%")
        self._scale_slider.valueChanged.connect(
            lambda v: self._scale_label.setText(f"{v}%")
        )
        scale_row.addWidget(self._scale_slider, 1)
        scale_row.addWidget(self._scale_label)
        ig.addLayout(scale_row)

        # Opacity slider
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity:"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(0, 100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.setTickInterval(10)
        self._opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._opacity_label = QLabel("1.0")
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v / 100:.2f}")
        )
        opacity_row.addWidget(self._opacity_slider, 1)
        opacity_row.addWidget(self._opacity_label)
        ig.addLayout(opacity_row)

        layout.addWidget(self._image_group)

        # --- Text mode controls ---
        self._text_group = QWidget()
        tg = QVBoxLayout(self._text_group)
        tg.setContentsMargins(0, 0, 0, 0)
        tg.setSpacing(8)

        text_row = QHBoxLayout()
        text_row.addWidget(QLabel("Text:"))
        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText("e.g. Sample Watermark")
        text_row.addWidget(self._text_input, 1)
        tg.addLayout(text_row)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font size:"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 200)
        self._font_size_spin.setValue(48)
        self._font_size_spin.setFixedWidth(80)
        font_row.addWidget(self._font_size_spin)
        font_row.addStretch()
        tg.addLayout(font_row)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Font color:"))
        self._font_color_input = QLineEdit("#ffffff")
        self._font_color_input.setFixedWidth(100)
        self._font_color_input.setPlaceholderText("#ffffff")
        color_row.addWidget(self._font_color_input)
        color_row.addStretch()
        tg.addLayout(color_row)

        # Background box
        bg_row = QHBoxLayout()
        self._bg_check = QCheckBox("Background box")
        bg_row.addWidget(self._bg_check)
        self._bg_color_input = QLineEdit("#000000@0.5")
        self._bg_color_input.setFixedWidth(120)
        self._bg_color_input.setPlaceholderText("#000000@0.5")
        self._bg_color_input.setEnabled(False)
        self._bg_check.toggled.connect(self._bg_color_input.setEnabled)
        bg_row.addWidget(self._bg_color_input)
        bg_row.addStretch()
        tg.addLayout(bg_row)

        self._text_group.hide()
        layout.addWidget(self._text_group)

        # --- Shared controls ---
        layout.addWidget(QLabel("Position:"))
        self._position_grid = OptionGrid(columns=5)
        self._position_grid.set_options(POSITIONS)
        layout.addWidget(self._position_grid)

        pad_row = QHBoxLayout()
        pad_row.addWidget(QLabel("Padding (px):"))
        self._padding_spin = QSpinBox()
        self._padding_spin.setRange(0, 500)
        self._padding_spin.setValue(20)
        self._padding_spin.setFixedWidth(80)
        pad_row.addWidget(self._padding_spin)
        pad_row.addStretch()
        layout.addLayout(pad_row)

        # --- Go ---
        self._go_btn = QPushButton("Apply Watermark")
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

        self._position_grid.select("bottom-right")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_file(self, path: str):
        self._input_path = path
        try:
            self._probe_info = probe(path)
            self._duration = get_duration_secs(self._probe_info)
            self._info.set_info(summarize(self._probe_info))
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._update_go_enabled()

    def _on_watermark_file(self, path: str):
        self._watermark_path = path
        self._update_go_enabled()

    def _on_mode_changed(self, index: int):
        is_image = index == 0
        self._image_group.setVisible(is_image)
        self._text_group.setVisible(not is_image)
        self._update_go_enabled()

    def _update_go_enabled(self):
        if not self._input_path:
            self._go_btn.setEnabled(False)
            return
        is_image = self._mode_combo.currentIndex() == 0
        if is_image:
            self._go_btn.setEnabled(bool(self._watermark_path))
        else:
            self._go_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Position math helpers
    # ------------------------------------------------------------------

    def _overlay_position(self, pad: int) -> str:
        """Return ffmpeg overlay x:y expression for the selected position."""
        sel = self._position_grid.selected()
        pos = sel[0] if sel else "bottom-right"
        positions = {
            "top-left": (f"{pad}", f"{pad}"),
            "top-right": (f"main_w-overlay_w-{pad}", f"{pad}"),
            "center": ("(main_w-overlay_w)/2", "(main_h-overlay_h)/2"),
            "bottom-left": (f"{pad}", f"main_h-overlay_h-{pad}"),
            "bottom-right": (f"main_w-overlay_w-{pad}", f"main_h-overlay_h-{pad}"),
        }
        x, y = positions[pos]
        return f"{x}:{y}"

    def _drawtext_position(self, pad: int) -> str:
        """Return ffmpeg drawtext x:y expression for the selected position."""
        sel = self._position_grid.selected()
        pos = sel[0] if sel else "bottom-right"
        positions = {
            "top-left": (f"{pad}", f"{pad}"),
            "top-right": (f"w-tw-{pad}", f"{pad}"),
            "center": ("(w-tw)/2", "(h-th)/2"),
            "bottom-left": (f"{pad}", f"h-th-{pad}"),
            "bottom-right": (f"w-tw-{pad}", f"h-th-{pad}"),
        }
        x, y = positions[pos]
        return x, y

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        is_image = self._mode_combo.currentIndex() == 0

        stem = Path(self._input_path).stem
        ext = Path(self._input_path).suffix
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_watermarked{ext}")

        if is_image:
            cmd = self._build_image_cmd(out_path)
        else:
            cmd = self._build_text_cmd(out_path)

        if cmd is None:
            return

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _build_image_cmd(self, out_path: str) -> list[str] | None:
        if not self._watermark_path:
            return None

        pad = self._padding_spin.value()
        scale_pct = self._scale_slider.value() / 100.0
        opacity = self._opacity_slider.value() / 100.0
        pos_expr = self._overlay_position(pad)

        # Scale watermark relative to video width, then overlay with opacity
        scale_w = f"iw*{scale_pct}*(main_w/iw)" if scale_pct < 1.0 else "main_w"
        # Simpler: scale watermark to scale_pct of main video width, keep aspect
        wm_scale = f"scale={scale_pct}*main_w:-1"

        # Build filter_complex:
        # [1:v] scale to percentage of input width -> [wm]
        # If opacity < 1, apply colorchannelmixer for alpha
        # [0:v][wm] overlay at position
        filter_parts = []
        if opacity < 1.0:
            filter_parts.append(
                f"[1:v]scale=iw*{scale_pct}:-1,format=rgba,"
                f"colorchannelmixer=aa={opacity}[wm];"
                f"[0:v][wm]overlay={pos_expr}"
            )
        else:
            filter_parts.append(
                f"[1:v]scale=iw*{scale_pct}:-1[wm];"
                f"[0:v][wm]overlay={pos_expr}"
            )

        filter_complex = filter_parts[0]

        return [
            "ffmpeg", "-y",
            "-i", self._input_path,
            "-i", self._watermark_path,
            "-filter_complex", filter_complex,
            "-c:a", "copy",
            "-progress", "pipe:1",
            out_path,
        ]

    def _build_text_cmd(self, out_path: str) -> list[str] | None:
        text = self._text_input.text().strip()
        if not text:
            self._progress.append_log("Error: no watermark text entered.")
            return None

        pad = self._padding_spin.value()
        font_size = self._font_size_spin.value()
        font_color = self._font_color_input.text().strip() or "#ffffff"
        x_expr, y_expr = self._drawtext_position(pad)

        # Escape special characters for ffmpeg drawtext
        escaped = text.replace("\\", "\\\\\\\\")
        escaped = escaped.replace("'", "\u2019")
        escaped = escaped.replace(":", "\\:")
        escaped = escaped.replace("%", "%%")

        drawtext = (
            f"drawtext=text='{escaped}'"
            f":fontsize={font_size}"
            f":fontcolor={font_color}"
            f":x={x_expr}:y={y_expr}"
        )

        if self._bg_check.isChecked():
            bg_color = self._bg_color_input.text().strip() or "#000000@0.5"
            drawtext += f":box=1:boxcolor={bg_color}:boxborderw={pad // 2}"

        return [
            "ffmpeg", "-y",
            "-i", self._input_path,
            "-vf", drawtext,
            "-c:a", "copy",
            "-progress", "pipe:1",
            out_path,
        ]

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
