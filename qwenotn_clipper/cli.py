from __future__ import annotations

import argparse
import json
import sys


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", help="completed YouTube VOD URL or local video file")
    parser.add_argument("--output", default="output")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--duration", default="45", help="seconds or auto for event windows")
    parser.add_argument("--focus", default="", help="theme such as 'funny GTA moments' or 'best gameplay kills'")
    parser.add_argument("--game", default="generic", choices=["generic", "valorant", "counter-strike-2", "shooter"])
    parser.add_argument("--event", default="", help="requested event such as headshot, kill, clutch, or objective")
    parser.add_argument("--pre-roll", type=float, default=4.0)
    parser.add_argument("--post-roll", type=float, default=7.0)
    parser.add_argument("--whisper-model", default="small")
    parser.add_argument("--cookies", help="permitted browser cookie export file; never logged")
    parser.add_argument("--cookies-from-browser", help="permitted browser profile, e.g. chrome")
    parser.add_argument("--extractor-args", help="yt-dlp extractor arguments")
    parser.add_argument("--caption-style", default="clean", choices=["clean", "gaming", "bold", "minimal", "none"])
    parser.add_argument("--crop", default="smart", choices=["smart", "center", "left", "right"])
    parser.add_argument("--normalize-audio", action="store_true")
    parser.add_argument("--music")
    parser.add_argument("--music-volume", type=float, default=0.08)
    parser.add_argument("--duck-source-audio", action="store_true")
    parser.add_argument("--vision", action="store_true", help="enable optional OpenCV motion evidence")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--live-window", type=int, help="bounded live mode is explicit; current release reports unsupported")
    parser.add_argument("--json", action="store_true")


def _kwargs(args) -> dict:
    if args.live_window is not None and args.live_window <= 0:
        raise ValueError("--live-window must be positive seconds")
    if args.live_window is not None:
        raise ValueError("Bounded live-window mode is not enabled in this release; use a completed VOD to avoid indefinite downloads.")
    duration: float | str = "auto" if str(args.duration).lower() == "auto" else float(args.duration)
    return dict(duration=duration, whisper_model=args.whisper_model, focus=args.focus, game=args.game, event=args.event, pre_roll=args.pre_roll, post_roll=args.post_roll, cookies=args.cookies, cookies_from_browser=args.cookies_from_browser, extractor_args=args.extractor_args, caption_style=args.caption_style, crop=args.crop, normalize_audio=args.normalize_audio, music=args.music, music_volume=args.music_volume, duck_source_audio=args.duck_source_audio, enable_vision=args.vision, enable_audio=not args.no_audio)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qwenotn-clipper", description="Fast, local-first clips for humans and AI agents.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in [("clip", "analyze a finite VOD and render vertical clips"), ("highlight", "alias for clip"), ("analyze", "analyze a finite VOD and write candidates without rendering")]:
        p = sub.add_parser(name, help=help_text); _common(p)
    g = sub.add_parser("gui", help="start the local browser GUI")
    g.add_argument("--host", default="127.0.0.1"); g.add_argument("--port", type=int, default=7860)
    args = parser.parse_args(argv)
    if args.command == "gui":
        try:
            import uvicorn
            from .gui import create_app
            uvicorn.run(create_app(), host=args.host, port=args.port); return 0
        except Exception as exc:
            print(str(exc), file=sys.stderr); return 2
    from .pipeline import analyze, process
    try:
        kwargs = _kwargs(args)
        fn = analyze if args.command == "analyze" else process
        result = fn(args.source, output_dir=args.output, count=args.count, progress=lambda m: None if args.json else print(m, file=sys.stderr), **kwargs)
        if args.json: print(json.dumps(result, indent=2))
        elif args.command == "analyze": print(f"Analyzed {len(result['candidates'])} candidates in {args.output}")
        else: print(f"Created {len(result['clips'])} clips in {args.output}")
        return 0
    except Exception as exc:
        payload = {"ok": False, "error": str(exc), "source": getattr(args, "source", None)}
        if getattr(args, "json", False): print(json.dumps(payload, indent=2))
        else: print(f"ERROR: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
