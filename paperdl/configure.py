"""交互式配置向导：生成/增量更新 .paperdl.env。绝不内置任何真实值。"""
from pathlib import Path
from typing import Callable, Optional

# (key, required, prompt, help, secret)
ENV_FIELDS = [
    ("CSTCLOUD_ID", True, "中科院通行证账号（邮箱）", "登录 passport.escience.cn 的账号", False),
    ("CSTCLOUD_PASSWORD", True, "通行证密码", "你的通行证密码", True),
    ("ELSEVIER_API_KEY", False, "Elsevier API Key", "dev.elsevier.com 免费申请；留空则 Elsevier 走浏览器", False),
    ("ELSEVIER_INSTTOKEN", False, "Elsevier 机构令牌", "图书馆提供，校外 API 全文用；通常留空", True),
    ("WILEY_TDM_TOKEN", False, "Wiley TDM Token", "Wiley 申请；留空则 Wiley 走浏览器", True),
    ("OPENALEX_MAILTO", False, "OpenAlex 联系邮箱", "检索礼貌池邮箱；留空则自动回退", False),
    ("SMTP_HOST", False, "SMTP 服务器", "如 smtp.qq.com；用邮件发送才填", False),
    ("SMTP_PORT", False, "SMTP 端口", "如 465", False),
    ("SMTP_USER", False, "SMTP 用户名", "你的邮箱", False),
    ("SMTP_PASSWORD", False, "SMTP 授权码", "邮箱 SMTP 授权码（非登录密码）", True),
    ("SMTP_FROM", False, "发件人", "通常同 SMTP_USER", False),
    ("SMTP_SSL", False, "SMTP 是否 SSL(true/false)", "465 端口填 true", False),
]
_KNOWN = [k for k, *_ in ENV_FIELDS]


def parse_env(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip()
    return out


def merge_env(existing: dict, updates: dict) -> dict:
    merged = dict(existing)
    for k, v in updates.items():
        if v != "":
            merged[k] = v
    return merged


def render_env(values: dict) -> str:
    lines = []
    for k in _KNOWN:
        if values.get(k, "") != "":
            lines.append(f"{k}={values[k]}")
    for k in sorted(values):
        if k not in _KNOWN and values[k] != "":
            lines.append(f"{k}={values[k]}")
    return "\n".join(lines) + "\n"


def write_env(path: Path, updates: dict) -> dict:
    existing = parse_env(path.read_text(encoding="utf-8")) if path.exists() else {}
    merged = merge_env(existing, updates)
    path.write_text(render_env(merged), encoding="utf-8")
    try:
        path.chmod(0o600)
    except Exception:
        pass
    return merged


def run_config(base: Optional[Path] = None,
               input_fn: Callable[[str], str] = input,
               getpass_fn: Optional[Callable[[str], str]] = None) -> Path:
    import getpass as _g
    getpass_fn = getpass_fn or _g.getpass
    base = Path(base) if base else Path.cwd()
    path = base / ".paperdl.env"
    existing = parse_env(path.read_text(encoding="utf-8")) if path.exists() else {}
    updates = {}
    print("配置 .paperdl.env（直接回车=跳过/保留原值）。密钥只存本机，不上传。\n")
    for key, required, prompt, help_text, secret in ENV_FIELDS:
        cur = existing.get(key, "")
        tag = "必填" if required else "可选"
        shown = "（已设置）" if (cur and secret) else (f"（当前: {cur}）" if cur else "")
        ask = f"[{tag}] {prompt} — {help_text}{shown}\n> "
        val = (getpass_fn(ask) if secret else input_fn(ask)).strip()
        if not val and required and not cur:
            while not val:
                val = (getpass_fn("  此项必填，请输入: ") if secret
                       else input_fn("  此项必填，请输入: ")).strip()
        if val:
            updates[key] = val
    write_env(path, updates)
    print(f"\n✅ 已写入 {path}（chmod 600）。下一步：paperdl login")
    return path
