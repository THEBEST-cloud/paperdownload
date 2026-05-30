import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from paperdl.adapters.base import Adapter
from paperdl.naming import build_filename
from paperdl.resolver import Metadata, fetch_metadata
from paperdl.dispatch import adapter_key_for
from paperdl.results import ResultRow, ResultStore

DELAY_MIN = 8
DELAY_MAX = 20
MAX_PER_RUN = 50
RETRIES = 2


@dataclass
class DownloadContext:
    page: object
    out_dir: Path
    adapters: Dict[str, Adapter]
    delay_min: float = DELAY_MIN
    delay_max: float = DELAY_MAX


def download_one(md: Metadata, adapter_key: Optional[str], ctx: DownloadContext) -> ResultRow:
    if adapter_key is None or adapter_key not in ctx.adapters:
        return ResultRow(doi=md.doi, publisher=md.publisher, title=md.title,
                         status="failed", reason="no_adapter", file_path="")
    adapter = ctx.adapters[adapter_key]
    result = adapter.download(ctx.page, md)
    if not result.ok:
        return ResultRow(doi=md.doi, publisher=md.publisher, title=md.title,
                         status="failed", reason=result.reason, file_path="")
    ctx.out_dir.mkdir(parents=True, exist_ok=True)
    fname = build_filename(md)
    (ctx.out_dir / fname).write_bytes(result.pdf_bytes)
    return ResultRow(doi=md.doi, publisher=md.publisher, title=md.title,
                     status="success", reason="", file_path=fname)


def read_doi_list(path: Path) -> List[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        doi = line.strip().split(",")[0].strip()  # 容忍 csv：取第一列
        if doi and not doi.lower().startswith("doi"):  # 跳过表头
            out.append(doi)
    return out


def run(list_path: Path, ctx: DownloadContext, store: ResultStore,
        max_per_run: int = MAX_PER_RUN) -> None:
    dois = read_doi_list(list_path)
    done = store.completed_dois()
    todo = [d for d in dois if d not in done]
    if len(todo) > max_per_run:
        print(f"清单 {len(todo)} 篇超过单次上限 {max_per_run}，本次只处理前 {max_per_run} 篇，"
              f"其余请下次再跑（已成功的会自动跳过）。")
        todo = todo[:max_per_run]

    for i, doi in enumerate(todo, 1):
        md = fetch_metadata(doi)
        akey = adapter_key_for(md.publisher, md.doi)
        print(f"[{i}/{len(todo)}] {doi} -> {akey or '无适配器'}  {md.title[:50]}")
        row = None
        for attempt in range(1, RETRIES + 2):
            row = download_one(md, akey, ctx)
            if row.status == "success" or row.reason in ("no_adapter",):
                break
            if attempt <= RETRIES:
                back = 2 ** attempt
                print(f"   失败({row.reason})，{back}s 后重试 {attempt}/{RETRIES}")
                time.sleep(back)
        store.record(row)
        print(f"   => {row.status} {row.reason}")
        if i < len(todo):
            time.sleep(random.uniform(ctx.delay_min, ctx.delay_max))

    rows_done = store.completed_dois()
    print(f"完成。成功累计 {len(rows_done)} 篇；失败明细见 results.csv。")
