from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .utils import parse_time

@dataclass
class Segment:
    start: float
    end: float
    text: str

@dataclass
class Candidate:
    start: float
    end: float
    score: float
    reason: str
    text: str

_HOOKS = re.compile(r"\b(why|how|never|always|secret|mistake|truth|actually|because|learned|realize|best|worst|first|only|impossible|shocking|important)\b", re.I)


def parse_srt(path: Path) -> list[Segment]:
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n", raw.strip())
    result: list[Segment] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        timing = next((line for line in lines if "-->" in line), "")
        if not timing:
            continue
        left, right = [x.strip().split(",")[0] for x in timing.split("-->", 1)]
        try:
            start = parse_time(left.replace(".", ":"))
            end = parse_time(right.replace(".", ":"))
        except ValueError:
            continue
        text = " ".join(x.strip() for x in lines[lines.index(timing) + 1:] if x.strip())
        if text and end > start:
            result.append(Segment(start, end, re.sub(r"<[^>]+>", "", text)))
    return result


def select_candidates(segments: list[Segment], duration: float, count: int = 5, target: float = 45.0) -> list[Candidate]:
    if not segments:
        return []
    window = max(15.0, min(90.0, target))
    raw: list[Candidate] = []
    for seg in segments:
        center = (seg.start + seg.end) / 2
        start = max(0.0, center - window / 2)
        end = min(duration, start + window)
        text = seg.text.strip()
        words = len(text.split())
        score = min(1.0, 0.25 + min(words, 35) / 100)
        reasons = ["complete spoken thought"]
        if _HOOKS.search(text):
            score += 0.25
            reasons.append("strong opening language")
        if "?" in text:
            score += 0.08
            reasons.append("question or tension")
        if words >= 18:
            score += 0.10
            reasons.append("substantial context")
        raw.append(Candidate(start, end, round(min(score, 1.0), 3), ", ".join(reasons), text))
    raw.sort(key=lambda x: x.score, reverse=True)
    chosen: list[Candidate] = []
    for item in raw:
        if all(item.end <= old.start + 5 or item.start >= old.end - 5 for old in chosen):
            chosen.append(item)
        if len(chosen) >= count:
            break
    return sorted(chosen, key=lambda x: x.start)


def candidates_json(candidates: list[Candidate]) -> list[dict]:
    return [asdict(c) for c in candidates]
