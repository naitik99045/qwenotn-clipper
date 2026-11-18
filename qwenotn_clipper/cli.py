from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qwenotn-clipper", description="Clean, local-first clips for humans and AI agents.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("clip", help="find highlights and render vertical clips")
    p.add_argument("source", help="YouTube URL or local video file")
    p.add_argument("--output", default="output", help="output directory")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--duration", type=float, default=45)
    p.add_argument("--whisper-model", default="small")
    p.add_argument("--json", action="store_true", help="print machine-readable result")
    g = sub.add_parser("gui", help="start the local browser GUI")
    g.add_argument("--host", default="127.0.0.1")
    g.add_argument("--port", type=int, default=7860)
    args = parser.parse_args(argv)
    if args.command == "gui":
        try:
            import uvicorn
            from .gui import create_app
            uvicorn.run(create_app(), host=args.host, port=args.port)
            return 0
        except Exception as exc:
            print(str(exc), file=sys.stderr); return 2
    from .pipeline import process
    try:
        result = process(args.source, args.output, args.count, args.duration, args.whisper_model, progress=lambda m: None if args.json else print(m, file=sys.stderr))
        print(json.dumps(result, indent=2) if args.json else f"Created {len(result['clips'])} clips in {args.output}")
        return 0
    except Exception as exc:
        if args.json: print(json.dumps({"ok": False, "error": str(exc)}))
        else: print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
