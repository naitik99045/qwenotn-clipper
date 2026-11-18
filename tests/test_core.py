from pathlib import Path

from qwenotn_clipper.highlights import parse_srt, select_candidates
from qwenotn_clipper.utils import format_time, parse_time


def test_time_roundtrip():
    assert parse_time("01:02:03") == 3723
    assert parse_time("02:30") == 150
    assert format_time(3723.4) == "01:02:03"


def test_srt_and_highlights(tmp_path: Path):
    srt = tmp_path / "a.srt"
    srt.write_text("1\n00:00:10,000 --> 00:00:15,000\nThe secret is simple.\n\n2\n00:01:00,000 --> 00:01:08,000\nThis is a normal sentence with enough context to make a useful clip.\n")
    segments = parse_srt(srt)
    assert len(segments) == 2
    candidates = select_candidates(segments, 120, count=2, target=30)
    assert len(candidates) == 2
    assert candidates[0].start < candidates[1].start
    assert any("strong opening" in c.reason for c in candidates)
