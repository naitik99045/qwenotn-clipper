from __future__ import annotations

from dataclasses import asdict, dataclass, field


EVENT_TYPES = {"headshot", "kill", "multi-kill", "elimination", "knock", "clutch", "objective", "loud-impact", "unknown-highlight"}


@dataclass
class Event:
    timestamp: float
    event_type: str = "unknown-highlight"
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    audio_score: float = 0.0
    visual_score: float = 0.0

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES:
            self.event_type = "unknown-highlight"
        self.timestamp = max(0.0, float(self.timestamp))
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def as_dict(self) -> dict:
        return asdict(self)


def event_window(event: Event, duration: float, pre_roll: float = 4.0, post_roll: float = 7.0) -> tuple[float, float]:
    return max(0.0, event.timestamp - max(0.0, pre_roll)), min(duration, event.timestamp + max(1.0, post_roll))
