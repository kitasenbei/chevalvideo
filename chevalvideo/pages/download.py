"""yt-dlp download page."""

import json
import subprocess

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from chevalvideo.runner import CommandRunner
from chevalvideo.widgets.progress import ProgressWidget


class DownloadPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._url = ""
        self._formats = []
        self._out_dir = ""
        self._runner = CommandRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading = QLabel("Download")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        # URL input
        url_row = QHBoxLayout()
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("Paste video URL here...")
        url_row.addWidget(self._url_input, 1)
        self._fetch_btn = QPushButton("Fetch Formats")
        self._fetch_btn.clicked.connect(self._fetch)
        url_row.addWidget(self._fetch_btn)
        layout.addLayout(url_row)

        # Output dir
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Save to:"))
        self._dir_label = QLabel("~/Downloads")
        self._out_dir = str(__import__("pathlib").Path.home() / "Downloads")
        dir_row.addWidget(self._dir_label, 1)
        dir_btn = QPushButton("Change")
        dir_btn.setFixedWidth(80)
        dir_btn.clicked.connect(self._pick_dir)
        dir_row.addWidget(dir_btn)
        layout.addLayout(dir_row)

        # Format table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["ID", "Ext", "Resolution", "Size", "Note"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self._table)

        self._go_btn = QPushButton("Download")
        self._go_btn.clicked.connect(self._run)
        self._go_btn.setEnabled(False)
        layout.addWidget(self._go_btn)

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

    def _fetch(self):
        url = self._url_input.text().strip()
        if not url:
            return
        self._url = url
        self._progress.append_log(f"Fetching formats for {url}...")

        try:
            result = subprocess.run(
                ["yt-dlp", "-j", "--no-download", url],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                self._progress.append_log(f"Error: {result.stderr.strip()}")
                return
            info = json.loads(result.stdout)
        except Exception as e:
            self._progress.append_log(f"Error: {e}")
            return

        self._formats = info.get("formats", [])
        self._table.setRowCount(len(self._formats))
        for i, f in enumerate(self._formats):
            self._table.setItem(i, 0, QTableWidgetItem(str(f.get("format_id", ""))))
            self._table.setItem(i, 1, QTableWidgetItem(f.get("ext", "")))
            res = f"{f.get('width', '?')}x{f.get('height', '?')}" if f.get("width") else "audio"
            self._table.setItem(i, 2, QTableWidgetItem(res))
            size = f.get("filesize") or f.get("filesize_approx")
            size_str = f"{size / 1048576:.1f} MB" if size else ""
            self._table.setItem(i, 3, QTableWidgetItem(size_str))
            note = f.get("format_note", "")
            self._table.setItem(i, 4, QTableWidgetItem(note))

        self._go_btn.setEnabled(True)
        self._progress.append_log(f"Found {len(self._formats)} formats")

    def _run(self):
        if not self._url or self._runner.is_running():
            return

        sel = self._table.selectedItems()
        fmt_id = None
        if sel:
            row = sel[0].row()
            fmt_id = self._formats[row].get("format_id")

        cmd = ["yt-dlp", "-o", f"{self._out_dir}/%(title)s.%(ext)s"]
        if fmt_id:
            cmd += ["-f", fmt_id]
        cmd.append(self._url)

        self._progress.reset()
        self._progress.set_running(True)
        self._go_btn.setEnabled(False)
        self._runner.run(cmd)

    def _on_done(self, ok, msg):
        self._progress.set_running(False)
        self._go_btn.setEnabled(True)
        self._progress.append_log(msg)
