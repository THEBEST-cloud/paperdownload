import json
import queue
import shutil
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from paperdl.downloader import DownloadContext, run as run_download
from paperdl.results import ResultStore
from paperdl.session import browser_context
from paperdl.cli import ADAPTERS

WEB_DATA = Path("web_data/jobs")


@dataclass
class JobItem:
    doi: str
    status: str = "pending"
    reason: str = ""
    title: str = ""
    publisher: str = ""
    file: str = ""


@dataclass
class Job:
    id: str
    created_at: str
    dois: list
    delay_min: float = 8.0
    delay_max: float = 20.0
    status: str = "queued"   # queued | running | done | error
    total: int = 0
    done: int = 0
    success: int = 0
    failed: int = 0
    current: str = ""
    owner: str = ""
    items: dict = field(default_factory=dict)   # doi -> JobItem(as dict)

    def to_public(self) -> dict:
        d = asdict(self)
        d["items"] = list(self.items.values())
        return d


class JobManager:
    def __init__(self, base: Optional[Path] = None):
        self.base = Path(base) if base else Path.cwd()
        self._jobs = {}
        self._lock = threading.Lock()
        (self.base / WEB_DATA).mkdir(parents=True, exist_ok=True)
        self._load_history()
        self._queue: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _jobs_root(self) -> Path:
        return self.base / WEB_DATA

    def _load_history(self):
        for jd in sorted(self._jobs_root().glob("*/job.json")):
            try:
                data = json.loads(jd.read_text(encoding="utf-8"))
                job = Job(
                    id=data["id"],
                    created_at=data["created_at"],
                    dois=data.get("dois", []),
                )
                for k in ("delay_min", "delay_max", "status", "total", "done", "success", "failed", "current", "owner"):
                    if k in data:
                        setattr(job, k, data[k])
                job.items = {it["doi"]: it for it in data.get("items", [])}
                # 历史里仍标 running 或 queued 的（上次中断）改为 done
                if job.status in ("running", "queued"):
                    job.status = "done"
                self._jobs[job.id] = job
            except Exception:
                continue

    def _persist(self, job: "Job"):
        d = self.base / WEB_DATA / job.id
        d.mkdir(parents=True, exist_ok=True)
        data = asdict(job)
        data["items"] = list(job.items.values())
        (d / "job.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def create(self, job_id: str, created_at: str, dois: list, delay_min=8.0, delay_max=20.0, owner: str = "") -> "Job":
        job = Job(id=job_id, created_at=created_at, dois=list(dois),
                  delay_min=delay_min, delay_max=delay_max, total=len(dois),
                  status="queued", owner=owner)
        for doi in dois:
            job.items[doi] = asdict(JobItem(doi=doi))
        with self._lock:
            self._jobs[job.id] = job
        self._persist(job)
        return job

    def get(self, job_id: str) -> Optional["Job"]:
        return self._jobs.get(job_id)

    def list(self, owner: Optional[str] = None) -> list:
        jobs = self._jobs.values()
        if owner is not None:
            jobs = [j for j in jobs if j.owner == owner]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def start(self, job: "Job", only_dois: Optional[list] = None):
        job.status = "queued"
        self._persist(job)
        self._queue.put((job, only_dois))

    def delete(self, job_id: str) -> bool:
        with self._lock:
            if job_id not in self._jobs:
                return False
            del self._jobs[job_id]
        shutil.rmtree(self.base / WEB_DATA / job_id, ignore_errors=True)
        return True

    def _worker_loop(self):
        while True:
            job, only = self._queue.get()
            try:
                self._run(job, only)
            finally:
                self._queue.task_done()

    def _run(self, job: "Job", only_dois):
        try:
            d = self.base / WEB_DATA / job.id
            (d / "pdfs").mkdir(parents=True, exist_ok=True)
            todo = only_dois if only_dois is not None else job.dois
            list_path = d / "dois.txt"
            list_path.write_text("\n".join(todo) + "\n", encoding="utf-8")
            store = ResultStore(d / "results.csv")
            job.status = "running"

            def progress(i, total, row):
                it = job.items.get(row.doi) or asdict(JobItem(doi=row.doi))
                it["status"] = row.status
                it["reason"] = row.reason
                it["title"] = row.title
                it["publisher"] = row.publisher
                it["file"] = row.file_path
                job.items[row.doi] = it
                job.current = row.doi
                job.done = sum(1 for x in job.items.values() if x["status"] in ("success", "failed"))
                job.success = sum(1 for x in job.items.values() if x["status"] == "success")
                job.failed = sum(1 for x in job.items.values() if x["status"] == "failed")
                self._persist(job)

            from paperdl.credentials import load_credentials
            creds = load_credentials(self.base)
            cid, pw = creds if creds else (None, None)
            # 有头-Xvfb：让 Nature/ACS 等走机构 Shibboleth 登录、并能过 Cloudflare
            with browser_context(headless=False, headed_xvfb=True, base=self.base) as ctx:
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                dctx = DownloadContext(page=page, out_dir=d / "pdfs", adapters=ADAPTERS,
                                       delay_min=job.delay_min, delay_max=job.delay_max,
                                       cid=cid, pw=pw)
                run_download(list_path, dctx, store, max_per_run=10**9, progress=progress)
            job.status = "done"
            job.current = ""
            self._persist(job)
        except Exception as e:
            job.status = "error"
            job.current = "ERROR: %s" % e
            self._persist(job)
