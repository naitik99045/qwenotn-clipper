from __future__ import annotations

from pathlib import Path


def detect_visual_evidence(media: Path, timestamp: float, *, profile: dict | None = None) -> dict:
    """Sample a small neighborhood and return conservative motion evidence.

    OCR/template recognition is optional and profile-driven. When optional vision
    packages are absent, callers receive an explicit unavailable status.
    """
    try:
        import cv2
    except ImportError:
        return {"visual_detection": "unavailable", "visual_score": 0.0, "visual_evidence": []}
    cap = cv2.VideoCapture(str(media))
    if not cap.isOpened():
        return {"visual_detection": "unavailable", "visual_score": 0.0, "visual_evidence": []}
    frames = []
    for offset in (-1.0, 0.0, 1.0):
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp + offset) * 1000)
        ok, frame = cap.read()
        if ok:
            frames.append(cv2.resize(frame, (320, 180)))
    cap.release()
    if len(frames) < 2:
        return {"visual_detection": "available", "visual_score": 0.0, "visual_evidence": []}
    diffs = [float(cv2.absdiff(frames[i - 1], frames[i]).mean()) / 255.0 for i in range(1, len(frames))]
    score = min(1.0, sum(diffs) / max(1, len(diffs)) * 3.0)
    evidence = ["visible frame change"] if score >= 0.2 else []
    return {"visual_detection": "available", "visual_score": round(score, 3), "visual_evidence": evidence}
