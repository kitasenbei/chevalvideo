"""Playback speed change page."""

import math
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

SPEED_PRESETS = [
    {"value": "0.25", "label": "0.25x", "description": "Quarter speed"},
    {"value": "0.5", "label": "0.5x", "description": "Half speed"},
    {"value": "0.75", "label": "0.75x", "description": "Slow"},
    {"value": "1.5", "label": "1.5x", "description": "Slightly fast"},
    {"value": "2", "label": "2x", "description": "Double speed"},
    {"value": "4", "label": "4x", "description": "Quadruple speed"},
]


def _build_atempo_chain(speed: float) -> list[str]:
    """Build a chain of atempo filters for the given speed factor.

    The atempo filter only accepts values in [0.5, 100.0], so for speeds
    below 0.5 we chain multiple atempo filters. For example, 0.25x
    requires two atempo=0.5 filters in sequence.
    """
    filters = []
    remaining = speed
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    while remaining > 100.0:
        filters.append("atempo=100.0")
        remaining /= 100.0
    filters.append(f"atempo={remaining:.6g}")
    return filters


class SpeedPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._probe_info = {}
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Speed")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # Speed presets
        layout.addWidget(QLabel("Speed preset:"))
        self._preset_grid = OptionGrid(columns=6)
        self._preset_grid.set_options(SPEED_PRESETS)
        self._preset_grid.selection_changed.connect(self._on_preset)
        layout.addWidget(self._preset_grid)

        # Custom speed input
        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Custom speed:"))
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(0.1, 100.0)
        self._speed_spin.setDecimals(2)
        self._speed_spin.setSingleStep(0.1)
        self._speed_spin.setValue(1.0)
        self._speed_spin.setSuffix("x")
        self._speed_spin.setFixedWidth(120)
        self._speed_spin.valueChanged.connect(self._on_custom_speed)
        custom_row.addWidget(self._speed_spin)
        custom_row.addStretch()
        layout.addLayout(custom_row)

        # Audio options
        self._adjust_pitch = QCheckBox("Adjust audio pitch (asetrate — pitch shifts with speed)")
        layout.addWidget(self._adjust_pitch)

        self._drop_audio = QCheckBox("Drop audio")
        layout.addWidget(self._drop_audio)

        # Smooth motion
        self._smooth_motion = QCheckBox("Smooth motion (frame interpolation via minterpolate)")
        layout.addWidget(self._smooth_motion)

        # FPS override
        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("Output FPS override (0 = auto):"))
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(0, 240)
        self._fps_spin.setValue(0)
        self._fps_spin.setFixedWidth(100)
        fps_row.addWidget(self._fps_spin)
        fps_row.addStretch()
        layout.addLayout(fps_row)

        # Run button
        self._go_btn = QPushButton("Change Speed")
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

        self._preset_grid.select("2")

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
        """Sync the custom spinbox when a preset is picked."""
        if sel:
            self._speed_spin.setValue(float(sel[0]))

    def _on_custom_speed(self, value):
        """Deselect presets when the user changes the spinbox manually."""
        # If the current value matches a preset, select it; otherwise clear
        matched = False
        for preset in SPEED_PRESETS:
            if math.isclose(value, float(preset["value"]), rel_tol=1e-4):
                self._preset_grid.select(preset["value"])
                matched = True
                break
        if not matched:
            # Deselect all presets by selecting a non-existent value
            self._preset_grid.select("")

    def _get_speed(self) -> float:
        return self._speed_spin.value()

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        speed = self._get_speed()
        if speed <= 0:
            return

        drop_audio = self._drop_audio.isChecked()
        adjust_pitch = self._adjust_pitch.isChecked()
        smooth = self._smooth_motion.isChecked()
        fps_override = self._fps_spin.value()

        ext = Path(self._input_path).suffix
        stem = Path(self._input_path).stem
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_{speed}x{ext}")

        # Build video filter chain
        vfilters = [f"setpts=PTS/{speed}"]
        if smooth:
            if fps_override > 0:
                vfilters.append(f"minterpolate=fps={fps_override}:mi_mode=mci")
            else:
                vfilters.append("minterpolate=mi_mode=mci")
        elif fps_override > 0:
            vfilters.append(f"fps={fps_override}")

        vf = ",".join(vfilters)

        cmd = ["ffmpeg", "-y", "-i", self._input_path, "-vf", vf]

        if drop_audio:
            cmd += ["-an"]
        elif adjust_pitch:
            # asetrate shifts pitch by changing the sample rate, then
            # aresample brings it back to the original rate so the
            # container is well-formed.
            audio_sr = self._get_audio_sample_rate()
            new_rate = int(audio_sr * speed)
            cmd += ["-af", f"asetrate={new_rate},aresample={audio_sr}"]
        else:
            # Use atempo chain for speed without pitch change
            atempo_chain = _build_atempo_chain(speed)
            cmd += ["-af", ",".join(atempo_chain)]

        cmd += ["-progress", "pipe:1", out_path]

        # Estimate output duration for progress tracking
        out_duration = self._duration / speed if speed > 0 else self._duration

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=out_duration)

    def _get_audio_sample_rate(self) -> int:
        """Return the audio sample rate from probe info, defaulting to 44100."""
        for s in self._probe_info.get("streams", []):
            if s.get("codec_type") == "audio":
                try:
                    return int(s["sample_rate"])
                except (KeyError, ValueError):
                    pass
        return 44100

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
