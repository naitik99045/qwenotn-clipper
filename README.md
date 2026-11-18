# qwenotn-clipper

A local-first, open-source clipper for YouTube VODs and local recordings. It is designed to work from a human browser GUI, a normal terminal, or an AI agent that can run commands and read JSON.

The project intentionally avoids AI-slop editing: no invented dialogue, fake reaction shots, AI avatars, noisy meme overlays, or automatic hook cards. It produces clean vertical clips with real source audio/video, optional real captions, restrained formatting, and a manifest explaining every decision.

## What it does

- Downloads a single YouTube source with `yt-dlp`, or accepts a local video file.
- Uses an optional local `faster-whisper` install to create real captions.
- Finds candidate moments with deterministic transcript heuristics and deduplication.
- Falls back to evenly spaced review clips when no transcript is available.
- Renders 9:16 MP4s with FFmpeg, centered framing, AAC audio, and burned captions when available.
- Writes `manifest.json` and one JSON file per clip so agents can inspect scores, timestamps, reasons, and output paths.
- Provides a local browser GUI and a CLI. Optional API/GUI dependencies are isolated.

## Install

Install FFmpeg and yt-dlp first. On Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
python3 -m pip install -U yt-dlp
```

Then install qwenotn-clipper:

```bash
git clone https://github.com/naitik99045/qwenotn-clipper.git
cd qwenotn-clipper
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[all]'
```

The `faster-whisper` package downloads a model the first time it is used. If you want a no-model fallback, install only `pip install -e '.[gui]'`; clips still render without captions when no `.srt` sidecar is present.

## CLI

```bash
qwenotn-clipper clip 'https://www.youtube.com/watch?v=VIDEO_ID' --count 5 --duration 45 --output output/video-1
```

For agent use, request JSON:

```bash
qwenotn-clipper clip INPUT --count 5 --duration 45 --json > result.json
```

A local file works too:

```bash
qwenotn-clipper clip ./recording.mp4 --output output/recording
```

The command exits non-zero with a clear error and JSON `{ "ok": false, "error": "..." }` when a required dependency, input, download, or render fails. It never claims success if an output file is missing or empty.

## Browser GUI

```bash
qwenotn-clipper gui --host 127.0.0.1 --port 7860
```

Open <http://127.0.0.1:7860>. Enter a YouTube URL or local path, choose clip count and duration, and review the generated files under `output/<job-id>/`.

## Agent integration

The lowest-friction integration is shell plus JSON. An agent can:

1. Run `qwenotn-clipper clip URL --json`.
2. Read `manifest.json` and the per-clip JSON files.
3. Pick clips using score, reason, duration, and caption status.
4. Ask for human approval.
5. Upload only approved MP4s through the destination platform's official workflow.

This works with Antigravity, Claude Code, Cursor, OpenClaw, and other agents that can execute a process. A future release can add an MCP server without changing the deterministic media pipeline.

## Reliability model

No media tool can promise zero errors because YouTube formats, codecs, GPU drivers, captions, and platform policies change. qwenotn-clipper is designed to fail safely instead:

- retries downloads and fragments;
- checks that FFmpeg outputs really exist and are non-empty;
- uses CPU-compatible FFmpeg encoding by default;
- uses optional Whisper rather than making a remote API a hard dependency;
- produces a usable no-transcript fallback;
- writes machine-readable error messages;
- keeps the generated clip free of synthetic content by default.

## Rights and publishing

Use this project for recordings you own or have permission to repurpose. Public visibility does not automatically grant permission to download, modify, or repost a stream. This repository does not include auto-posting; review clips manually and use official platform APIs or upload workflows.

## License

MIT.
