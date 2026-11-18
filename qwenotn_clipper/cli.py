from __future__ import annotations

import argparse
import json
import sys


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", help="completed YouTube VOD URL or local video file")
    parser.add_argument("--output", default="output", help="output directory")
    parser.add_argument("--count", type=int, default=10, help="maximum number of candidates/clips")
    parser.add_argument("--duration", type=float, default=45, help="target clip duration in seconds")
    parser.add_argument("--focus", default="", help="theme such as 'funny GTA moments' or 'best gameplay kills'")
    parser.add_argument("--whisper-model", default="small")
    parser.add_argument("--json", action="store_true", help="print machine-readable result")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qwenotn-clipper", description="Fast, local-first clips for humans and AI agents.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("clip", help="analyze a finite VOD and render vertical clips")
    _common(p)
    a = sub.add_parser("analyze", help="analyze a finite VOD and write candidates without rendering")
    _common(a)
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
    from .pipeline import analyze, process
    try:
        fn = analyze if args.command == "analyze" else process
        result = fn(args.source, args.output, args.count, args.duration, args.whisper_model, args.focus, progress=lambda m: None if args.json else print(m, file=sys.stderr))
        print(json.dumps(result, indent=2) if args.json else (f"Analyzed {len(result['candidates'])} candidates in {args.output}" if args.command == "analyze" else f"Created {len(result['clips'])} clips in {args.output}"))
        return 0
    except Exception as exc:
        payload = {"ok": False, "error": str(exc), "source": getattr(args, "source", None)}
        if args.json: print(json.dumps(payload, indent=2))
        else: print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
