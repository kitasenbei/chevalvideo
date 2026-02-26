# chevalvideo

PyQt6 desktop video power tool wrapping **ffmpeg** and **yt-dlp**. Bloomberg Terminal aesthetic. All operations shell out to the real CLI tools — no hardcoded ffmpeg logic.

## Requirements

- Python 3.10+
- PyQt6
- ffmpeg / ffprobe on PATH
- yt-dlp on PATH (for Download page)

## Install

```bash
cd chevalvideo
python -m venv .venv
source .venv/bin/activate
pip install PyQt6
```

## Run

```bash
source .venv/bin/activate
python -m chevalvideo
```

## Pages

| Page | What it does |
|------|-------------|
| **Convert** | Format/codec conversion — mp4/mkv/webm/avi, H.264/H.265/AV1/VP9, CRF slider |
| **Compress** | Quality presets (CRF 18/23/28) or target file size, codec selection |
| **Extract Audio** | Rip audio track — mp3/flac/wav/aac with bitrate control |
| **Trim** | Cut segments with start/end timestamps, stream copy or re-encode |
| **Resize** | Resolution scaling — 4K/1080p/720p/480p presets or custom scale |
| **Speed** | Playback speed — presets 0.25x–4x, pitch adjust, frame interpolation |
| **Rotate/Crop** | Rotation (90/180), flip (h/v), crop presets (16:9/4:3/1:1/9:16), auto black bar detection |
| **Merge** | Concatenate multiple files — concat demuxer (fast) or re-encode, crossfade transitions |
| **Watermark** | Image or text overlay — position, scale, opacity, drawtext with font/color |
| **Subtitles** | Burn in, embed as soft track, or extract subtitle streams |
| **Audio Mix** | Replace/add/mix audio tracks, remove audio, normalize (loudnorm), volume adjust |
| **Download** | yt-dlp frontend — format table, playlist support, subs/thumbnail/metadata embed, SponsorBlock, aria2c, cookies, rate limit, concurrent fragments |
| **Strip Meta** | Remove all metadata with stream copy |
| **Thumbnail** | Extract a single frame at any timestamp as PNG/JPG |
| **GIF** | Video to GIF with palette-based pipeline, fps/width/time range control |
| **Batch** | Process multiple files with the same operation — convert, compress, extract audio, resize, strip meta, normalize, thumbnails |

## Architecture

```
chevalvideo/
├── __main__.py          # Entry point
├── app.py               # Main window + sidebar nav
├── runner.py            # QProcess wrapper — runs ffmpeg/yt-dlp, parses progress
├── probe.py             # ffprobe wrapper — returns structured info
├── style.py             # Bloomberg Terminal dark theme
├── widgets/
│   ├── file_picker.py   # Drag-drop + browse file input
│   ├── progress.py      # Progress bar + log + cancel
│   ├── media_info.py    # Probe info display grid
│   └── option_grid.py   # Clickable card selector
└── pages/
    └── ...              # 16 page modules
```

Every page follows the same pattern: file input → auto-probe → options → go → progress bar + live log showing the actual command being run.
