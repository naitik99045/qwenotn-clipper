from __future__ import annotations

import json
import re
import shutil
import subprocess
import os
import sys
from pathlib import Path
from typing import Any


def find_executable(name: str, env_var: str | None = None) -> str:
    """Find a tool without assuming the shell PATH is correctly configured."""
    candidates: list[str] = []
    if env_var and os.environ.get(env_var):
        candidates.append(os.environ[env_var])
    exe_dir = Path(sys.executable).resolve().parent
    candidates.extend([str(exe_dir / name), str(exe_dir / f"{name}.exe"), str(exe_dir / "Scripts" / name), str(exe_dir / "Scripts" / f"{name}.exe")])
    which = shutil.which(name)
    if which:
        candidates.append(which)
    candidates.extend([str(Path.home() / ".local" / "bin" / name), str(Path.home() / "AppData" / "Roaming" / "Python" / "Python311" / "Scripts" / f"{name}.exe")])
    for candidate in candidates:
        p = Path(candidate)
        if p.exists() and p.is_file():
            return str(p)
    install = {"yt-dlp": "python -m pip install -U yt-dlp", "ffmpeg": "install FFmpeg and add it to PATH", "ffprobe": "install FFmpeg (ffprobe is included)"}.get(name, f"install {name}")
    checked = ", ".join(candidates) or "no candidate paths"
    raise RuntimeError(f"Required program not found: {name}. Install with: {install}. Checked: {checked}")


def require_binary(name: str, env_var: str | None = None) -> str:
    return find_executable(name, env_var)


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def parse_time(value: str | float | int) -> float:
    if isinstance(value, (float, int)):
        return float(value)
    parts = value.strip().split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Invalid time: {value}")


def format_time(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def safe_name(value: str, fallback: str = "clip") -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._-")
    return (value[:80] or fallback)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
