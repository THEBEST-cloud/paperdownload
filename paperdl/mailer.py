import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from paperdl.credentials import load_env

DEFAULT_MAX_BYTES = 20 * 1024 * 1024  # 每封邮件附件总大小上限 ~20MB


def plan_batches(sizes, max_bytes=DEFAULT_MAX_BYTES):
    """sizes: list of (name, size_bytes). 贪心打包成多个批次，每批附件总大小<=max_bytes。
    单个超过 max_bytes 的文件单独成一批(oversized,仍会尝试发,可能被服务器拒)。"""
    batches, cur, cur_sz = [], [], 0
    for name, sz in sizes:
        if sz > max_bytes:
            if cur:
                batches.append(cur); cur, cur_sz = [], 0
            batches.append([name])
            continue
        if cur and cur_sz + sz > max_bytes:
            batches.append(cur); cur, cur_sz = [], 0
        cur.append(name); cur_sz += sz
    if cur:
        batches.append(cur)
    return batches


def smtp_config(base=None) -> dict:
    cfg = load_env(base)
    return {
        "host": cfg.get("SMTP_HOST", "") or "",
        "port": int(cfg.get("SMTP_PORT", "465") or "465"),
        "user": cfg.get("SMTP_USER", "") or "",
        "password": cfg.get("SMTP_PASSWORD", "") or "",
        "from_addr": (cfg.get("SMTP_FROM") or cfg.get("SMTP_USER") or ""),
        "ssl": str(cfg.get("SMTP_SSL", "true")).lower() != "false",
    }


def _build_message(from_addr, to, subject, body, pdf_dir, names):
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    for name in names:
        data = (Path(pdf_dir) / name).read_bytes()
        msg.add_attachment(data, maintype="application", subtype="pdf", filename=name)
    return msg


def send_pdfs(pdf_dir, to, subject_prefix="paperdl 文献", max_bytes=DEFAULT_MAX_BYTES,
              cfg=None, smtp_factory=None) -> dict:
    """把 pdf_dir 下所有 .pdf 分批发到 to。smtp_factory 仅供测试注入。"""
    cfg = cfg or smtp_config()
    if not cfg["host"] or not cfg["user"] or not cfg["password"]:
        return {"ok": False, "error": "SMTP 未配置：请在 .paperdl.env 填 SMTP_HOST/SMTP_USER/SMTP_PASSWORD"}
    if not to:
        return {"ok": False, "error": "收件人为空"}
    pdf_dir = Path(pdf_dir)
    files = sorted(pdf_dir.glob("*.pdf"))
    if not files:
        return {"ok": False, "error": "没有可发送的 PDF"}
    sizes = [(f.name, f.stat().st_size) for f in files]
    batches = plan_batches(sizes, max_bytes)

    if smtp_factory is not None:
        server = smtp_factory()
    elif cfg["ssl"]:
        server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ssl.create_default_context(), timeout=60)
    else:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=60)
        server.starttls(context=ssl.create_default_context())
    sent = 0
    try:
        server.login(cfg["user"], cfg["password"])
        for i, names in enumerate(batches, 1):
            subject = "%s (%d/%d)" % (subject_prefix, i, len(batches))
            body = "共 %d 篇 PDF，分 %d 封发送，本封 %d 篇。\n\n— paperdl" % (len(files), len(batches), len(names))
            msg = _build_message(cfg["from_addr"], to, subject, body, pdf_dir, names)
            server.send_message(msg)
            sent += 1
    finally:
        try:
            server.quit()
        except Exception:
            pass
    return {"ok": True, "emails": sent, "files": len(files), "batches": len(batches)}
