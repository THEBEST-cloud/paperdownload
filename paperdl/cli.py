import argparse
import tempfile
from pathlib import Path

from paperdl.downloader import DownloadContext, run, MAX_PER_RUN
from paperdl.results import ResultStore
from paperdl.session import browser_context, run_login
from paperdl.adapters import springer, elsevier, nature, acs, rsc, wiley, crossref, frontiers, ieee, unpaywall, science, pnas, aims


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="paperdl", description="按 DOI 清单批量下载文献")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="打开浏览器手动登录并保存会话")

    pr = sub.add_parser("run", help="按清单下载")
    pr.add_argument("list", help="DOI 清单文件（txt/csv，每行一个 DOI 或第一列为 DOI）")
    pr.add_argument("--max", type=int, default=MAX_PER_RUN, help="单次上限")
    pr.add_argument("--show", action="store_true", help="显示浏览器窗口(默认无头；仅在有图形界面的机器上可用)")

    sub.add_parser("retry", help="仅重试上次失败的条目")

    sp = sub.add_parser("serve", help="启动网页前端")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000)

    return p


# 已注册的适配器
ADAPTERS = {"springer": springer, "elsevier": elsevier, "nature": nature, "acs": acs, "rsc": rsc, "wiley": wiley, "crossref": crossref, "frontiers": frontiers, "ieee": ieee, "unpaywall": unpaywall, "science": science, "pnas": pnas, "aims": aims}


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
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("paperdl.web.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
