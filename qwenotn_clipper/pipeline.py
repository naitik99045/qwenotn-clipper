from __future__ import annotations

from pathlib import Path
from typing import Callable

from .highlights import Candidate, candidates_json, parse_srt, select_candidates
from .media import download, inspect_source, probe_duration, render_clip, transcribe
from .utils import write_json


def _candidates(total: float, subtitle: Path | None, count: int, duration: float, focus: str) -> list[Candidate]:
    segments = parse_srt(subtitle) if subtitle else []
    if segments:
        return select_candidates(segments, total, count=count, target=duration, focus=focus)
    # This is deliberately explicit and low-confidence, so agents do not mistake
    # evenly spaced review clips for detected highlights.
    step = max(duration, 15.0)
    starts = [min(max(0.0, total - step), i * step) for i in range(max(1, min(count, int(total // step) or 1)))]
    return [Candidate(s, min(total, s + step), 0.0, "no transcript; evenly spaced review fallback", "") for s in starts]


def analyze(source: str, output_dir: str = "output", count: int = 10, duration: float = 45.0, whisper_model: str = "small", focus: str = "", progress: Callable[[str], None] | None = None) -> dict:
    log = progress or (lambda _: None)
    out = Path(output_dir).resolve(); work = out / ".work"; out.mkdir(parents=True, exist_ok=True)
    log("Checking whether the source is a completed VOD or an active livestream")
    source_meta = inspect_source(source)
    if source_meta.get("is_live"):
        raise RuntimeError("Active livestream detected. qwenotn-clipper will not download or watch an unlimited live stream. Use a completed VOD or implement a bounded live-window workflow.")
    log("Preparing finite source")
    media, subtitle = download(source, work)
    total = probe_duration(media)
    if subtitle is None:
        log("Generating local captions when faster-whisper is installed")
        subtitle = transcribe(media, work / "source.srt", whisper_model)
    candidates = _candidates(total, subtitle, count, duration, focus)
    manifest = {"ok": True, "source": source, "title": source_meta.get("title"), "media": str(media), "duration": total, "captions": str(subtitle) if subtitle else None, "focus": focus, "confidence_note": "Transcript ranking is not visual game-event verification; review candidates before publishing.", "candidates": candidates_json(candidates), "clips": []}
    write_json(out / "manifest.json", manifest)
    return manifest


def process(source: str, output_dir: str = "output", count: int = 5, duration: float = 45.0, whisper_model: str = "small", focus: str = "", progress: Callable[[str], None] | None = None) -> dict:
    log = progress or (lambda _: None)
    manifest = analyze(source, output_dir, count, duration, whisper_model, focus, log)
    out = Path(output_dir).resolve(); media = Path(manifest["media"]); subtitle = Path(manifest["captions"]) if manifest["captions"] else None
    candidates = [Candidate(**{k: item[k] for k in ("start", "end", "score", "reason", "text")}) for item in manifest["candidates"]]
    for index, candidate in enumerate(candidates, 1):
        path = out / f"clip_{index:02d}.mp4"
        log(f"Rendering clip {index}/{len(candidates)}")
        render_clip(media, path, candidate.start, candidate.end, subtitle)
        clip_info = {"index": index, "path": str(path), "start": candidate.start, "end": candidate.end, "score": candidate.score, "reason": candidate.reason, "captioned": bool(subtitle)}
        manifest["clips"].append(clip_info)
        write_json(out / f"clip_{index:02d}.json", clip_info)
    write_json(out / "manifest.json", manifest)
    return manifest
