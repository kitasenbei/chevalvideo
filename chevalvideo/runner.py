"""QProcess wrapper for running ffmpeg/yt-dlp with progress parsing."""

import re
import signal

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class CommandRunner(QObject):
    """Runs a CLI command via QProcess, parses progress, emits signals."""

    progress = pyqtSignal(float)       # 0.0 – 100.0
    output = pyqtSignal(str)           # raw line of output
    finished = pyqtSignal(bool, str)   # (success, message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None
        self._duration = 0.0  # total duration in seconds (for ffmpeg progress)
        self._mode = "ffmpeg"

    def run(self, cmd: list[str], *, duration: float = 0.0):
        """Start a command. `duration` is used for ffmpeg progress calculation."""
        if self._proc is not None:
            return

        self._duration = duration
        self._mode = "yt-dlp" if "yt-dlp" in cmd[0] else "ffmpeg"

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_output)
        self._proc.finished.connect(self._on_finished)

        self.output.emit(f"$ {' '.join(cmd)}")
        self._proc.start(cmd[0], cmd[1:])

    def cancel(self):
        """Send SIGTERM to the running process."""
        if self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning:
            pid = self._proc.processId()
            if pid:
                try:
                    import os
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning

    def _on_output(self):
        data = self._proc.readAllStandardOutput().data().decode(errors="replace")
        for line in data.splitlines():
            line = line.strip()
            if not line:
                continue
            self.output.emit(line)
            self._parse_progress(line)

    def _parse_progress(self, line: str):
        if self._mode == "yt-dlp":
            m = re.search(r"\[download\]\s+([\d.]+)%", line)
            if m:
                self.progress.emit(float(m.group(1)))
        else:
            # ffmpeg progress: look for out_time_us or out_time
            m = re.search(r"out_time_us=(\d+)", line)
            if m and self._duration > 0:
                current = int(m.group(1)) / 1_000_000
                pct = min(current / self._duration * 100, 100.0)
                self.progress.emit(pct)
                return
            m = re.search(r"out_time=(\d+):(\d+):([\d.]+)", line)
            if m and self._duration > 0:
                secs = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
                pct = min(secs / self._duration * 100, 100.0)
                self.progress.emit(pct)

    def _on_finished(self, exit_code, _exit_status):
        ok = exit_code == 0
        msg = "Done" if ok else f"Exited with code {exit_code}"
        self._proc = None
        if ok:
            self.progress.emit(100.0)
        self.finished.emit(ok, msg)
