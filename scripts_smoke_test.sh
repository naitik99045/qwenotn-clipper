#!/usr/bin/env bash
set -euo pipefail
mkdir -p /tmp/qwenotn-smoke
ffmpeg -y -f lavfi -i testsrc=size=640x360:rate=25 -f lavfi -i sine=frequency=440:duration=12 -t 12 -c:v libx264 -pix_fmt yuv420p -c:a aac /tmp/qwenotn-smoke/input.mp4 >/dev/null 2>&1
python -m qwenotn_clipper.cli clip /tmp/qwenotn-smoke/input.mp4 --count 1 --duration 5 --output /tmp/qwenotn-smoke/output --json
 test -s /tmp/qwenotn-smoke/output/clip_01.mp4
printf 'smoke test passed\n'
