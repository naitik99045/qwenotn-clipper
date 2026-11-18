from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .utils import format_time, require_binary, run, safe_name


def probe_duration(path: Path) -> float:
    require_binary("ffprobe")
    result = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(result.stdout.strip())


def download(source: str, workdir: Path) -> tuple[Path, Path | None]:
    if Path(source).exists():
        media = Path(source).resolve()
        sidecar = media.with_suffix(".srt")
        return media, sidecar if sidecar.exists() else None
    require_binary("yt-dlp")
    workdir.mkdir(parents=True, exist_ok=True)
    template = str(workdir / "source.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "--retries", "3", "--fragment-retries", "3", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4", "-o", template, source]
    result = run(cmd, check=False)
    if result.returncode:
        raise RuntimeError("yt-dlp could not download the source.\n" + result.stderr[-2000:])
    media = next((p for p in workdir.glob("source.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}), None)
    if not media:
        raise RuntimeError("yt-dlp finished but no media file was found")
    subtitle = next(iter(workdir.glob("source*.srt")), None)
    return media, subtitle


def transcribe(media: Path, output: Path, model: str = "small") -> Path | None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    try:
        model_obj = WhisperModel(model, device="auto", compute_type="int8")
        segments, _ = model_obj.transcribe(str(media), vad_filter=True, word_timestamps=False)
        lines = []
        for i, seg in enumerate(segments, 1):
            def ts(sec: float) -> str:
                ms = int(sec * 1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            lines += [str(i), f"{ts(seg.start)} --> {ts(seg.end)}", seg.text.strip(), ""]
        output.write_text("\n".join(lines), encoding="utf-8")
        return output
    except Exception:
        return None


def render_clip(media: Path, out: Path, start: float, end: float, subtitle: Path | None = None, style: str = "clean") -> None:
    require_binary("ffmpeg")
    duration = max(1.0, end - start)
    # Center crop to 9:16, scale to 1080x1920, and avoid hook cards or synthetic overlays.
    vf = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    if subtitle and subtitle.exists():
        escaped = str(subtitle).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        fonts = "FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=110"
        vf += f",subtitles='{escaped}':force_style='{fonts}'"
    cmd = ["ffmpeg", "-y", "-ss", format_time(start), "-i", str(media), "-t", f"{duration:.3f}", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    result = run(cmd, check=False)
    if result.returncode:
        raise RuntimeError("FFmpeg render failed.\n" + result.stderr[-2500:])
    if not out.exists() or out.stat().st_size < 1024:
        raise RuntimeError("FFmpeg reported success but the output clip is missing or empty")
