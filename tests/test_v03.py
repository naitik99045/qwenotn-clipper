from pathlib import Path

import pytest

from qwenotn_clipper.events import Event, event_window
from qwenotn_clipper.highlights import Segment, select_candidates
from qwenotn_clipper.pipeline import analyze
from qwenotn_clipper.utils import find_executable


def test_find_executable_reports_or_finds_python():
    assert Path(find_executable("python", "QWENOTN_TEST_MISSING")).exists()


def test_event_window_is_bounded():
    assert event_window(Event(2, "headshot"), 20, 4, 7) == (0.0, 9.0)
    assert event_window(Event(19, "kill"), 20, 4, 7) == (15.0, 20.0)


def test_focus_matching_changes_reason():
    items = select_candidates([Segment(10, 15, "funny GTA chase and crash")], 60, count=1, target=30, focus="GTA chase")
    assert "matches focus" in items[0].reason


def test_active_stream_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("qwenotn_clipper.pipeline.inspect_source", lambda *a, **k: {"is_live": True, "source_status": "active_livestream"})
    with pytest.raises(RuntimeError, match="Active livestream"):
        analyze("https://example.invalid/live", str(tmp_path))
