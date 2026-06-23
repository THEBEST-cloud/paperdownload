import argparse
import tempfile
from pathlib import Path

from paperdl.downloader import DownloadContext, run, MAX_PER_RUN
from paperdl.results import ResultStore
from paperdl.session import browser_context, run_login
from paperdl.adapters import springer, elsevier, nature, acs, rsc, wiley, crossref, frontiers, ieee, unpaywall, science, pnas, aims, annualreviews, mdpi
from paperdl.search import get_source
from paperdl.search.base import SearchQuery
from paperdl.search.export import to_doi_list, to_csv, to_bibtex


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="paperdl", description="按 DOI 清单批量下载文献")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="打开浏览器手动登录并保存会话")

    pr = sub.add_parser("run", help="按清单下载")
    pr.add_argument("list", help="DOI 清单文件（txt/csv，每行一个 DOI 或第一列为 DOI）")
    pr.add_argument("--max", type=int, default=MAX_PER_RUN, help="单次上限")
    pr.add_argument("--show", action="store_true", help="显示浏览器窗口(默认无头；仅在有图形界面的机器上可用)")

    sub.add_parser("retry", help="仅重试上次失败的条目")

    sub.add_parser("config", help="交互式配置账号/密钥（.paperdl.env）")
    sub.add_parser("doctor", help="环境/登录/代理自检")

    sp = sub.add_parser("serve", help="启动网页前端")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000)

    ps = sub.add_parser("search", help="按关键词检索文献(OpenAlex)")
    ps.add_argument("query", help="检索关键词")
    ps.add_argument("--from", dest="year_from", type=int, default=None, help="起始年份")
    ps.add_argument("--to", dest="year_to", type=int, default=None, help="结束年份")
    ps.add_argument("--oa", action="store_true", help="仅开放获取")
    ps.add_argument("--sort", choices=["relevance", "cited", "year"], default="relevance")
    ps.add_argument("--type", dest="work_type", default="article", help="文献类型(默认 article)")
    ps.add_argument("-n", "--num", type=int, default=25, help="结果数量(<=200)")
    ps.add_argument("-o", "--out", default=None, help="导出 DOI 清单到文件")
    ps.add_argument("--csv", default=None, help="导出 CSV 到文件")
    ps.add_argument("--bib", default=None, help="导出 BibTeX 到文件")

    return p


# 已注册的适配器
ADAPTERS = {"springer": springer, "elsevier": elsevier, "nature": nature, "acs": acs, "rsc": rsc, "wiley": wiley, "crossref": crossref, "frontiers": frontiers, "ieee": ieee, "unpaywall": unpaywall, "science": science, "pnas": pnas, "aims": aims, "annualreviews": annualreviews, "mdpi": mdpi}


def _do_run(list_path: str, max_per_run: int, show: bool = False) -> None:
    from paperdl.credentials import load_credentials
    store = ResultStore(Path("results.csv"))
    creds = load_credentials()
    cid, pw = creds if creds else (None, None)
    # 有头-Xvfb：让 Nature/ACS 等走机构 Shibboleth 登录、并能过 Cloudflare
    with browser_context(headless=not show, headed_xvfb=not show) as ctx:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        dctx = DownloadContext(page=page, out_dir=Path("downloads"), adapters=ADAPTERS,
                               cid=cid, pw=pw)
        run(Path(list_path), dctx, store, max_per_run=max_per_run)


def _do_search(args) -> None:
    src = get_source()
    page = src.search(SearchQuery(
        query=args.query, year_from=args.year_from, year_to=args.year_to,
        oa_only=args.oa, work_type=args.work_type, sort=args.sort,
        per_page=min(args.num, 200), page=1,
    ))
    papers = page.results
    wrote = False
    if args.out:
        Path(args.out).write_text(to_doi_list(papers), encoding="utf-8")
        print("已写 DOI 清单 → %s (%d 条)" % (args.out, sum(1 for p in papers if p.doi)))
        wrote = True
    if args.csv:
        Path(args.csv).write_text(to_csv(papers), encoding="utf-8")
        print("已写 CSV → %s" % args.csv)
        wrote = True
    if args.bib:
        Path(args.bib).write_text(to_bibtex(papers), encoding="utf-8")
        print("已写 BibTeX → %s" % args.bib)
        wrote = True
    if wrote:
        return
    print("共约 %d 条,显示前 %d:" % (page.total, len(papers)))
    for i, p in enumerate(papers, 1):
        au = (p.authors[0] + " 等") if p.authors else "—"
        oa = "OA" if p.is_oa else "  "
        print("%2d. [%s] %s (%s, %s) 被引%d  %s"
              % (i, oa, p.title[:70], au, p.year or "—", p.cited_by, p.doi or "无DOI"))


def _do_retry() -> None:
    store = ResultStore(Path("results.csv"))
    failed = store.failed_dois()
    if not failed:
        print("没有需要重试的失败条目。")
        return
    tmp = Path(tempfile.mkstemp(suffix=".txt")[1])
    tmp.write_text("\n".join(failed), encoding="utf-8")
    _do_run(str(tmp), max_per_run=len(failed))
    tmp.unlink(missing_ok=True)


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "login":
        run_login()
    elif args.command == "run":
        _do_run(args.list, args.max, args.show)
    elif args.command == "retry":
        _do_retry()
    elif args.command == "config":
        from paperdl.configure import run_config
        run_config()
    elif args.command == "doctor":
        import sys
        from paperdl.doctor import run_doctor
        sys.exit(run_doctor())
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("paperdl.web.app:app", host=args.host, port=args.port)
    elif args.command == "search":
        _do_search(args)


if __name__ == "__main__":
    main()
