import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response, Cookie, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from paperdl.extract import extract_dois_from_text, extract_dois_from_excel
from paperdl.dispatch import adapter_key_for
from paperdl.web.jobs import JobManager
from paperdl.web.auth import Auth
from paperdl.mailer import send_pdfs
from dataclasses import asdict
from paperdl.search import get_source
from paperdl.search.base import SearchQuery
from paperdl.search.base import Paper
from paperdl.search.export import to_doi_list, to_csv, to_bibtex

app = FastAPI(title="paperdl")
mgr = JobManager()
auth = Auth()
STATIC = Path(__file__).parent / "static"

_counter = [0]


def _new_id() -> str:
    _counter[0] += 1
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-%d" % _counter[0]


def current_user(sid: str = Cookie(default=None)) -> str:
    u = auth.user_for_sid(sid)
    if not u:
        raise HTTPException(401, "未登录")
    return u


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


# ── Auth endpoints (no login required) ──────────────────────────────────────

@app.post("/api/register")
def api_register(payload: dict):
    ok, msg = auth.register(payload.get("username", ""), payload.get("password", ""))
    if not ok:
        raise HTTPException(400, msg)
    return {"ok": True}


@app.post("/api/login")
def api_login(payload: dict, response: Response):
    sid = auth.login(payload.get("username", ""), payload.get("password", ""))
    if not sid:
        raise HTTPException(401, "用户名或密码错误")
    response.set_cookie("sid", sid, httponly=True, max_age=7 * 24 * 3600, samesite="lax")
    return {"ok": True, "user": payload.get("username", "").strip()}


@app.post("/api/logout")
def api_logout(response: Response, sid: str = Cookie(default=None)):
    auth.logout(sid)
    response.delete_cookie("sid")
    return {"ok": True}


@app.get("/api/me")
def api_me(user: str = Depends(current_user)):
    return {"user": user}


# ── Job endpoints (login required) ──────────────────────────────────────────

@app.post("/api/extract")
async def api_extract(file: UploadFile = File(None), text: str = Form(None),
                      user: str = Depends(current_user)):
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
async def api_create_job(payload: dict, user: str = Depends(current_user)):
    dois = payload.get("dois") or []
    if not dois:
        raise HTTPException(400, "no dois")
    job = mgr.create(_new_id(), datetime.now(timezone.utc).isoformat(), dois,
                     delay_min=float(payload.get("delay_min", 8)),
                     delay_max=float(payload.get("delay_max", 20)),
                     owner=user)
    mgr.start(job)
    return {"job_id": job.id}


@app.get("/api/jobs")
def api_list_jobs(user: str = Depends(current_user)):
    return [{"id": j.id, "created_at": j.created_at, "total": j.total,
             "success": j.success, "failed": j.failed, "status": j.status} for j in mgr.list(owner=user)]


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str, user: str = Depends(current_user)):
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    return job.to_public()


@app.post("/api/jobs/{job_id}/retry")
def api_retry(job_id: str, user: str = Depends(current_user)):
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    failed = [doi for doi, it in job.items.items() if it["status"] == "failed"]
    if not failed:
        return {"retrying": 0}
    mgr.start(job, only_dois=failed)
    return {"retrying": len(failed)}


@app.post("/api/jobs/{job_id}/resume")
def api_resume(job_id: str, user: str = Depends(current_user)):
    """续跑未完成的任务：处理所有 pending(被打断没跑到的) + failed 条目。"""
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    if job.status in ("running", "queued"):
        raise HTTPException(409, "任务正在运行")
    todo = [doi for doi, it in job.items.items()
            if it["status"] in ("pending", "failed")]
    if not todo:
        return {"resuming": 0}
    mgr.start(job, only_dois=todo)
    return {"resuming": len(todo)}


@app.post("/api/jobs/{job_id}/retry-item")
def api_retry_item(job_id: str, payload: dict, user: str = Depends(current_user)):
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    if job.status == "running":
        raise HTTPException(409, "任务正在运行，请稍候")
    doi = (payload.get("doi") or "").strip()
    if doi not in job.items:
        raise HTTPException(404, "该 DOI 不在此任务中")
    mgr.start(job, only_dois=[doi])
    return {"retrying": 1, "doi": doi}


@app.get("/api/jobs/{job_id}/file")
def api_file(job_id: str, name: str, dl: int = 0, user: str = Depends(current_user)):
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    p = (mgr.base / "web_data/jobs" / job_id / "pdfs" / name).resolve()
    root = (mgr.base / "web_data/jobs" / job_id / "pdfs").resolve()
    if root not in p.parents or not p.exists():
        raise HTTPException(404, "no file")
    if dl:
        # filename= 会带上 Content-Disposition: attachment，强制浏览器下载到磁盘
        return FileResponse(p, media_type="application/pdf", filename=name)
    return FileResponse(p, media_type="application/pdf")


@app.post("/api/jobs/{job_id}/email")
def api_email(job_id: str, payload: dict, user: str = Depends(current_user)):
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    to = (payload.get("to") or "").strip()
    if not to:
        raise HTTPException(400, "收件人为空")
    pdf_dir = mgr.base / "web_data/jobs" / job_id / "pdfs"
    res = send_pdfs(pdf_dir, to, subject_prefix="paperdl 文献 [%s]" % job_id)
    return res


@app.get("/api/jobs/{job_id}/zip")
def api_zip(job_id: str, user: str = Depends(current_user)):
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    pdfs = (mgr.base / "web_data/jobs" / job_id / "pdfs")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in pdfs.glob("*.pdf"):
            z.write(f, f.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": 'attachment; filename="%s.zip"' % job_id})


@app.delete("/api/jobs/{job_id}")
def api_delete_job(job_id: str, user: str = Depends(current_user)):
    job = mgr.get(job_id)
    if not job or job.owner != user:
        raise HTTPException(404, "not found")
    mgr.delete(job_id)
    return {"ok": True}


# ── Search endpoints (login required) ───────────────────────────────────────

@app.get("/api/search")
def api_search(q: str, year_from: int = None, year_to: int = None,
               oa: bool = False, sort: str = "relevance", type: str = "article",
               page: int = 1, per_page: int = 25, user: str = Depends(current_user)):
    src = get_source()
    sp = src.search(SearchQuery(query=q, year_from=year_from, year_to=year_to,
                                oa_only=oa, work_type=type, sort=sort,
                                page=page, per_page=min(per_page, 200)))
    return {"results": [asdict(p) for p in sp.results],
            "total": sp.total, "page": sp.page, "per_page": sp.per_page}


@app.post("/api/search/export")
def api_search_export(payload: dict, user: str = Depends(current_user)):
    rows = payload.get("papers") or []
    papers = [Paper(**{k: r.get(k) for k in
                       ("title", "authors", "year", "venue", "doi",
                        "cited_by", "is_oa", "abstract", "type", "oa_url")
                       if r.get(k) is not None}) for r in rows]
    fmt = payload.get("format", "doi")
    if fmt == "csv":
        body, media, name = to_csv(papers), "text/csv", "papers.csv"
    elif fmt == "bib":
        body, media, name = to_bibtex(papers), "text/plain", "papers.bib"
    else:
        body, media, name = to_doi_list(papers), "text/plain", "dois.txt"
    return Response(content=body, media_type=media,
                    headers={"Content-Disposition": 'attachment; filename="%s"' % name})


@app.post("/api/search/download")
def api_search_download(payload: dict, user: str = Depends(current_user)):
    dois = [d for d in (payload.get("dois") or []) if d]
    if not dois:
        raise HTTPException(400, "no dois")
    job = mgr.create(_new_id(), datetime.now(timezone.utc).isoformat(), dois, owner=user)
    mgr.start(job)
    return {"job_id": job.id}
