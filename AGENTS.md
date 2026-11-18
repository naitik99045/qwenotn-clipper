# Agent contract

qwenotn-clipper is safe to call from an agent through the CLI.

## Preferred command

```bash
qwenotn-clipper clip INPUT --count 5 --duration 45 --output output/job --json
```

Treat stdout as JSON. On failure, exit code is non-zero and the JSON contains `ok: false` and an actionable `error`. On success, inspect `clips[*].path`, `score`, `reason`, and `captioned`.

## Editing policy

Do not add invented text, AI-generated visuals, fake reactions, meme overlays, or audio not present in the source. The default renderer only crops, scales, pads, encodes, and optionally burns captions generated from source speech.

## Approval policy

Never publish automatically unless the user has explicitly configured an approved publishing action. The normal agent flow is clip -> inspect manifest -> ask for approval -> publish approved files.
