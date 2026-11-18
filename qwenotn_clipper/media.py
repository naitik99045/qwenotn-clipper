from __future__ import annotations

import json
from pathlib import Path

from .utils import format_time, require_binary, run


def probe_duration(path: Path) -> float:
    ffprobe = require_binary("ffprobe", "QWENOTN_FFPROBE")
    result = run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(result.stdout.strip())


def _yt_args(cookies: str | None = None, cookies_from_browser: str | None = None, extractor_args: str | None = None) -> list[str]:
    args: list[str] = []
    if cookies:
        args += ["--cookies", cookies]
    if cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    if extractor_args:
        args += ["--extractor-args", extractor_args]
    return args


def inspect_source(source: str, *, cookies: str | None = None, cookies_from_browser: str | None = None, extractor_args: str | None = None) -> dict:
    if Path(source).exists():
        return {"source": source, "source_status": "local_file", "is_live": False, "live_status": "not_live", "duration": None}
    ytdlp = require_binary("yt-dlp", "QWENOTN_YTDLP")
    result = run([ytdlp, "--dump-single-json", "--skip-download", "--no-playlist", "--no-warnings", *_yt_args(cookies, cookies_from_browser, extractor_args), source], check=False)
    if result.returncode:
        err = result.stderr.lower()
        if "sign in" in err or "private" in err or "authentication" in err:
            status = "authentication_failure"
        elif "bot" in err or "captcha" in err or "verify" in err:
            status = "bot_verification_failure"
        elif "private" in err:
            status = "private_video"
        elif "not available" in err or "deleted" in err:
            status = "deleted_or_unavailable"
        else:
            status = "inspection_failed"
        hint = " Retry with --cookies-from-browser chrome or --cookies FILE if this is your permitted video." if status in {"authentication_failure", "bot_verification_failure"} else ""
        raise RuntimeError(f"Source inspection failed ({status}).{hint}\n{result.stderr[-1200:]}")
    try:
        data = json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError("yt-dlp returned invalid metadata") from exc
    live_status = data.get("live_status") or ("is_live" if data.get("is_live") else "not_live")
    if live_status == "is_upcoming":
        status = "upcoming_livestream"
    elif live_status == "is_live":
        status = "active_livestream"
    elif data.get("was_live") or data.get("release_timestamp"):
        status = "completed_vod"
    else:
        status = "completed_vod"
    return {"source": source, "title": data.get("title"), "source_status": status, "is_live": status == "active_livestream", "live_status": live_status, "duration": data.get("duration"), "webpage_url": data.get("webpage_url", source)}


def download(source: str, workdir: Path, *, allow_live: bool = False, cookies: str | None = None, cookies_from_browser: str | None = None, extractor_args: str | None = None) -> tuple[Path, Path | None]:
    if Path(source).exists():
        media = Path(source).resolve()
        sidecar = media.with_suffix(".srt")
        return media, sidecar if sidecar.exists() else None
    ytdlp = require_binary("yt-dlp", "QWENOTN_YTDLP")
    metadata = inspect_source(source, cookies=cookies, cookies_from_browser=cookies_from_browser, extractor_args=extractor_args)
    if metadata.get("is_live") and not allow_live:
        raise RuntimeError("Active livestream detected. Full-stream downloading is disabled. Use the completed VOD or an explicit bounded live-window mode.")
    workdir.mkdir(parents=True, exist_ok=True)
    template = str(workdir / "source.%(ext)s")
    cmd = [ytdlp, "--no-playlist", "--continue", "--part", "--retries", "5", "--fragment-retries", "5", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4", "-o", template, *_yt_args(cookies, cookies_from_browser, extractor_args), source]
    result = run(cmd, check=False)
    if result.returncode:
        raise RuntimeError("yt-dlp could not download the permitted source.\n" + result.stderr[-2000:])
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


def render_clip(media: Path, out: Path, start: float, end: float, subtitle: Path | None = None, style: str = "clean", crop: str = "smart", normalize_audio: bool = False, music: Path | None = None, music_volume: float = 0.08, duck_source_audio: bool = False, replay: float = 0.0) -> None:
    ffmpeg = require_binary("ffmpeg", "QWENOTN_FFMPEG")
    duration = max(1.0, end - start)
    if crop == "center":
        vf = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    elif crop == "left":
        vf = "crop=ih*9/16:ih:0:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    elif crop == "right":
        vf = "crop=ih*9/16:ih:iw-ih*9/16:0,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    else:
        # Fit the complete gameplay frame by default; this preserves HUD/kill-feed evidence.
        vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black"
    if subtitle and subtitle.exists() and style != "none":
        escaped = str(subtitle).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        sizes = {"clean": 18, "gaming": 22, "bold": 26, "minimal": 16}
        fonts = f"FontName=DejaVu Sans,FontSize={sizes.get(style, 18)},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=110"
        vf += f",subtitles='{escaped}':force_style='{fonts}'"
    inputs = ["-ss", format_time(start), "-i", str(media)]
    filters = []
    audio = "[0:a]"
    if normalize_audio:
        filters.append("[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a0]")
        audio = "[a0]"
    if music and music.exists():
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        filters.append(f"[1:a]volume={max(0.0, min(1.0, music_volume))}[mus]")
        filters.append(f"{audio}volume={'0.75' if duck_source_audio else '1.0'}[src]")
        filters.append("[src][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]")
        audio = "[aout]"
    cmd = [ffmpeg, "-y", *inputs, "-t", f"{duration:.3f}", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
    if filters:
        cmd += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", audio]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    result = run(cmd, check=False)
    if result.returncode:
        raise RuntimeError("FFmpeg render failed.\n" + result.stderr[-2500:])
    if not out.exists() or out.stat().st_size < 1024:
        raise RuntimeError("FFmpeg reported success but the output clip is missing or empty")
