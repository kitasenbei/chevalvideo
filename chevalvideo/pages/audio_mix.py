"""Audio track manipulation page."""

import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from chevalvideo.probe import probe, summarize, get_duration_secs
from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.file_picker import FileDropWidget
from chevalvideo.widgets.media_info import MediaInfoWidget
from chevalvideo.widgets.option_grid import OptionGrid
from chevalvideo.widgets.progress import ProgressWidget

AUDIO_FILTERS = "Audio files (*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.opus);;All files (*)"

MODES = [
    {"value": "replace", "label": "Replace Audio", "description": "Swap audio track entirely"},
    {"value": "add", "label": "Add Track", "description": "Add additional audio track"},
    {"value": "mix", "label": "Mix/Overlay", "description": "Mix original with new audio"},
    {"value": "remove", "label": "Remove Audio", "description": "Strip all audio"},
    {"value": "normalize", "label": "Normalize", "description": "EBU R128 loudnorm"},
    {"value": "volume", "label": "Volume", "description": "Adjust volume level"},
]


class AudioMixPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_path = ""
        self._audio_path = ""
        self._duration = 0.0
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Audio Mix")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        # Video input
        self._file_drop = FileDropWidget()
        self._file_drop.file_selected.connect(self._on_file)
        layout.addWidget(self._file_drop)

        self._info = MediaInfoWidget()
        layout.addWidget(self._info)

        # Mode selection
        layout.addWidget(QLabel("Mode:"))
        self._mode_grid = OptionGrid(columns=3)
        self._mode_grid.set_options(MODES)
        self._mode_grid.selection_changed.connect(self._on_mode_changed)
        layout.addWidget(self._mode_grid)

        # --- Replace mode panel ---
        self._replace_panel = QWidget()
        rp_layout = QVBoxLayout(self._replace_panel)
        rp_layout.setContentsMargins(0, 0, 0, 0)
        rp_layout.setSpacing(8)

        rp_row = QHBoxLayout()
        rp_row.addWidget(QLabel("New audio file:"))
        self._replace_file_label = QLabel("No file selected")
        rp_row.addWidget(self._replace_file_label, 1)
        self._replace_browse_btn = QPushButton("Browse")
        self._replace_browse_btn.setFixedWidth(100)
        self._replace_browse_btn.clicked.connect(lambda: self._pick_audio("replace"))
        rp_row.addWidget(self._replace_browse_btn)
        rp_layout.addLayout(rp_row)

        self._shortest_cb = QCheckBox("Trim to shortest (if audio/video lengths differ)")
        self._shortest_cb.setChecked(True)
        rp_layout.addWidget(self._shortest_cb)

        self._replace_panel.hide()
        layout.addWidget(self._replace_panel)

        # --- Add track mode panel ---
        self._add_panel = QWidget()
        ap_layout = QVBoxLayout(self._add_panel)
        ap_layout.setContentsMargins(0, 0, 0, 0)
        ap_layout.setSpacing(8)

        ap_row = QHBoxLayout()
        ap_row.addWidget(QLabel("Additional audio:"))
        self._add_file_label = QLabel("No file selected")
        ap_row.addWidget(self._add_file_label, 1)
        self._add_browse_btn = QPushButton("Browse")
        self._add_browse_btn.setFixedWidth(100)
        self._add_browse_btn.clicked.connect(lambda: self._pick_audio("add"))
        ap_row.addWidget(self._add_browse_btn)
        ap_layout.addLayout(ap_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Language code:"))
        self._lang_input = QLineEdit()
        self._lang_input.setPlaceholderText("e.g. eng, fra, jpn")
        self._lang_input.setFixedWidth(120)
        lang_row.addWidget(self._lang_input)
        lang_row.addStretch()
        ap_layout.addLayout(lang_row)

        self._add_panel.hide()
        layout.addWidget(self._add_panel)

        # --- Mix mode panel ---
        self._mix_panel = QWidget()
        mp_layout = QVBoxLayout(self._mix_panel)
        mp_layout.setContentsMargins(0, 0, 0, 0)
        mp_layout.setSpacing(8)

        mp_row = QHBoxLayout()
        mp_row.addWidget(QLabel("Audio to mix in:"))
        self._mix_file_label = QLabel("No file selected")
        mp_row.addWidget(self._mix_file_label, 1)
        self._mix_browse_btn = QPushButton("Browse")
        self._mix_browse_btn.setFixedWidth(100)
        self._mix_browse_btn.clicked.connect(lambda: self._pick_audio("mix"))
        mp_row.addWidget(self._mix_browse_btn)
        mp_layout.addLayout(mp_row)

        orig_row = QHBoxLayout()
        orig_row.addWidget(QLabel("Original volume:"))
        self._orig_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._orig_vol_slider.setRange(0, 200)
        self._orig_vol_slider.setValue(100)
        self._orig_vol_label = QLabel("100%")
        self._orig_vol_slider.valueChanged.connect(
            lambda v: self._orig_vol_label.setText(f"{v}%")
        )
        orig_row.addWidget(self._orig_vol_slider, 1)
        orig_row.addWidget(self._orig_vol_label)
        mp_layout.addLayout(orig_row)

        overlay_row = QHBoxLayout()
        overlay_row.addWidget(QLabel("Overlay volume:"))
        self._overlay_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._overlay_vol_slider.setRange(0, 200)
        self._overlay_vol_slider.setValue(100)
        self._overlay_vol_label = QLabel("100%")
        self._overlay_vol_slider.valueChanged.connect(
            lambda v: self._overlay_vol_label.setText(f"{v}%")
        )
        overlay_row.addWidget(self._overlay_vol_slider, 1)
        overlay_row.addWidget(self._overlay_vol_label)
        mp_layout.addLayout(overlay_row)

        self._mix_panel.hide()
        layout.addWidget(self._mix_panel)

        # --- Remove mode panel (no extra controls needed) ---
        self._remove_panel = QWidget()
        rm_layout = QVBoxLayout(self._remove_panel)
        rm_layout.setContentsMargins(0, 0, 0, 0)
        rm_layout.addWidget(QLabel("All audio tracks will be stripped from the video."))
        self._remove_panel.hide()
        layout.addWidget(self._remove_panel)

        # --- Normalize mode panel ---
        self._normalize_panel = QWidget()
        np_layout = QVBoxLayout(self._normalize_panel)
        np_layout.setContentsMargins(0, 0, 0, 0)
        np_layout.setSpacing(8)

        lufs_row = QHBoxLayout()
        lufs_row.addWidget(QLabel("Target LUFS:"))
        self._lufs_spin = QSpinBox()
        self._lufs_spin.setRange(-50, 0)
        self._lufs_spin.setValue(-14)
        self._lufs_spin.setSuffix(" LUFS")
        self._lufs_spin.setFixedWidth(120)
        lufs_row.addWidget(self._lufs_spin)
        lufs_row.addStretch()
        np_layout.addLayout(lufs_row)

        self._normalize_panel.hide()
        layout.addWidget(self._normalize_panel)

        # --- Volume mode panel ---
        self._volume_panel = QWidget()
        vp_layout = QVBoxLayout(self._volume_panel)
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.setSpacing(8)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Volume:"))
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 500)
        self._vol_slider.setValue(100)
        self._vol_pct_label = QLabel("100%")
        self._vol_slider.valueChanged.connect(self._on_vol_slider_changed)
        vol_row.addWidget(self._vol_slider, 1)
        vol_row.addWidget(self._vol_pct_label)
        vp_layout.addLayout(vol_row)

        db_row = QHBoxLayout()
        db_row.addWidget(QLabel("Or set in dB:"))
        self._db_spin = QDoubleSpinBox()
        self._db_spin.setRange(-60.0, 30.0)
        self._db_spin.setValue(0.0)
        self._db_spin.setSuffix(" dB")
        self._db_spin.setSingleStep(0.5)
        self._db_spin.setFixedWidth(120)
        self._db_spin.valueChanged.connect(self._on_db_changed)
        db_row.addWidget(self._db_spin)
        db_row.addStretch()
        vp_layout.addLayout(db_row)

        self._volume_panel.hide()
        layout.addWidget(self._volume_panel)

        # --- Go button ---
        self._go_btn = QPushButton("Run")
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

        # Default mode
        self._mode_grid.select("replace")
        self._on_mode_changed(["replace"])

        # Track whether volume slider or dB spin is being updated programmatically
        self._syncing_volume = False

    # ── File handling ──────────────────────────────────────────────

    def _on_file(self, path: str):
        self._input_path = path
        try:
            info = probe(path)
            self._duration = get_duration_secs(info)
            self._info.set_info(summarize(info))
        except Exception as e:
            self._progress.append_log(f"Probe error: {e}")
        self._go_btn.setEnabled(True)

    def _pick_audio(self, target: str):
        path, _ = QFileDialog.getOpenFileName(self, "Select audio file", "", AUDIO_FILTERS)
        if not path:
            return
        self._audio_path = path
        name = Path(path).name
        if target == "replace":
            self._replace_file_label.setText(name)
        elif target == "add":
            self._add_file_label.setText(name)
        elif target == "mix":
            self._mix_file_label.setText(name)

    # ── Mode switching ─────────────────────────────────────────────

    def _on_mode_changed(self, sel):
        mode = sel[0] if sel else ""
        self._replace_panel.setVisible(mode == "replace")
        self._add_panel.setVisible(mode == "add")
        self._mix_panel.setVisible(mode == "mix")
        self._remove_panel.setVisible(mode == "remove")
        self._normalize_panel.setVisible(mode == "normalize")
        self._volume_panel.setVisible(mode == "volume")

    # ── Volume sync ────────────────────────────────────────────────

    def _on_vol_slider_changed(self, value):
        self._vol_pct_label.setText(f"{value}%")
        if self._syncing_volume:
            return
        self._syncing_volume = True
        # Convert percentage to dB: dB = 20 * log10(pct/100)
        import math
        if value > 0:
            db = 20 * math.log10(value / 100)
        else:
            db = -60.0
        self._db_spin.setValue(db)
        self._syncing_volume = False

    def _on_db_changed(self, db):
        if self._syncing_volume:
            return
        self._syncing_volume = True
        # Convert dB to percentage: pct = 10^(dB/20) * 100
        import math
        pct = int(math.pow(10, db / 20) * 100)
        pct = max(0, min(500, pct))
        self._vol_slider.setValue(pct)
        self._syncing_volume = False

    # ── Build & run command ────────────────────────────────────────

    def _run(self):
        if not self._input_path or self._runner.is_running():
            return

        mode_sel = self._mode_grid.selected()
        if not mode_sel:
            return
        mode = mode_sel[0]

        stem = Path(self._input_path).stem
        ext = Path(self._input_path).suffix
        out_dir = str(Path(self._input_path).parent)
        out_path = os.path.join(out_dir, f"{stem}_audio{ext}")

        cmd = self._build_cmd(mode, out_path)
        if cmd is None:
            return

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd, duration=self._duration)

    def _build_cmd(self, mode: str, out_path: str):
        if mode == "replace":
            if not self._audio_path:
                self._progress.append_log("Error: no audio file selected")
                return None
            cmd = [
                "ffmpeg", "-y",
                "-i", self._input_path,
                "-i", self._audio_path,
                "-c:v", "copy",
                "-map", "0:v",
                "-map", "1:a",
            ]
            if self._shortest_cb.isChecked():
                cmd.append("-shortest")
            cmd += ["-progress", "pipe:1", out_path]
            return cmd

        elif mode == "add":
            if not self._audio_path:
                self._progress.append_log("Error: no audio file selected")
                return None
            cmd = [
                "ffmpeg", "-y",
                "-i", self._input_path,
                "-i", self._audio_path,
                "-map", "0",
                "-map", "1:a",
                "-c", "copy",
            ]
            lang = self._lang_input.text().strip()
            if lang:
                cmd += ["-metadata:s:a:1", f"language={lang}"]
            cmd += ["-progress", "pipe:1", out_path]
            return cmd

        elif mode == "mix":
            if not self._audio_path:
                self._progress.append_log("Error: no audio file selected")
                return None
            orig_vol = self._orig_vol_slider.value() / 100.0
            overlay_vol = self._overlay_vol_slider.value() / 100.0
            filter_str = (
                f"[0:a]volume={orig_vol}[a0];"
                f"[1:a]volume={overlay_vol}[a1];"
                f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", self._input_path,
                "-i", self._audio_path,
                "-filter_complex", filter_str,
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-progress", "pipe:1", out_path,
            ]
            return cmd

        elif mode == "remove":
            cmd = [
                "ffmpeg", "-y",
                "-i", self._input_path,
                "-c:v", "copy",
                "-an",
                "-progress", "pipe:1", out_path,
            ]
            return cmd

        elif mode == "normalize":
            target_lufs = self._lufs_spin.value()
            filter_str = f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11"
            cmd = [
                "ffmpeg", "-y",
                "-i", self._input_path,
                "-c:v", "copy",
                "-af", filter_str,
                "-progress", "pipe:1", out_path,
            ]
            return cmd

        elif mode == "volume":
            import math
            db = self._db_spin.value()
            filter_str = f"volume={db}dB"
            cmd = [
                "ffmpeg", "-y",
                "-i", self._input_path,
                "-c:v", "copy",
                "-af", filter_str,
                "-progress", "pipe:1", out_path,
            ]
            return cmd

        return None

    # ── Completion ─────────────────────────────────────────────────

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
