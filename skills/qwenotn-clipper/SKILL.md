---
name: qwenotn-clipper
description: Create and review clean vertical clips from a YouTube URL or local recording using qwenotn-clipper. Use when the user asks to find highlights, add real captions, render 9:16 clips, or inspect clip manifests. Do not publish automatically.
---

# qwenotn-clipper

Use the local qwenotn-clipper CLI as the media renderer. Keep the output source-derived: do not add invented dialogue, AI avatars, fake reactions, meme overlays, synthetic audio, or generated hook cards. Never use Chrome or an agent to manually watch an entire multi-hour stream.

## First-time setup

From the cloned plugin/repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[all]'
qwenotn-clipper --help
```

The host also needs `ffmpeg` and `yt-dlp`. If the command is unavailable, report the exact installation error rather than pretending a clip was created.

## Create clips from a completed VOD

```bash
qwenotn-clipper clip INPUT \
  --count 5 \
  --duration 45 \
  --focus "best genuine moments" \
  --output output/agent-job \
  --json > output/agent-job/result.json
```

`INPUT` may be a YouTube URL or a local video path. Read `output/agent-job/manifest.json` and the `clip_*.json` files. Each clip has a path, timestamps, score, reason, and caption status.

For a large finite VOD, analyze first and render second:

```bash
qwenotn-clipper analyze INPUT --count 30 --duration 45 --focus "funny GTA moments" --output output/agent-job --json
```

The tool rejects an active livestream before downloading it. Do not override this safety behavior. Wait for the replay/VOD or use a dedicated bounded live-window implementation.

## Review policy

After rendering, list the generated MP4 paths and summarize the strongest candidates. Ask for approval before any upload or posting. The qwenotn-clipper repository does not provide automatic publishing.

## Caption policy

Use real source subtitles or local Whisper transcription only. If `captioned` is false, tell the user that the clip has no captions and do not fabricate them. Prefer a clear error or a no-transcript fallback over adding synthetic text.

## GUI

For a human review workflow, run:

```bash
qwenotn-clipper gui --host 127.0.0.1 --port 7860
```

Then open `http://127.0.0.1:7860`.
