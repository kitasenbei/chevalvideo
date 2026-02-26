"""Rotate, flip, and crop video page."""

import os
import re
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

ROTATION_PRESETS = [
    {"value": "transpose=1", "label": "90\u00b0 CW", "description": "Clockwise"},
    {"value": "transpose=2", "label": "90\u00b0 CCW", "description": "Counter-clockwise"},
    {"value": "transpose=1,transpose=1", "label": "180\u00b0", "description": "Upside down"},
    {"value": "none", "label": "None", "description": "No rotation"},
]

CROP_PRESETS = [
    {"value": "16:9", "label": "16:9", "description": "Widescreen"},
    {"value": "4:3", "label": "4:3", "description": "Standard"},
    {"value": "1:1", "label": "1:1", "description": "Square"},
    {"value": "9:16", "label": "9:16", "description": "Vertical"},
    {"value": "custom", "label": "Custom", "description": "Manual w/h/x/y"},
]


class RotatePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._duration = 0.0
        self._probe_info = {}
        self._video_width = 0
        self._video_height = 0
        self._runner = CommandRunner(self)
        self._cropdetect_runner = CommandRunner(self)
        self._detected_crop = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Rotate / Flip / Crop")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # --- ROTATION ---
        layout.addWidget(QLabel("Rotation:"))
        self._rotation_grid = OptionGrid(columns=4)
        self._rotation_grid.set_options(ROTATION_PRESETS)
        layout.addWidget(self._rotation_grid)

        # --- FLIP ---
        layout.addWidget(QLabel("Flip:"))
        self._hflip_check = QCheckBox("Horizontal flip")
        self._vflip_check = QCheckBox("Vertical flip")
        flip_row = QHBoxLayout()
        flip_row.addWidget(self._hflip_check)
        flip_row.addWidget(self._vflip_check)
        flip_row.addStretch()
        layout.addLayout(flip_row)

        # --- CROP ---
        layout.addWidget(QLabel("Crop:"))
        self._crop_grid = OptionGrid(columns=5)
        self._crop_grid.set_options(CROP_PRESETS)
        self._crop_grid.selection_changed.connect(self._on_crop_preset)
        layout.addWidget(self._crop_grid)

        # Custom crop controls (hidden by default)
        self._custom_crop_widget = QWidget()
        cc_layout = QHBoxLayout(self._custom_crop_widget)
        cc_layout.setContentsMargins(0, 0, 0, 0)

        cc_layout.addWidget(QLabel("W:"))
        self._crop_w = QSpinBox()
        self._crop_w.setRange(0, 7680)
        self._crop_w.setValue(0)
        self._crop_w.setFixedWidth(90)
        cc_layout.addWidget(self._crop_w)

        cc_layout.addWidget(QLabel("H:"))
        self._crop_h = QSpinBox()
        self._crop_h.setRange(0, 4320)
        self._crop_h.setValue(0)
        self._crop_h.setFixedWidth(90)
        cc_layout.addWidget(self._crop_h)

        cc_layout.addWidget(QLabel("X:"))
        self._crop_x = QSpinBox()
        self._crop_x.setRange(0, 7680)
        self._crop_x.setValue(0)
        self._crop_x.setFixedWidth(90)
        cc_layout.addWidget(self._crop_x)

        cc_layout.addWidget(QLabel("Y:"))
        self._crop_y = QSpinBox()
        self._crop_y.setRange(0, 4320)
        self._crop_y.setValue(0)
        self._crop_y.setFixedWidth(90)
        cc_layout.addWidget(self._crop_y)

        cc_layout.addStretch()
        self._custom_crop_widget.hide()
        layout.addWidget(self._custom_crop_widget)

        self._center_crop_check = QCheckBox("Center crop (auto-calculate x/y offsets)")
        self._center_crop_check.stateChanged.connect(self._update_center_crop)
        self._center_crop_check.hide()
        layout.addWidget(self._center_crop_check)

        # Connect spinbox changes to recalculate center offsets
        self._crop_w.valueChanged.connect(self._update_center_crop)
        self._crop_h.valueChanged.connect(self._update_center_crop)

        # --- AUTO-CROP ---
        layout.addWidget(QLabel("Auto-crop:"))
        self._autocrop_check = QCheckBox("Auto-detect black bars")
        layout.addWidget(self._autocrop_check)

        # --- GO ---
        self._go_btn = QPushButton("Process")
        self._go_btn.clicked.connect(self._run)
        self._go_btn.setEnabled(False)
        layout.addWidget(self._go_btn)

        self._progress = ProgressWidget()
        self._progress.cancel_button.clicked.connect(self._runner.cancel)
        layout.addWidget(self._progress)

        self._runner.progress.connect(self._progress.set_progress)
        self._runner.output.connect(self._progress.append_log)
        self._runner.finished.connect(self._on_done)

        self._cropdetect_runner.output.connect(self._on_cropdetect_output)
        self._cropdetect_runner.finished.connect(self._on_cropdetect_done)

        layout.addStretch()

        self._rotation_grid.select("none")

    # ---- slots ----

    def _on_file(self, path: str):
        self._input_path = path
        self._detected_crop = ""
        try:
            self._probe_info = probe(path)
            self._duration = get_duration_secs(self._probe_info)
            self._info.set_info(summarize(self._probe_info))
            # Extract video dimensions
            for s in self._probe_info.get("streams", []):
                if s.get("codec_type") == "video":
                    self._video_width = int(s.get("width", 0))
                    self._video_height = int(s.get("height", 0))
                    break
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._go_btn.setEnabled(True)

    def _on_crop_preset(self, sel):
        is_custom = sel == ["custom"]
        self._custom_crop_widget.setVisible(is_custom)
        self._center_crop_check.setVisible(is_custom)

    def _update_center_crop(self):
        if not self._center_crop_check.isChecked():
            return
        w = self._crop_w.value()
        h = self._crop_h.value()
        if self._video_width > 0 and w > 0:
            self._crop_x.setValue(max(0, (self._video_width - w) // 2))
        if self._video_height > 0 and h > 0:
            self._crop_y.setValue(max(0, (self._video_height - h) // 2))

    def _build_vf(self) -> str:
        """Build the combined -vf filter string from all sections."""
        filters = []

        # Rotation
        rot_sel = self._rotation_grid.selected()
        if rot_sel and rot_sel[0] != "none":
            filters.append(rot_sel[0])

        # Flip
        if self._hflip_check.isChecked():
            filters.append("hflip")
        if self._vflip_check.isChecked():
            filters.append("vflip")

        # Crop (auto-crop overrides preset/custom crop)
        if self._autocrop_check.isChecked() and self._detected_crop:
            filters.append(self._detected_crop)
        else:
            crop_sel = self._crop_grid.selected()
            if crop_sel:
                crop_val = crop_sel[0]
                if crop_val == "custom":
                    w = self._crop_w.value()
                    h = self._crop_h.value()
                    x = self._crop_x.value()
                    y = self._crop_y.value()
                    if w > 0 and h > 0:
                        filters.append(f"crop={w}:{h}:{x}:{y}")
                elif crop_val != "custom":
                    crop_filter = self._ratio_to_crop(crop_val)
                    if crop_filter:
                        filters.append(crop_filter)

        return ",".join(filters)

    def _ratio_to_crop(self, ratio: str) -> str:
        """Convert an aspect ratio like '16:9' to a crop expression."""
        parts = ratio.split(":")
        if len(parts) != 2:
            return ""
        rw, rh = int(parts[0]), int(parts[1])
        # Use ffmpeg expressions so it works on any resolution
        # crop=min(iw,ih*rw/rh):min(ih,iw*rh/rw)
        # centered: (iw-ow)/2:(ih-oh)/2
        return (
            f"crop='min(iw,ih*{rw}/{rh})':'min(ih,iw*{rh}/{rw})':"
            f"'(iw-ow)/2':'(ih-oh)/2'"
        )

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        # If auto-crop is requested and we haven't detected yet, do cropdetect first
        if self._autocrop_check.isChecked() and not self._detected_crop:
            self._run_cropdetect()
            return

        vf = self._build_vf()

        ext = Path(self._input_path).suffix
        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_transformed{ext}")

        cmd = ["ffmpeg", "-y", "-i", self._input_path]
        if vf:
            cmd += ["-vf", vf]
        cmd += ["-c:a", "copy", "-progress", "pipe:1", out_path]

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _run_cropdetect(self):
        """Run a short cropdetect pass to find black bar dimensions."""
        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._progress.append_log("Detecting black bars...")

        # Analyse ~10 seconds starting at 30s in (or from start for short videos)
        start = "30" if self._duration > 40 else "0"
        cmd = [
            "ffmpeg", "-ss", start, "-i", self._input_path,
            "-t", "10", "-vf", "cropdetect=24:16:0",
            "-f", "null", "-",
        ]
        self._cropdetect_runner.run(cmd, duration=0)

    def _on_cropdetect_output(self, line: str):
        # Capture the last cropdetect line: crop=W:H:X:Y
        m = re.search(r"crop=(\d+:\d+:\d+:\d+)", line)
        if m:
            self._detected_crop = f"crop={m.group(1)}"

    def _on_cropdetect_done(self, ok, msg):
        if ok and self._detected_crop:
            self._progress.append_log(f"Detected: {self._detected_crop}")
            # Now run the actual encode with the detected crop
            self._run()
        else:
            self._progress.set_running(False)
            self._go_btn.setEnabled(True)
            if not self._detected_crop:
                self._progress.append_log("Could not detect crop area. No black bars found.")
            else:
                self._progress.append_log(f"Cropdetect failed: {msg}")

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
