import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from paperdl.extract import extract_dois_from_text, extract_dois_from_excel
from paperdl.dispatch import adapter_key_for
from paperdl.web.jobs import JobManager

app = FastAPI(title="paperdl")
mgr = JobManager()
STATIC = Path(__file__).parent / "static"

_counter = [0]


def _new_id() -> str:
    _counter[0] += 1
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-%d" % _counter[0]


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.post("/api/extract")
async def api_extract(file: UploadFile = File(None), text: str = Form(None)):
    dois = []
    if file is not None and file.filename:
        suffix = Path(file.filename or "x").suffix.lower()
        raw = await file.read()
        tmp = Path("web_data") / ("upload" + suffix)
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(raw)
        if suffix in (".xls", ".xlsx"):
            dois = extract_dois_from_excel(tmp)
        else:
            dois = extract_dois_from_text(raw.decode("utf-8", "ignore"))
    elif text:
        dois = extract_dois_from_text(text)
    dist = {}
    for d in dois:
        k = adapter_key_for("", d) or "其他(兜底)"
        dist[k] = dist.get(k, 0) + 1
    return {"dois": dois, "count": len(dois), "distribution": dist}


@app.post("/api/jobs")
async def api_create_job(payload: dict):
    dois = payload.get("dois") or []
    if not dois:
        raise HTTPException(400, "no dois")
    job = mgr.create(_new_id(), datetime.now(timezone.utc).isoformat(), dois,
                     delay_min=float(payload.get("delay_min", 8)),
                     delay_max=float(payload.get("delay_max", 20)))
    mgr.start(job)
    return {"job_id": job.id}


@app.get("/api/jobs")
def api_list_jobs():
    return [{"id": j.id, "created_at": j.created_at, "total": j.total,
             "success": j.success, "failed": j.failed, "status": j.status} for j in mgr.list()]


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str):
    job = mgr.get(job_id)
    if not job:
        raise HTTPException(404, "not found")
    return job.to_public()


@app.post("/api/jobs/{job_id}/retry")
def api_retry(job_id: str):
    job = mgr.get(job_id)
    if not job:
        raise HTTPException(404, "not found")
    failed = [doi for doi, it in job.items.items() if it["status"] == "failed"]
    if not failed:
        return {"retrying": 0}
    mgr.start(job, only_dois=failed)
    return {"retrying": len(failed)}


@app.get("/api/jobs/{job_id}/file")
def api_file(job_id: str, name: str, dl: int = 0):
    job = mgr.get(job_id)
    if not job:
        raise HTTPException(404, "not found")
    p = (mgr.base / "web_data/jobs" / job_id / "pdfs" / name).resolve()
    root = (mgr.base / "web_data/jobs" / job_id / "pdfs").resolve()
    if root not in p.parents or not p.exists():
        raise HTTPException(404, "no file")
    if dl:
        # filename= 会带上 Content-Disposition: attachment，强制浏览器下载到磁盘
        return FileResponse(p, media_type="application/pdf", filename=name)
    return FileResponse(p, media_type="application/pdf")


@app.get("/api/jobs/{job_id}/zip")
def api_zip(job_id: str):
    job = mgr.get(job_id)
    if not job:
        raise HTTPException(404, "not found")
    pdfs = (mgr.base / "web_data/jobs" / job_id / "pdfs")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in pdfs.glob("*.pdf"):
            z.write(f, f.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": 'attachment; filename="%s.zip"' % job_id})
