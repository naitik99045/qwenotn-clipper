from __future__ import annotations

import array
import math
import subprocess
from pathlib import Path

from .utils import require_binary, run


def detect_audio_spikes(media: Path, *, max_events: int = 80) -> list[dict]:
    """Return supporting audio evidence; audio alone is never treated as proof."""
    ffmpeg = require_binary("ffmpeg", "QWENOTN_FFMPEG")
    result = subprocess.run([ffmpeg, "-v", "error", "-i", str(media), "-vn", "-ac", "1", "-ar", "2000", "-f", "s16le", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode or not result.stdout:
        return []
    samples = array.array("h")
    samples.frombytes(result.stdout.encode("latin1") if isinstance(result.stdout, str) else result.stdout)
    window = 1000
    rms: list[float] = []
    for i in range(0, len(samples), window):
        chunk = samples[i:i + window]
        if not chunk:
            continue
        rms.append(math.sqrt(sum(x * x for x in chunk) / len(chunk)) / 32768.0)
    if len(rms) < 4:
        return []
    baseline = sorted(rms)[max(0, int(len(rms) * 0.5))] or 0.001
    peaks = []
    for i, value in enumerate(rms):
        ratio = min(1.0, value / max(baseline * 2.0, 0.01))
        if ratio >= 0.55:
            peaks.append({"timestamp": round(i * 0.5, 3), "audio_score": round(ratio, 3), "audio_evidence": ["short audio energy spike"]})
    peaks.sort(key=lambda x: x["audio_score"], reverse=True)
    chosen: list[dict] = []
    for item in peaks:
        if all(abs(item["timestamp"] - old["timestamp"]) >= 5 for old in chosen):
            chosen.append(item)
        if len(chosen) >= max_events:
            break
    return sorted(chosen, key=lambda x: x["timestamp"])
