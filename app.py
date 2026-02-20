"""
VIBE STUDIO v2.1 — AI-Powered Video Creator & Editor
Run:   python app.py
Open:  http://localhost:8000
"""

import os, sys, json, uuid, shutil, asyncio, subprocess, logging, time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

try:
    from fastapi import (
        FastAPI, UploadFile, File, Form, Request,
        HTTPException, WebSocket, WebSocketDisconnect
    )
    from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    print("\n" + "="*60)
    print("  MISSING DEPENDENCIES — Run:")
    print("  pip install -r requirements.txt")
    print("  Also install FFmpeg (brew/apt/choco install ffmpeg)")
    print("="*60 + "\n")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
OUTPUT_DIR = BASE_DIR / "static" / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vibe-studio")

def check_ffmpeg():
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        logger.info(f"FFmpeg: {r.stdout.split(chr(10))[0]}")
        return True
    except FileNotFoundError:
        logger.warning("FFmpeg NOT found — video export disabled")
        return False

HAS_FFMPEG = check_ffmpeg()

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Vibe Studio", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
projects = {}

VIDEO_CATEGORIES = {
    "motivational": {"label": "💪 Motivational", "color_filter": "eq=brightness=0.06:saturation=1.3"},
    "travel":       {"label": "✈️ Travel",       "color_filter": "eq=brightness=0.04:saturation=1.5"},
    "food":         {"label": "🍕 Food",         "color_filter": "eq=brightness=0.05:saturation=1.4"},
    "fitness":      {"label": "🏋️ Fitness",      "color_filter": "eq=contrast=1.2:saturation=1.2"},
    "corporate":    {"label": "🏢 Corporate",    "color_filter": "eq=brightness=0.02:saturation=0.9"},
    "celebration":  {"label": "🎉 Celebration",  "color_filter": "eq=brightness=0.08:saturation=1.6"},
    "religious":    {"label": "🕌 Religious",     "color_filter": "eq=brightness=0.03:saturation=0.85:gamma=1.05"},
    "chill":        {"label": "😎 Chill",         "color_filter": "eq=brightness=0.02:saturation=0.8"},
}
AUDIO_VIBES = {
    "energetic":  {"label": "⚡ Energetic",  "desc": "Upbeat, fast-paced"},
    "chill":      {"label": "🌊 Chill",      "desc": "Lo-fi / ambient"},
    "cinematic":  {"label": "🎬 Cinematic",  "desc": "Epic orchestral"},
    "romantic":   {"label": "💕 Romantic",    "desc": "Soft, emotional"},
    "religious":  {"label": "🕌 Religious",   "desc": "Nasheeds, spiritual, devotional"},
    "corporate":  {"label": "📊 Corporate",  "desc": "Professional background"},
    "travel":     {"label": "🌍 Travel",     "desc": "World music, adventurous"},
    "custom":     {"label": "🎵 Custom",     "desc": "Upload your own audio"},
}

async def run_ffmpeg(cmd, timeout=120):
    logger.info(f"FFmpeg: {' '.join(cmd[:8])}...")
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill(); return {"success": False, "error": "Timed out"}
    if proc.returncode != 0:
        return {"success": False, "error": stderr.decode()[-500:]}
    return {"success": True}


# ══════════════════════════════════════════════════════════════════════════════
# ALL API ROUTES (defined BEFORE static mount)
# ══════════════════════════════════════════════════════════════════════════════

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, "categories": VIDEO_CATEGORIES,
        "audio_vibes": AUDIO_VIBES, "has_ffmpeg": HAS_FFMPEG,
    })

# ── Debug: list all routes ────────────────────────────────────────────────────
@app.get("/api/debug/routes")
async def debug_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods'):
            routes.append({"path": route.path, "methods": list(route.methods)})
    return routes

# ── Info ──────────────────────────────────────────────────────────────────────
@app.get("/api/categories")
async def list_categories():
    return VIDEO_CATEGORIES

@app.get("/api/audio-vibes")
async def list_audio_vibes():
    return AUDIO_VIBES

@app.get("/api/status")
async def get_status():
    return {"ffmpeg": HAS_FFMPEG, "projects": len(projects), "version": "2.1.0"}

# ── Audio Search ──────────────────────────────────────────────────────────────
CURATED_AUDIO = [
    {"id": "1", "title": "Peaceful Ambient", "user": "Royalty-Free", "duration": 120, "genre": "chill,ambient,peaceful,meditation,religious,spiritual", "preview_url": ""},
    {"id": "2", "title": "Upbeat Corporate", "user": "Royalty-Free", "duration": 90, "genre": "corporate,business,upbeat,professional", "preview_url": ""},
    {"id": "3", "title": "Cinematic Epic", "user": "Royalty-Free", "duration": 150, "genre": "cinematic,epic,dramatic,film,trailer", "preview_url": ""},
    {"id": "4", "title": "Energetic Pop", "user": "Royalty-Free", "duration": 100, "genre": "energetic,pop,upbeat,happy,fun", "preview_url": ""},
    {"id": "5", "title": "Acoustic Guitar", "user": "Royalty-Free", "duration": 110, "genre": "acoustic,guitar,warm,folk,travel", "preview_url": ""},
    {"id": "6", "title": "Lo-Fi Chill Beats", "user": "Royalty-Free", "duration": 180, "genre": "lofi,chill,beats,study,relax", "preview_url": ""},
    {"id": "7", "title": "Nasheed Devotional", "user": "Royalty-Free", "duration": 130, "genre": "nasheed,religious,islamic,spiritual,devotional,peaceful", "preview_url": ""},
    {"id": "8", "title": "Happy Celebration", "user": "Royalty-Free", "duration": 95, "genre": "celebration,happy,birthday,party,wedding,eid", "preview_url": ""},
    {"id": "9", "title": "Motivational Rise", "user": "Royalty-Free", "duration": 120, "genre": "motivational,inspiring,gym,fitness,workout,rise", "preview_url": ""},
    {"id": "10", "title": "Nature & Serenity", "user": "Royalty-Free", "duration": 140, "genre": "nature,calm,serene,water,forest,peaceful", "preview_url": ""},
    {"id": "11", "title": "Travel Adventure", "user": "Royalty-Free", "duration": 105, "genre": "travel,adventure,world,explore,journey", "preview_url": ""},
    {"id": "12", "title": "Romantic Piano", "user": "Royalty-Free", "duration": 130, "genre": "romantic,piano,love,wedding,soft,emotional", "preview_url": ""},
]

@app.get("/api/audio/search")
async def search_audio(q: str, per_page: int = 12, api_key: str = ""):
    """Search royalty-free music. Uses Pixabay API if key provided, else curated list."""
    logger.info(f"Audio search: q={q}, has_key={bool(api_key)}")
    key = api_key or os.environ.get("PIXABAY_API_KEY", "")

    if key:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://pixabay.com/api/",
                    params={"key": key, "q": q, "media_type": "music", "per_page": per_page},
                    timeout=10,
                )
                logger.info(f"Pixabay response: {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    results = []
                    for h in data.get("hits", []):
                        results.append({
                            "id": h.get("id"),
                            "title": h.get("tags", "Untitled"),
                            "user": h.get("user", "Unknown"),
                            "duration": h.get("duration", 0),
                            "preview_url": h.get("previewURL", ""),
                            "download_url": h.get("audio", h.get("previewURL", "")),
                        })
                    return {"results": results, "total": data.get("totalHits", 0), "source": "pixabay"}
                else:
                    logger.error(f"Pixabay error {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Audio search error: {e}")

    # Fallback to curated
    ql = q.lower()
    matches = [t for t in CURATED_AUDIO if any(w in t["genre"] for w in ql.split())]
    if not matches:
        matches = CURATED_AUDIO
    return {
        "results": matches, "total": len(matches), "source": "curated",
        "note": "Add your Pixabay API key in Settings for real music search with audio previews. Free key at pixabay.com/api/docs/"
    }

@app.get("/api/audio/download")
async def download_audio_proxy(url: str):
    """Proxy download of audio to avoid CORS."""
    try:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True) as client:
            r = await client.get(url, timeout=30)
            if r.status_code == 200:
                return Response(content=r.content, media_type="audio/mpeg",
                                headers={"Content-Disposition": "attachment; filename=audio.mp3"})
    except Exception as e:
        raise HTTPException(500, str(e))

# ── Project API ───────────────────────────────────────────────────────────────
@app.post("/api/project/create")
async def create_project(category: str = Form("motivational"), audio_vibe: str = Form("energetic"), duration: int = Form(30)):
    pid = str(uuid.uuid4())[:8]
    (UPLOAD_DIR / pid).mkdir(parents=True, exist_ok=True)
    projects[pid] = {
        "id": pid, "category": category, "audio_vibe": audio_vibe,
        "target_duration": duration, "media": [],
        "audio_tracks": [],  # list of {id, filename, path, url, role, volume}
        "audio_file": None,  # legacy compat
        "video_volume": 100,  # 0-100 for original video audio
        "status": "draft", "created": datetime.now().isoformat(),
    }
    return {"project_id": pid}

@app.get("/api/project/{pid}")
async def get_project(pid: str):
    if pid not in projects: raise HTTPException(404)
    return projects[pid]

@app.put("/api/project/{pid}")
async def update_project(pid: str, request: Request):
    if pid not in projects: raise HTTPException(404)
    data = await request.json()
    for k in ["category", "audio_vibe", "target_duration", "video_volume"]:
        if k in data: projects[pid][k] = data[k]
    return {"status": "updated"}

# ── Upload API ────────────────────────────────────────────────────────────────
@app.post("/api/project/{pid}/upload")
async def upload_media(pid: str, files: List[UploadFile] = File(...)):
    if pid not in projects: raise HTTPException(404)
    project = projects[pid]
    results = []
    for f in files:
        fid = str(uuid.uuid4())[:8]
        ext = Path(f.filename).suffix.lower()
        safe = f"{fid}{ext}"
        fp = UPLOAD_DIR / pid / safe
        with open(fp, "wb") as out:
            out.write(await f.read())
        if ext in [".mp3",".wav",".aac",".ogg",".m4a"]:
            audio_item = {
                "id": fid, "type": "audio", "filename": f.filename,
                "path": str(fp), "url": f"/static/uploads/{pid}/{safe}",
                "role": f"Audio {len(project['audio_tracks'])+1}",
                "volume": 50
            }
            project["audio_tracks"].append(audio_item)
            project["audio_file"] = str(fp)  # legacy compat: last uploaded
            results.append({"id": fid, "type": "audio", "filename": f.filename, "url": f"/static/uploads/{pid}/{safe}"})
            continue
        mtype = "video" if ext in [".mp4",".mov",".avi",".mkv",".webm"] else "image"
        item = {"id": fid, "type": mtype, "filename": f.filename, "path": str(fp),
                "url": f"/static/uploads/{pid}/{safe}", "order": len(project["media"]),
                "trim_start": 0, "trim_end": None, "caption": "", "custom_duration": None}
        project["media"].append(item)
        results.append(item)
    return {"uploaded": results, "total": len(project["media"])}

@app.delete("/api/project/{pid}/media/{mid}")
async def delete_media(pid: str, mid: str):
    if pid not in projects: raise HTTPException(404)
    projects[pid]["media"] = [m for m in projects[pid]["media"] if m["id"] != mid]
    return {"status": "deleted"}

@app.put("/api/project/{pid}/media/{mid}")
async def update_media(pid: str, mid: str, request: Request):
    if pid not in projects: raise HTTPException(404)
    data = await request.json()
    for m in projects[pid]["media"]:
        if m["id"] == mid:
            for k in ["trim_start","trim_end","caption","order","custom_duration"]:
                if k in data: m[k] = data[k]
            return {"status": "updated", "media": m}
    raise HTTPException(404)

@app.put("/api/project/{pid}/reorder")
async def reorder_media(pid: str, request: Request):
    if pid not in projects: raise HTTPException(404)
    data = await request.json()
    om = {mid: i for i, mid in enumerate(data["order"])}
    for m in projects[pid]["media"]:
        if m["id"] in om: m["order"] = om[m["id"]]
    projects[pid]["media"].sort(key=lambda x: x["order"])
    return {"status": "reordered"}

# ── Audio Track Management ────────────────────────────────────────────────────
@app.get("/api/project/{pid}/audio")
async def get_audio_tracks(pid: str):
    if pid not in projects: raise HTTPException(404)
    return {"audio_tracks": projects[pid].get("audio_tracks", []),
            "video_volume": projects[pid].get("video_volume", 100)}

@app.put("/api/project/{pid}/audio/{aid}")
async def update_audio_track(pid: str, aid: str, request: Request):
    """Update audio track volume or role."""
    if pid not in projects: raise HTTPException(404)
    data = await request.json()
    for t in projects[pid].get("audio_tracks", []):
        if t["id"] == aid:
            if "volume" in data: t["volume"] = data["volume"]
            if "role" in data: t["role"] = data["role"]
            return {"status": "updated", "track": t}
    raise HTTPException(404, "Audio track not found")

@app.delete("/api/project/{pid}/audio/{aid}")
async def delete_audio_track(pid: str, aid: str):
    if pid not in projects: raise HTTPException(404)
    project = projects[pid]
    project["audio_tracks"] = [t for t in project.get("audio_tracks", []) if t["id"] != aid]
    # Update legacy field
    if project["audio_tracks"]:
        project["audio_file"] = project["audio_tracks"][-1]["path"]
    else:
        project["audio_file"] = None
    return {"status": "deleted"}

@app.put("/api/project/{pid}/video-volume")
async def set_video_volume(pid: str, request: Request):
    if pid not in projects: raise HTTPException(404)
    data = await request.json()
    projects[pid]["video_volume"] = data.get("volume", 100)
    return {"status": "updated"}

# ── Trim API ──────────────────────────────────────────────────────────────────
@app.post("/api/project/{pid}/trim/{mid}")
async def trim_video(pid: str, mid: str, request: Request):
    if not HAS_FFMPEG: raise HTTPException(400, "FFmpeg not installed")
    if pid not in projects: raise HTTPException(404)
    data = await request.json()
    media = next((m for m in projects[pid]["media"] if m["id"] == mid), None)
    if not media or media["type"] != "video": raise HTTPException(400)
    out_name = f"{mid}_trimmed.mp4"
    out_path = str(UPLOAD_DIR / pid / out_name)
    cmd = ["ffmpeg", "-y", "-ss", str(data.get("start",0)), "-i", media["path"]]
    if data.get("end"): cmd += ["-to", str(data["end"])]
    cmd += ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast", out_path]
    r = await run_ffmpeg(cmd)
    if not r["success"]: raise HTTPException(500, r["error"])
    media["path"] = out_path
    media["url"] = f"/static/uploads/{pid}/{out_name}"
    return {"status": "trimmed", "media": media}

# ── Generate Video API ────────────────────────────────────────────────────────
@app.post("/api/project/{pid}/generate")
async def generate_video(pid: str, request: Request):
    if not HAS_FFMPEG: raise HTTPException(400, "FFmpeg not installed")
    if pid not in projects: raise HTTPException(404)
    project = projects[pid]
    media_items = sorted(project["media"], key=lambda x: x["order"])
    if not media_items: raise HTTPException(400, "No media")
    try: body = await request.json()
    except: body = {}
    target_dur = body.get("duration", project["target_duration"])
    w, h, fps = body.get("width", 1080), body.get("height", 1920), body.get("fps", 30)
    cat = VIDEO_CATEGORIES.get(project["category"], VIDEO_CATEGORIES["motivational"])
    cf = cat["color_filter"]
    video_vol = project.get("video_volume", 100) / 100.0
    audio_tracks = project.get("audio_tracks", [])

    # Calculate per-segment duration: use custom_duration if set, else split evenly
    default_dur = max(2, target_dur / len(media_items))

    # Check how much time custom durations consume
    custom_total = sum(m.get("custom_duration", 0) for m in media_items if m.get("custom_duration"))
    auto_count = sum(1 for m in media_items if not m.get("custom_duration"))
    if auto_count > 0 and custom_total < target_dur:
        auto_dur = max(2, (target_dur - custom_total) / auto_count)
    else:
        auto_dur = default_dur

    logger.info(f"Generating: {len(media_items)} items, {target_dur}s target, auto_dur={auto_dur:.1f}s, {w}x{h}")

    # Longer timeout for longer videos
    seg_timeout = max(90, int(target_dur * 4))

    # Step 1: Create each segment
    segments = []
    for i, item in enumerate(media_items):
        # Per-clip duration
        dur_per = item.get("custom_duration") or auto_dur
        seg = str(UPLOAD_DIR / pid / f"seg_{i:03d}.mp4")
        if item["type"] == "image":
            # zoompan frames = dur_per * fps
            zpframes = int(dur_per * fps)
            # Show FULL image with blurred background (no black bars, no crop)
            # Input 0 = blurred background, Input 1 = sharp foreground
            vf = (
                # Background: scale to fill, crop to frame, blur
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h}:(iw-{w})/2:(ih-{h})/2,"
                f"gblur=sigma=30[bg];"
                # Foreground: fit entire image (no crop), make transparent padding
                f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                # Overlay foreground centered on blurred bg
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                # Gentle Ken Burns zoom
                f"zoompan=z='min(zoom+0.0005,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={zpframes}:s={w}x{h}:fps={fps},"
                f"{cf}"
            )
            cmd = ["ffmpeg","-y","-loop","1","-i",item["path"],
                   "-loop","1","-i",item["path"],
                   "-filter_complex", vf,
                   "-t",str(dur_per),
                   "-c:v","libx264","-preset","fast","-pix_fmt","yuv420p","-an",seg]
        else:
            # Video: keep original audio if video_vol > 0, apply volume
            ss = item.get("trim_start", 0)
            cmd = ["ffmpeg","-y"]
            if ss: cmd += ["-ss", str(ss)]
            cmd += ["-i", item["path"]]
            te = item.get("trim_end")
            avail_dur = (te - ss) if te else dur_per
            seg_dur = min(dur_per, avail_dur) if te else dur_per
            cmd += ["-t", str(seg_dur)]
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},{cf}"
            if video_vol > 0:
                # Keep audio with volume control
                cmd += ["-vf", vf,
                        "-af", f"volume={video_vol}",
                        "-c:v","libx264","-preset","fast","-pix_fmt","yuv420p",
                        "-c:a","aac","-b:a","128k", seg]
            else:
                cmd += ["-vf", vf,
                        "-c:v","libx264","-preset","fast","-pix_fmt","yuv420p","-an", seg]
        r = await run_ffmpeg(cmd, seg_timeout)
        if r["success"]:
            segments.append(seg)
        else:
            logger.error(f"Segment {i} failed: {r.get('error','')[:200]}")

    if not segments: raise HTTPException(500, "All segments failed")

    # Step 2: Concatenate segments (video-only to avoid stream mismatch)
    concat_f = str(UPLOAD_DIR / pid / "concat.txt")
    with open(concat_f, "w") as f:
        for s in segments: f.write(f"file '{s}'\n")

    out_name = f"vibe_{pid}_{int(time.time())}.mp4"
    concat_out = str(OUTPUT_DIR / f"concat_{out_name}")
    final = str(OUTPUT_DIR / out_name)

    concat_timeout = max(180, int(target_dur * 3))
    r = await run_ffmpeg([
        "ffmpeg","-y","-f","concat","-safe","0","-i",concat_f,
        "-c:v","libx264","-preset","fast","-pix_fmt","yuv420p",
        "-an",  # always strip audio — we mix separately below
        concat_out
    ], concat_timeout)
    if not r["success"]: raise HTTPException(500, "Concat failed")

    # Step 3: Mix all audio sources into the video
    # Strategy: concat video is always silent. We build all audio inputs
    # separately and amix them, then merge with the silent video.

    valid_tracks = [t for t in audio_tracks if os.path.exists(t["path"])]
    has_vid_segments_audio = video_vol > 0 and any(m["type"] == "video" for m in media_items)

    # Extract video audio if needed (from original video segments before concat stripped it)
    vid_audio_file = None
    if has_vid_segments_audio:
        # Re-concat only video segments that had audio to extract their audio
        va_concat = str(UPLOAD_DIR / pid / "va_concat.txt")
        va_segs = []
        for i, item in enumerate(media_items):
            seg_path = str(UPLOAD_DIR / pid / f"seg_{i:03d}.mp4")
            if item["type"] == "video" and os.path.exists(seg_path):
                va_segs.append(seg_path)
        if va_segs:
            with open(va_concat, "w") as f:
                for s in va_segs: f.write(f"file '{s}'\n")
            vid_audio_file = str(UPLOAD_DIR / pid / "vid_audio.aac")
            va_r = await run_ffmpeg([
                "ffmpeg","-y","-f","concat","-safe","0","-i",va_concat,
                "-vn","-c:a","aac","-b:a","128k", vid_audio_file
            ], 60)
            if not va_r["success"]:
                logger.warning("Could not extract video audio, skipping")
                vid_audio_file = None

    if valid_tracks or vid_audio_file:
        # Build ffmpeg command: video + looped audio inputs
        inputs = ["-i", concat_out]
        filter_parts = []
        mix_labels = []
        inp_idx = 1

        # Add each uploaded/searched audio track (looped to fill video length)
        for idx, track in enumerate(valid_tracks):
            inputs += ["-stream_loop", "-1", "-i", track["path"]]
            vol = track.get("volume", 50) / 100.0
            label = f"a{idx}"
            filter_parts.append(f"[{inp_idx}:a]volume={vol}[{label}]")
            mix_labels.append(f"[{label}]")
            inp_idx += 1

        # Add video original audio if extracted
        if vid_audio_file:
            inputs += ["-i", vid_audio_file]
            filter_parts.append(f"[{inp_idx}:a]volume={video_vol}[va]")
            mix_labels.append("[va]")
            inp_idx += 1

        # Build the mix
        n = len(mix_labels)
        if n == 1:
            # Single source — rename directly to [aout]
            filter_str = filter_parts[0]
            # Replace last label with [aout]
            last_bracket = filter_str.rfind("[")
            filter_str = filter_str[:last_bracket] + "[aout]"
        else:
            # Multiple sources — amix
            all_labels = "".join(mix_labels)
            filter_str = ";".join(filter_parts) + f";{all_labels}amix=inputs={n}:duration=first:dropout_transition=0:normalize=0[aout]"

        logger.info(f"Audio mix: {n} sources, filter={filter_str}")

        mix_cmd = ["ffmpeg","-y"] + inputs + [
            "-filter_complex", filter_str,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(target_dur),
            final
        ]
        r2 = await run_ffmpeg(mix_cmd, concat_timeout)
        if r2["success"]:
            try: os.remove(concat_out)
            except: pass
        else:
            logger.error(f"Audio mix failed: {r2.get('error','')[:300]}")
            # Fallback: overlay first audio simply
            fb_track = valid_tracks[0]["path"] if valid_tracks else vid_audio_file
            if fb_track:
                r3 = await run_ffmpeg([
                    "ffmpeg","-y","-i",concat_out,
                    "-stream_loop","-1","-i",fb_track,
                    "-c:v","copy","-c:a","aac","-b:a","192k",
                    "-map","0:v:0","-map","1:a:0",
                    "-t",str(target_dur),final
                ])
                if r3["success"]:
                    try: os.remove(concat_out)
                    except: pass
                else:
                    shutil.move(concat_out, final)
            else:
                shutil.move(concat_out, final)
    else:
        shutil.move(concat_out, final)

    # Cleanup
    for s in segments:
        try: os.remove(s)
        except: pass
    for tmp in ["concat.txt", "va_concat.txt", "vid_audio.aac"]:
        try: os.remove(str(UPLOAD_DIR / pid / tmp))
        except: pass

    project["status"] = "complete"
    project["output"] = f"/static/outputs/{out_name}"
    return {"status": "complete", "video_url": f"/static/outputs/{out_name}",
            "download_url": f"/api/download/{out_name}", "filename": out_name}

@app.get("/api/download/{filename}")
async def download_video(filename: str):
    fp = OUTPUT_DIR / filename
    if not fp.exists(): raise HTTPException(404)
    return FileResponse(str(fp), filename=filename, media_type="video/mp4")

# ── AI Chat API ───────────────────────────────────────────────────────────────
@app.post("/api/chat")
async def ai_chat(request: Request):
    data = await request.json()
    msg = data.get("message", "")
    pid = data.get("project_id")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            ctx = ""
            if pid and pid in projects:
                p = projects[pid]
                ctx = f"\nProject: category={p['category']}, audio={p['audio_vibe']}, {len(p['media'])} files."
            resp = client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=1000,
                system=f"You are Vibe Studio AI, a creative video assistant. Categories: {list(VIDEO_CATEGORIES.keys())}. Audio vibes: {list(AUDIO_VIBES.keys())}. Respond with suggestions and optionally a JSON action block in ```json``` fences.{ctx}",
                messages=[{"role": "user", "content": msg}],
            )
            return {"reply": resp.content[0].text, "source": "ai"}
        except Exception as e:
            logger.error(f"AI error: {e}")
    return {"reply": _template_reply(msg), "source": "template"}

def _template_reply(msg):
    ml = msg.lower()
    if any(w in ml for w in ["religious","islamic","spiritual","nasheed","quran","church","devotional","eid","ramadan"]):
        return '🕌 For a **religious** video:\n\n```json\n{"action":"configure","category":"religious","audio_vibe":"religious","captions":["In the name of God, the Most Gracious","Peace and blessings upon you","With hardship comes ease","May your faith guide your way"],"suggestion":"Warm golden tones, soft transitions. Upload calligraphy or nature photos."}\n```\n\nUpload your own nasheed or devotional audio, or search for "peaceful" / "spiritual" in the audio search!'
    if any(w in ml for w in ["motivat","inspire","gym","workout","fitness"]):
        return '💪 **Motivational** vibe:\n\n```json\n{"action":"configure","category":"motivational","audio_vibe":"energetic","captions":["Rise and grind","No excuses","Your only limit is you","Make it happen"],"suggestion":"High contrast, bold text, quick cuts."}\n```'
    if any(w in ml for w in ["travel","trip","vacation"]):
        return '✈️ **Travel** vibe:\n\n```json\n{"action":"configure","category":"travel","audio_vibe":"travel","captions":["Exploring the unknown","Wanderlust diaries","New horizons","Life is a journey"],"suggestion":"Saturated colors, smooth transitions."}\n```'
    if any(w in ml for w in ["food","cook","recipe"]):
        return '🍕 **Food** vibe:\n\n```json\n{"action":"configure","category":"food","audio_vibe":"chill","captions":["Made with love","Good food, good mood","Chef\'s kiss"],"suggestion":"Warm tones, close-ups, slow motion."}\n```'
    if any(w in ml for w in ["celebrat","birthday","wedding","party"]):
        return '🎉 **Celebration** vibe:\n\n```json\n{"action":"configure","category":"celebration","audio_vibe":"energetic","captions":["Cheers!","Making memories","Best day ever"],"suggestion":"Bright colors, fun transitions!"}\n```'
    return '🎬 Welcome to **Vibe Studio AI**! Tell me what kind of video you want:\n\n- "Religious video with nasheeds"\n- "Motivational gym reel"\n- "Travel montage"\n- "Birthday celebration"\n- "Food/recipe reel"\n\nDescribe your vision and I\'ll configure everything!'


# ══════════════════════════════════════════════════════════════════════════════
# STATIC FILES MOUNT — must be LAST so API routes take priority
# ══════════════════════════════════════════════════════════════════════════════
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))

    # Print all registered API routes for debugging
    print("\n  Registered routes:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            print(f"    {','.join(route.methods):8s} {route.path}")
    print()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                 🎬  VIBE STUDIO v2.1  🎬                     ║
║                                                              ║
║   Browser:   http://localhost:{port}                          ║
║   FFmpeg:    {'✅ Ready' if HAS_FFMPEG else '❌ Not found'}                                ║
║   AI Chat:   {'✅ Key set' if os.environ.get('ANTHROPIC_API_KEY') else '⚠️  Set ANTHROPIC_API_KEY for AI chat'}         ║
╚══════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=port)
