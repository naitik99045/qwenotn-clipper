from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .audio import detect_audio_spikes
from .events import event_window
from .highlights import Candidate, candidates_json, parse_srt, select_candidates
from .media import download, inspect_source, probe_duration, render_clip, transcribe
from .utils import write_json
from .vision import detect_visual_evidence


def _profile(game: str) -> dict:
    path = Path(__file__).parent / "profiles" / f"{game}.json"
    if not path.exists():
        path = Path(__file__).parent / "profiles" / "generic.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _candidates(total: float, subtitle: Path | None, count: int, duration: float | str, focus: str, event: str, pre_roll: float, post_roll: float) -> list[dict]:
    target = 45.0 if duration == "auto" else float(duration)
    segments = parse_srt(subtitle) if subtitle else []
    if segments:
        selected = select_candidates(segments, total, count=count, target=target, focus=focus)
    else:
        step = max(target, 15.0)
        starts = [min(max(0.0, total - step), i * step) for i in range(max(1, min(count, int(total // step) or 1)))]
        selected = [Candidate(s, min(total, s + step), 0.0, "no transcript; evenly spaced review fallback", "") for s in starts]
    output = []
    for item in selected:
        start = max(0.0, item.start - pre_roll)
        end = min(total, item.end + post_roll if duration == "auto" else item.end)
        output.append({**candidates_json([item])[0], "start": start, "end": end, "event_type": event or "unknown-highlight", "score_breakdown": {"transcript_score": round(item.score, 3), "focus_match_score": 0.1 if focus and focus.lower() in item.text.lower() else 0.0, "visual_event_score": 0.0, "audio_event_score": 0.0, "motion_change_score": 0.0, "context_score": 0.0}, "evidence": []})
    return output


def analyze(source: str, output_dir: str = "output", count: int = 10, duration: float | str = 45.0, whisper_model: str = "small", focus: str = "", progress: Callable[[str], None] | None = None, *, game: str = "generic", event: str = "", pre_roll: float = 4.0, post_roll: float = 7.0, cookies: str | None = None, cookies_from_browser: str | None = None, extractor_args: str | None = None, enable_vision: bool = False, enable_audio: bool = True, **_render_options) -> dict:
    log = progress or (lambda _: None)
    out = Path(output_dir).resolve(); work = out / ".work"; out.mkdir(parents=True, exist_ok=True)
    log("Checking whether the source is a completed VOD or an active livestream")
    source_meta = inspect_source(source, cookies=cookies, cookies_from_browser=cookies_from_browser, extractor_args=extractor_args)
    if source_meta.get("is_live"):
        raise RuntimeError("Active livestream detected. qwenotn-clipper will not download or watch an unlimited live stream. Use the completed VOD or an explicit bounded live-window mode.")
    media, subtitle = download(source, work, cookies=cookies, cookies_from_browser=cookies_from_browser, extractor_args=extractor_args)
    total = probe_duration(media)
    if subtitle is None:
        log("Generating local captions when faster-whisper is installed")
        subtitle = transcribe(media, work / "source.srt", whisper_model)
    candidates = _candidates(total, subtitle, count, duration, focus, event, pre_roll, post_roll)
    audio_events = detect_audio_spikes(media) if enable_audio else []
    profile = _profile(game)
    visual_status = "unavailable"
    for item in candidates:
        center = (item["start"] + item["end"]) / 2
        nearby = [e for e in audio_events if abs(e["timestamp"] - center) <= max(8.0, post_roll)]
        if nearby:
            best = max(nearby, key=lambda e: e["audio_score"])
            item["score_breakdown"]["audio_event_score"] = best["audio_score"]
            item["evidence"].extend(best["audio_evidence"])
        if enable_vision:
            visual = detect_visual_evidence(media, center, profile=profile)
            visual_status = visual["visual_detection"]
            item["score_breakdown"]["visual_event_score"] = visual["visual_score"]
            item["evidence"].extend(visual["visual_evidence"])
        weights = profile.get("weights", {})
        b = item["score_breakdown"]
        item["score"] = round(min(1.0, b["transcript_score"] * weights.get("transcript", 0.2) + b["focus_match_score"] * weights.get("focus", 0.1) + b["visual_event_score"] * weights.get("visual", 0.35) + b["audio_event_score"] * weights.get("audio", 0.2) + b["motion_change_score"] * weights.get("motion", 0.05) + b["context_score"] * weights.get("context", 0.1)), 3)
        item["reason"] = "; ".join(item["evidence"]) or item["reason"]
        item["confidence_note"] = "Evidence is supporting signal, not guaranteed event recognition; review before publishing."
    candidates.sort(key=lambda x: x["score"], reverse=True)
    manifest = {"ok": True, "source": source, "title": source_meta.get("title"), "media": str(media), "duration": total, "captions": str(subtitle) if subtitle else None, "focus": focus, "game": game, "requested_event": event or None, "source_status": source_meta.get("source_status", "completed_vod"), "detector_version": "0.3.0", "visual_detection": visual_status, "audio_detection": "available" if enable_audio else "disabled", "score_breakdown": {"weights": profile.get("weights", {})}, "candidates": candidates[:count], "clips": [], "warnings": ["No visual event detector is enabled." if not enable_vision else "Visual motion evidence does not prove a named game event."]}
    write_json(out / "manifest.json", manifest)
    return manifest


def process(source: str, output_dir: str = "output", count: int = 5, duration: float | str = 45.0, whisper_model: str = "small", focus: str = "", progress: Callable[[str], None] | None = None, **kwargs) -> dict:
    log = progress or (lambda _: None)
    manifest = analyze(source, output_dir, count, duration, whisper_model, focus, log, **kwargs)
    out = Path(output_dir).resolve(); media = Path(manifest["media"]); subtitle = Path(manifest["captions"]) if manifest["captions"] else None
    for index, candidate in enumerate(manifest["candidates"], 1):
        path = out / f"clip_{index:02d}.mp4"
        log(f"Rendering clip {index}/{len(manifest['candidates'])}")
        render_clip(media, path, candidate["start"], candidate["end"], subtitle, style=kwargs.get("caption_style", "clean"), crop=kwargs.get("crop", "smart"), normalize_audio=kwargs.get("normalize_audio", False), music=Path(kwargs["music"]) if kwargs.get("music") else None, music_volume=kwargs.get("music_volume", 0.08), duck_source_audio=kwargs.get("duck_source_audio", False))
        clip_info = {"index": index, "path": str(path), "start": candidate["start"], "end": candidate["end"], "score": candidate["score"], "reason": candidate["reason"], "event_type": candidate.get("event_type"), "evidence": candidate.get("evidence", []), "score_breakdown": candidate.get("score_breakdown", {}), "captioned": bool(subtitle), "render_settings": {"crop": kwargs.get("crop", "smart"), "caption_style": kwargs.get("caption_style", "clean"), "normalize_audio": kwargs.get("normalize_audio", False)}}
        manifest["clips"].append(clip_info)
        write_json(out / f"clip_{index:02d}.json", clip_info)
    write_json(out / "manifest.json", manifest)
    return manifest
