"""MemPalace Web UI — FastAPI backend wrapping mempalace CLI."""
import subprocess
import os
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="MemPalace Web")

MEM_PATH = os.path.expanduser("~/.local/bin/mempalace")
TPL_DIR = Path(__file__).parent / "templates"
INDEX_HTML = (TPL_DIR / "index.html").read_text(encoding="utf-8")


def _run(*args, timeout=30):
    env = os.environ.copy()
    env["HTTP_PROXY"] = "http://127.0.0.1:7897"
    env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
    try:
        r = subprocess.run(
            [MEM_PATH, *args],
            capture_output=True, text=True, timeout=timeout, env=env
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(INDEX_HTML)


@app.get("/api/status")
def api_status():
    out, err, rc = _run("status")
    if rc != 0:
        raise HTTPException(500, err or "status failed")
    lines = out.strip().split("\n")
    result = {"raw": out, "wings": []}
    current_wing = None
    for line in lines:
        if line.startswith("  WING:"):
            name = line.split("WING:")[1].strip()
            current_wing = {"name": name, "rooms": []}
            result["wings"].append(current_wing)
        elif "ROOM:" in line and current_wing is not None:
            parts = line.split("ROOM:")[1].strip().split()
            room_name = parts[0]
            count = parts[-2] if len(parts) >= 3 else "0"
            current_wing["rooms"].append({"name": room_name, "drawers": count})
    return result


@app.get("/api/search")
def api_search(q: str = Query(...), wing: str = "", room: str = ""):
    args = ["search", q]
    if wing:
        args += ["--wing", wing]
    if room:
        args += ["--room", room]
    out, err, rc = _run(*args, timeout=60)
    if rc != 0:
        raise HTTPException(500, err or "search failed")
    return {"results": out.strip()}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766)
