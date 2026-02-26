"""Shells out to ffprobe, returns structured dict."""

import json
import subprocess


def probe(path: str) -> dict:
    """Run ffprobe on a file and return parsed JSON output."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def summarize(info: dict) -> dict:
    """Extract a human-friendly summary from probe output."""
    fmt = info.get("format", {})
    video = audio = None
    for s in info.get("streams", []):
        if s["codec_type"] == "video" and video is None:
            video = s
        elif s["codec_type"] == "audio" and audio is None:
            audio = s

    summary = {
        "filename": fmt.get("filename", ""),
        "format": fmt.get("format_long_name", fmt.get("format_name", "")),
        "duration": _fmt_duration(float(fmt.get("duration", 0))),
        "size": _fmt_size(int(fmt.get("size", 0))),
        "bitrate": f"{int(fmt.get('bit_rate', 0)) // 1000} kbps" if fmt.get("bit_rate") else "",
    }
    if video:
        summary["video_codec"] = video.get("codec_name", "")
        summary["resolution"] = f"{video.get('width', '?')}x{video.get('height', '?')}"
        summary["fps"] = _parse_fps(video.get("r_frame_rate", ""))
    if audio:
        summary["audio_codec"] = audio.get("codec_name", "")
        summary["sample_rate"] = f"{audio.get('sample_rate', '')} Hz"
        summary["channels"] = audio.get("channels", "")
    return summary


def get_duration_secs(info: dict) -> float:
    """Return duration in seconds from probe info."""
    return float(info.get("format", {}).get("duration", 0))


def _fmt_duration(secs: float) -> str:
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def _parse_fps(rate_str: str) -> str:
    if "/" in rate_str:
        num, den = rate_str.split("/")
        try:
            return f"{int(num) / int(den):.2f}"
        except (ValueError, ZeroDivisionError):
            return rate_str
    return rate_str
