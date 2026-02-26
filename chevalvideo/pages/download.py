"""yt-dlp download page — full power tool."""

import json
import subprocess
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.progress import ProgressWidget


class DownloadPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._url = ""
        self._formats = []
        self._video_info = {}
        self._out_dir = str(Path.home() / "Downloads")
        self._runner = CommandRunner(self)
        self._fetch_proc = None
        self._fetch_buf = b""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        heading = QLabel("Download")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        # ── URL input ──
        url_row = QHBoxLayout()
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("Paste video URL here...")
        self._url_input.returnPressed.connect(self._fetch)
        url_row.addWidget(self._url_input, 1)
        self._fetch_btn = QPushButton("Fetch")
        self._fetch_btn.clicked.connect(self._fetch)
        url_row.addWidget(self._fetch_btn)
        layout.addLayout(url_row)

        # ── Video info bar ──
        self._info_label = QLabel("")
        self._info_label.setObjectName("subheading")
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)

        # ── Options grid ──
        opts = QGroupBox("Options")
        opts_grid = QGridLayout(opts)
        opts_grid.setSpacing(8)

        # Row 0: output dir
        opts_grid.addWidget(QLabel("Save to:"), 0, 0)
        dir_row = QHBoxLayout()
        self._dir_label = QLabel(self._out_dir)
        dir_row.addWidget(self._dir_label, 1)
        dir_btn = QPushButton("...")
        dir_btn.setFixedWidth(36)
        dir_btn.clicked.connect(self._pick_dir)
        dir_row.addWidget(dir_btn)
        opts_grid.addLayout(dir_row, 0, 1, 1, 3)

        # Row 1: filename template
        opts_grid.addWidget(QLabel("Filename:"), 1, 0)
        self._filename_input = QLineEdit("%(title)s.%(ext)s")
        self._filename_input.setPlaceholderText("%(title)s.%(ext)s")
        opts_grid.addWidget(self._filename_input, 1, 1, 1, 3)

        # Row 2: format selection mode
        opts_grid.addWidget(QLabel("Format:"), 2, 0)
        self._format_combo = QComboBox()
        self._format_combo.addItems([
            "Best (video+audio)",
            "Best video + best audio (merge)",
            "Best audio only",
            "Worst (smallest)",
            "Pick from table",
        ])
        self._format_combo.currentIndexChanged.connect(self._on_format_mode)
        opts_grid.addWidget(self._format_combo, 2, 1, 1, 3)

        # Row 3: merge format, container
        opts_grid.addWidget(QLabel("Merge into:"), 3, 0)
        self._merge_combo = QComboBox()
        self._merge_combo.addItems(["mkv", "mp4", "webm", "Don't merge"])
        opts_grid.addWidget(self._merge_combo, 3, 1)

        opts_grid.addWidget(QLabel("Recode to:"), 3, 2)
        self._recode_combo = QComboBox()
        self._recode_combo.addItems(["Don't recode", "mp4", "mkv", "webm", "mp3", "flac", "wav", "ogg"])
        opts_grid.addWidget(self._recode_combo, 3, 3)

        # Row 4: checkboxes
        checks_row1 = QHBoxLayout()
        self._playlist_check = QCheckBox("Full playlist")
        self._subs_check = QCheckBox("Subtitles")
        self._thumb_check = QCheckBox("Embed thumbnail")
        self._metadata_check = QCheckBox("Embed metadata")
        self._metadata_check.setChecked(True)
        checks_row1.addWidget(self._playlist_check)
        checks_row1.addWidget(self._subs_check)
        checks_row1.addWidget(self._thumb_check)
        checks_row1.addWidget(self._metadata_check)
        checks_row1.addStretch()
        opts_grid.addLayout(checks_row1, 4, 0, 1, 4)

        # Row 5: more checkboxes
        checks_row2 = QHBoxLayout()
        self._chapters_check = QCheckBox("Embed chapters")
        self._chapters_check.setChecked(True)
        self._sponsorblock_check = QCheckBox("SponsorBlock remove")
        self._cookies_check = QCheckBox("Use browser cookies")
        self._aria2_check = QCheckBox("aria2c downloader")
        checks_row2.addWidget(self._chapters_check)
        checks_row2.addWidget(self._sponsorblock_check)
        checks_row2.addWidget(self._cookies_check)
        checks_row2.addWidget(self._aria2_check)
        checks_row2.addStretch()
        opts_grid.addLayout(checks_row2, 5, 0, 1, 4)

        # Row 6: subtitle lang, cookies browser, rate limit, concurrent frags
        opts_grid.addWidget(QLabel("Sub lang:"), 6, 0)
        self._sub_lang_input = QLineEdit("en")
        self._sub_lang_input.setFixedWidth(80)
        opts_grid.addWidget(self._sub_lang_input, 6, 1)

        opts_grid.addWidget(QLabel("Browser:"), 6, 2)
        self._browser_combo = QComboBox()
        self._browser_combo.addItems(["firefox", "chrome", "chromium", "brave", "edge", "opera", "safari"])
        opts_grid.addWidget(self._browser_combo, 6, 3)

        # Row 7: rate limit, concurrent fragments
        opts_grid.addWidget(QLabel("Rate limit:"), 7, 0)
        self._rate_input = QLineEdit()
        self._rate_input.setPlaceholderText("e.g. 5M, 500K")
        self._rate_input.setFixedWidth(100)
        opts_grid.addWidget(self._rate_input, 7, 1)

        opts_grid.addWidget(QLabel("Fragments:"), 7, 2)
        self._frags_spin = QSpinBox()
        self._frags_spin.setRange(1, 32)
        self._frags_spin.setValue(1)
        opts_grid.addWidget(self._frags_spin, 7, 3)

        # Row 8: extra args
        opts_grid.addWidget(QLabel("Extra args:"), 8, 0)
        self._extra_input = QLineEdit()
        self._extra_input.setPlaceholderText("--geo-bypass --sleep-interval 2 ...")
        opts_grid.addWidget(self._extra_input, 8, 1, 1, 3)

        layout.addWidget(opts)

        # ── Format table ──
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["ID", "Ext", "Resolution", "FPS", "Codec", "Size", "Note"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setVisible(False)
        layout.addWidget(self._table)

        # ── Go ──
        btn_row = QHBoxLayout()
        self._go_btn = QPushButton("Download")
        self._go_btn.clicked.connect(self._run)
        self._go_btn.setEnabled(False)
        btn_row.addWidget(self._go_btn)
        self._audio_btn = QPushButton("Audio Only")
        self._audio_btn.clicked.connect(self._run_audio)
        self._audio_btn.setEnabled(False)
        btn_row.addWidget(self._audio_btn)
        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.clicked.connect(self._open_folder)
        self._open_folder_btn.setVisible(False)
        btn_row.addWidget(self._open_folder_btn)
        layout.addLayout(btn_row)

        # ── Progress ──
        self._progress = ProgressWidget()
        self._progress.cancel_button.clicked.connect(self._runner.cancel)
        layout.addWidget(self._progress)

        self._runner.progress.connect(self._progress.set_progress)
        self._runner.output.connect(self._progress.append_log)
        self._runner.finished.connect(self._on_done)

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Save to", self._out_dir)
        if d:
            self._out_dir = d
            self._dir_label.setText(d)

    def _on_format_mode(self, idx):
        self._table.setVisible(idx == 4)

    # ── Fetch formats ──

    def _fetch(self):
        url = self._url_input.text().strip()
        if not url or self._fetch_proc is not None:
            return
        self._url = url
        self._fetch_buf = b""
        self._fetch_btn.setEnabled(False)
        self._info_label.setText("Fetching...")
        self._progress.append_log(f"Fetching formats for {url}...")

        cmd = ["yt-dlp", "-j", "--no-download"]
        if not self._playlist_check.isChecked():
            cmd.append("--no-playlist")
        cmd.append(url)

        self._progress.append_log(f"$ {' '.join(cmd)}")
        self._fetch_proc = QProcess(self)
        self._fetch_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._fetch_proc.readyReadStandardOutput.connect(self._on_fetch_output)
        self._fetch_proc.finished.connect(self._on_fetch_done)
        self._fetch_proc.start(cmd[0], cmd[1:])

    def _on_fetch_output(self):
        self._fetch_buf += self._fetch_proc.readAllStandardOutput().data()

    def _on_fetch_done(self, exit_code, _status):
        self._fetch_proc = None
        self._fetch_btn.setEnabled(True)

        if exit_code != 0:
            self._info_label.setText("Fetch failed")
            self._progress.append_log(f"yt-dlp exited with code {exit_code}")
            text = self._fetch_buf.decode(errors="replace").strip()
            if text:
                self._progress.append_log(text)
            return

        text = self._fetch_buf.decode(errors="replace").strip()
        lines = [l for l in text.splitlines() if l.strip().startswith("{")]
        if not lines:
            self._info_label.setText("No info returned")
            self._progress.append_log("No format info returned")
            return

        try:
            info = json.loads(lines[0])
        except json.JSONDecodeError as e:
            self._progress.append_log(f"JSON parse error: {e}")
            return

        self._video_info = info

        # Show video info
        title = info.get("title", "?")
        uploader = info.get("uploader", "?")
        duration = info.get("duration_string", info.get("duration", "?"))
        view_count = info.get("view_count")
        views = f"{view_count:,}" if view_count else "?"
        self._info_label.setText(
            f"{title}  |  {uploader}  |  {duration}  |  {views} views"
        )

        # Populate format table
        self._formats = info.get("formats", [])
        self._table.setRowCount(len(self._formats))
        for i, f in enumerate(self._formats):
            self._table.setItem(i, 0, QTableWidgetItem(str(f.get("format_id", ""))))
            self._table.setItem(i, 1, QTableWidgetItem(f.get("ext", "")))
            if f.get("width"):
                res = f"{f.get('width', '?')}x{f.get('height', '?')}"
            elif f.get("acodec") and f.get("acodec") != "none":
                res = "audio"
            else:
                res = ""
            self._table.setItem(i, 2, QTableWidgetItem(res))
            fps = str(f.get("fps", "")) if f.get("fps") else ""
            self._table.setItem(i, 3, QTableWidgetItem(fps))
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            codec = ""
            if vcodec and vcodec != "none":
                codec += vcodec.split(".")[0]
            if acodec and acodec != "none":
                codec += (" + " if codec else "") + acodec.split(".")[0]
            self._table.setItem(i, 4, QTableWidgetItem(codec))
            size = f.get("filesize") or f.get("filesize_approx")
            size_str = f"{size / 1048576:.1f} MB" if size else ""
            self._table.setItem(i, 5, QTableWidgetItem(size_str))
            self._table.setItem(i, 6, QTableWidgetItem(f.get("format_note", "")))

        self._go_btn.setEnabled(True)
        self._audio_btn.setEnabled(True)
        self._progress.append_log(f"Found {len(self._formats)} formats")
        if len(lines) > 1:
            self._progress.append_log(f"Playlist: {len(lines)} videos (showing first)")

    # ── Build command ──

    def _build_cmd(self, *, audio_only=False) -> list[str]:
        cmd = ["yt-dlp"]

        # Output template
        template = self._filename_input.text().strip() or "%(title)s.%(ext)s"
        cmd += ["-o", f"{self._out_dir}/{template}"]

        # Playlist
        if self._playlist_check.isChecked():
            cmd.append("--yes-playlist")
        else:
            cmd.append("--no-playlist")

        # Format selection
        if audio_only:
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            fmt_idx = self._format_combo.currentIndex()
            if fmt_idx == 4:
                # Pick from table
                sel = self._table.selectedItems()
                if sel:
                    row = sel[0].row()
                    fmt_id = self._formats[row].get("format_id")
                    if fmt_id:
                        cmd += ["-f", fmt_id]
            elif fmt_idx == 0:
                cmd += ["-f", "bv*+ba/b"]
            elif fmt_idx == 1:
                cmd += ["-f", "bv+ba"]
            elif fmt_idx == 2:
                cmd += ["-f", "ba"]
            elif fmt_idx == 3:
                cmd += ["-f", "wv*+wa/w"]

        # Merge format
        if not audio_only:
            merge = self._merge_combo.currentText()
            if merge != "Don't merge":
                cmd += ["--merge-output-format", merge]

        # Recode
        recode = self._recode_combo.currentText()
        if recode != "Don't recode":
            cmd += ["--recode-video", recode]

        # Subtitles
        if self._subs_check.isChecked():
            lang = self._sub_lang_input.text().strip() or "en"
            cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", lang, "--embed-subs"]

        # Thumbnail
        if self._thumb_check.isChecked():
            cmd += ["--embed-thumbnail"]

        # Metadata
        if self._metadata_check.isChecked():
            cmd += ["--embed-metadata"]

        # Chapters
        if self._chapters_check.isChecked():
            cmd += ["--embed-chapters"]

        # SponsorBlock
        if self._sponsorblock_check.isChecked():
            cmd += ["--sponsorblock-remove", "all"]

        # Cookies
        if self._cookies_check.isChecked():
            browser = self._browser_combo.currentText()
            cmd += ["--cookies-from-browser", browser]

        # aria2c
        if self._aria2_check.isChecked():
            cmd += ["--downloader", "aria2c"]

        # Rate limit
        rate = self._rate_input.text().strip()
        if rate:
            cmd += ["-r", rate]

        # Concurrent fragments
        frags = self._frags_spin.value()
        if frags > 1:
            cmd += ["--concurrent-fragments", str(frags)]

        # Extra args
        extra = self._extra_input.text().strip()
        if extra:
            cmd += extra.split()

        cmd.append(self._url)
        return cmd

    def _run(self):
        if not self._url or self._runner.is_running():
            return
        cmd = self._build_cmd()
        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._audio_btn.setEnabled(False)
        self._runner.run(cmd)

    def _run_audio(self):
        if not self._url or self._runner.is_running():
            return
        cmd = self._build_cmd(audio_only=True)
        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._audio_btn.setEnabled(False)
        self._runner.run(cmd)

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._audio_btn.setEnabled(True)
        self._progress.append_log(msg)
        if ok:
            self._open_folder_btn.setVisible(True)

    def _open_folder(self):
        subprocess.Popen(["xdg-open", self._out_dir])
