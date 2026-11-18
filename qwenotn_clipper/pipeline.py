from __future__ import annotations

from pathlib import Path
from typing import Callable

from .highlights import Candidate, candidates_json, parse_srt, select_candidates
from .media import download, probe_duration, render_clip, transcribe
from .utils import write_json


def process(source: str, output_dir: str = "output", count: int = 5, duration: float = 45.0, whisper_model: str = "small", progress: Callable[[str], None] | None = None) -> dict:
    log = progress or (lambda _: None)
    out = Path(output_dir).resolve(); work = out / ".work"; out.mkdir(parents=True, exist_ok=True)
    log("Preparing source")
    media, subtitle = download(source, work)
    total = probe_duration(media)
    if subtitle is None:
        log("Generating local captions when faster-whisper is installed")
        subtitle = transcribe(media, work / "source.srt", whisper_model)
    segments = parse_srt(subtitle) if subtitle else []
    if segments:
        candidates = select_candidates(segments, total, count=count, target=duration)
    else:
        # No transcript is a valid degraded mode: make evenly spaced review clips.
        step = max(duration, 15.0)
        starts = [min(max(0.0, total - step), i * step) for i in range(max(1, min(count, int(total // step) or 1)))]
        candidates = [Candidate(s, min(total, s + step), 0.0, "no transcript; evenly spaced fallback", "") for s in starts]
    manifest = {"source": source, "media": str(media), "duration": total, "captions": str(subtitle) if subtitle else None, "candidates": candidates_json(candidates), "clips": []}
    write_json(out / "manifest.json", manifest)
    for index, candidate in enumerate(candidates, 1):
        path = out / f"clip_{index:02d}.mp4"
        log(f"Rendering clip {index}/{len(candidates)}")
        render_clip(media, path, candidate.start, candidate.end, subtitle)
        clip_info = {"index": index, "path": str(path), "start": candidate.start, "end": candidate.end, "score": candidate.score, "reason": candidate.reason, "captioned": bool(subtitle)}
        manifest["clips"].append(clip_info)
        write_json(out / f"clip_{index:02d}.json", clip_info)
    write_json(out / "manifest.json", manifest)
    return manifest
