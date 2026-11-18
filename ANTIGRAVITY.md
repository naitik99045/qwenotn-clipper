# Install as an Antigravity plugin

Antigravity plugins are local directories with a `plugin.json` manifest and optional skills. This repository now includes both.

## CLI installation from GitHub

```bash
git clone https://github.com/naitik99045/qwenotn-clipper.git
cd qwenotn-clipper
agy plugin validate --strict .
agy plugin install .
agy plugin list
```

Restart Antigravity or reload plugins if needed. In an interactive CLI session, use `/plugin` to confirm the plugin is installed and enabled. Invoke the skill explicitly with:

```text
/qwenotn-clipper
```

Or ask naturally:

```text
Use qwenotn-clipper to create five clean captioned vertical clips from this stream. Do not add AI-generated overlays and do not publish anything.
```

## Workspace-only installation

To activate it only in one project, copy or clone the repository under:

```text
<your-workspace>/.agents/plugins/qwenotn-clipper/
```

Then open that workspace in Antigravity. For all workspaces on the machine, place it under:

```text
~/.gemini/config/plugins/qwenotn-clipper/
```

## Runtime prerequisites

Plugin installation does not install system media dependencies. On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
python3 -m pip install -U yt-dlp
python3 -m pip install -e '.[all]'
```

Run `qwenotn-clipper --help` before the first job. The plugin uses shell + JSON rather than an MCP server, which keeps the first integration local and auditable.
