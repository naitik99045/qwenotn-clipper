from __future__ import annotations

import html
import threading
import uuid
from pathlib import Path
from typing import Any

from .pipeline import process

JOBS: dict[str, dict[str, Any]] = {}


def create_app():
    try:
        from fastapi import FastAPI, Form
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError("GUI dependencies missing. Install with: pip install -e '.[gui]'") from exc
    app = FastAPI(title="qwenotn-clipper", version="0.3.0")
    Path("output").mkdir(parents=True, exist_ok=True)
    app.mount("/files", StaticFiles(directory="output"), name="files")

    @app.get("/", response_class=HTMLResponse)
    def home():
        return HTMLResponse("""<!doctype html><meta name='viewport' content='width=device-width'><title>qwenotn-clipper</title><style>body{font:16px system-ui;max-width:760px;margin:40px auto;padding:0 18px;background:#111;color:#eee}input,button{font:inherit;padding:12px;margin:6px 0;width:100%;box-sizing:border-box}button{background:#6ee7b7;border:0;cursor:pointer}.card{border:1px solid #444;padding:16px;margin-top:18px;border-radius:10px}small{color:#aaa}</style><h1>qwenotn-clipper</h1><p>Local-first, clean clips. No fake hook cards, AI avatars, or unnecessary effects.</p><form method='post' action='/jobs'><input name='source' placeholder='YouTube URL or local video path' required><input name='count' type='number' min='1' max='20' value='5'><input name='duration' type='number' min='15' max='120' value='45'><button>Find and render clips</button></form><p><small>Outputs are written to ./output. Review clips before publishing.</small></p>""")

    @app.post("/jobs", response_class=HTMLResponse)
    def new_job(source: str = Form(...), count: int = Form(5), duration: float = Form(45)):
        job_id = uuid.uuid4().hex[:10]
        JOBS[job_id] = {"status": "queued", "logs": [], "result": None}
        def run_job():
            JOBS[job_id]["status"] = "running"
            try:
                result = process(source, f"output/{job_id}", count, duration, progress=lambda m: JOBS[job_id]["logs"].append(m))
                JOBS[job_id].update(status="done", result=result)
            except Exception as exc:
                JOBS[job_id].update(status="error", error=str(exc))
        threading.Thread(target=run_job, daemon=True).start()
        return HTMLResponse(f"<meta http-equiv='refresh' content='0;url=/jobs/{job_id}'><p>Started job {html.escape(job_id)}</p>")

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_page(job_id: str):
        job = JOBS.get(job_id)
        if not job: return HTMLResponse("Job not found", status_code=404)
        if job["status"] in {"queued", "running"}: return HTMLResponse(f"<meta http-equiv='refresh' content='2'><h2>Job {job_id}: {job['status']}</h2><pre>{html.escape(chr(10).join(job['logs']))}</pre>")
        if job["status"] == "error": return HTMLResponse(f"<h2>Failed</h2><pre>{html.escape(job['error'])}</pre>", status_code=500)
        clips = "".join(f"<li><a href='/files/{job_id}/clip_{c['index']:02d}.mp4'>Download clip {c['index']}</a> — score {c['score']}</li>" for c in job["result"]["clips"])
        return HTMLResponse(f"<h2>Complete</h2><p>Review before posting.</p><ul>{clips}</ul><pre>{html.escape(str(job['result']['candidates']))}</pre>")

    @app.get("/api/jobs/{job_id}")
    def job_api(job_id: str):
        return JSONResponse(JOBS.get(job_id, {"status": "not_found"}))

    return app
