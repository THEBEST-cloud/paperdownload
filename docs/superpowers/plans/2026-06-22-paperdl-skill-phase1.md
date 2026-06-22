# paperdl Skill 阶段一 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 paperdl 加 `config`/`doctor` 子命令、干净打包、并脱敏打包成 Claude Code skill + Codex 包，让同事一键装、自己配账号、自检、跑下载。

**Architecture:** 在现有 argparse CLI 上加两个子命令（纯函数 + 薄交互层，便于 TDD）；加 `pyproject.toml` 提供 `paperdl` 控制台入口与 `setup.sh`；一个打包脚本把脱敏源码 + `SKILL.md`/`AGENTS.md`/references 组装到目标目录。只服务中科院 CSTCloud，不做通用化。

**Tech Stack:** Python 3.10+，argparse，pytest，setuptools，patchright/httpx/fastapi（已有）。

## Global Constraints

- 只服务中科院 CSTCloud 通行证；不做 CARSI/EZProxy/通用化/arXiv/搜索/Sci-Hub。
- **绝不把任何真实密钥/会话打进包**：`.paperdl.env`、`.profile/`、`downloads/`、`web_data/`、`results.csv` 等永不进 skill 包。
- 测试用 `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest`，仓库根目录运行。
- 现有 145 个测试必须保持通过；新代码遵循现有风格（中文注释、小文件、纯函数可测）。
- 提交信息结尾加：`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 文件结构

- `paperdl/configure.py`（新）：`.paperdl.env` 解析/合并/渲染/写入 + 交互向导。
- `paperdl/doctor.py`（新）：各项自检函数 + `run_doctor`。
- `paperdl/cli.py`（改）：注册 `config`/`doctor` 子命令并分发。
- `pyproject.toml`（新）：控制台入口 + 依赖。
- `scripts/setup.sh`（新）：建 venv + 装包 + 装 chromium + 查 xvfb。
- `scripts/make_skill.py`（新）：脱敏打包成 skill/Codex 包。
- `skill/SKILL.md`、`skill/AGENTS.md`、`skill/references/{env.example,troubleshooting.md,codex-mcp.toml}`（新）：随包文档。
- `tests/test_configure.py`、`tests/test_doctor.py`、`tests/test_make_skill.py`（新）。

---

### Task 1: `paperdl config` 配置向导

**Files:**
- Create: `paperdl/configure.py`
- Create: `tests/test_configure.py`
- Modify: `paperdl/cli.py`（`build_parser` 加 `config` 子命令；`main` 加分发）

**Interfaces:**
- Produces:
  - `ENV_FIELDS: list[tuple[str,bool,str,str,bool]]`（key, required, prompt, help, secret）
  - `parse_env(text: str) -> dict`
  - `merge_env(existing: dict, updates: dict) -> dict`（updates 中空串不覆盖）
  - `render_env(values: dict) -> str`
  - `write_env(path: Path, updates: dict) -> dict`（合并已有、写入、chmod 600，返回合并后 dict）
  - `run_config(base=None, input_fn=input, getpass_fn=None) -> Path`

- [ ] **Step 1: 写失败测试**

`tests/test_configure.py`：
```python
from pathlib import Path
from paperdl.configure import parse_env, merge_env, render_env, write_env, ENV_FIELDS, run_config


def test_parse_env_basic():
    d = parse_env("A=1\n# c\nB = two \n\nbad\n")
    assert d == {"A": "1", "B": "two"}


def test_merge_env_updates_nonblank_preserves_existing():
    assert merge_env({"A": "1", "B": "2"}, {"B": "9", "C": "3"}) == {"A": "1", "B": "9", "C": "3"}


def test_merge_env_blank_does_not_overwrite():
    assert merge_env({"A": "1"}, {"A": ""}) == {"A": "1"}


def test_render_env_roundtrip_known_order():
    text = render_env({"CSTCLOUD_PASSWORD": "p", "CSTCLOUD_ID": "x@y"})
    # CSTCLOUD_ID 在 ENV_FIELDS 里排在 PASSWORD 之前，渲染应保持该顺序
    assert text.index("CSTCLOUD_ID=") < text.index("CSTCLOUD_PASSWORD=")
    assert parse_env(text) == {"CSTCLOUD_ID": "x@y", "CSTCLOUD_PASSWORD": "p"}


def test_write_env_creates_merges_and_chmods(tmp_path):
    p = tmp_path / ".paperdl.env"
    p.write_text("CSTCLOUD_ID=old@x\nELSEVIER_API_KEY=k\n", encoding="utf-8")
    write_env(p, {"CSTCLOUD_ID": "new@x", "CSTCLOUD_PASSWORD": "pw"})
    d = parse_env(p.read_text(encoding="utf-8"))
    assert d["CSTCLOUD_ID"] == "new@x"        # 更新
    assert d["CSTCLOUD_PASSWORD"] == "pw"      # 新增
    assert d["ELSEVIER_API_KEY"] == "k"        # 保留
    assert (p.stat().st_mode & 0o777) == 0o600


def test_run_config_collects_required(tmp_path):
    answers = iter(["acct@cas.cn"])          # 非密钥项的 input
    secrets = iter(["secretpw"])             # 密钥项的 getpass（CSTCLOUD_PASSWORD）
    # 其余可选项一律回车跳过
    def inp(prompt):
        if "通行证账号" in prompt:
            return next(answers)
        return ""
    def gp(prompt):
        if "通行证密码" in prompt:
            return next(secrets)
        return ""
    run_config(base=tmp_path, input_fn=inp, getpass_fn=gp)
    d = parse_env((tmp_path / ".paperdl.env").read_text(encoding="utf-8"))
    assert d["CSTCLOUD_ID"] == "acct@cas.cn"
    assert d["CSTCLOUD_PASSWORD"] == "secretpw"
    assert "ELSEVIER_API_KEY" not in d        # 跳过的可选项不写
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest tests/test_configure.py -q`
Expected: FAIL（ModuleNotFoundError: paperdl.configure）

- [ ] **Step 3: 写实现 `paperdl/configure.py`**

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest tests/test_configure.py -q`
Expected: PASS（6 passed）

- [ ] **Step 5: 接进 CLI**

`paperdl/cli.py` — `build_parser()` 里 `sub.add_parser("retry", ...)` 之后加：
```python
    sub.add_parser("config", help="交互式配置账号/密钥（.paperdl.env）")
    sub.add_parser("doctor", help="环境/登录/代理自检")
```
`main()` 里 `elif args.command == "retry":` 分支之后加：
```python
    elif args.command == "config":
        from paperdl.configure import run_config
        run_config()
    elif args.command == "doctor":
        import sys
        from paperdl.doctor import run_doctor
        sys.exit(run_doctor())
```
（`doctor` 实现见 Task 2；本步先加分发，doctor 模块下个任务建。若现在跑 `paperdl doctor` 会 ImportError，属正常，Task 2 补上。）

- [ ] **Step 6: 验证 config 子命令存在 + 全量测试**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m paperdl config --help && /home/hoo/.conda/envs/res-agent/bin/python3 -m pytest -q`
Expected: 显示 config 帮助；测试全 PASS（原有 + 新 6 个）

- [ ] **Step 7: 提交**

```bash
git add paperdl/configure.py tests/test_configure.py paperdl/cli.py
git commit -m "feat: paperdl config 交互式配置向导(.paperdl.env)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `paperdl doctor` 自检

**Files:**
- Create: `paperdl/doctor.py`
- Create: `tests/test_doctor.py`
- （cli.py 的 doctor 分发已在 Task 1 Step 5 加好）

**Interfaces:**
- Consumes: `paperdl.configure.parse_env`
- Produces:
  - `Check`（dataclass: name:str, status:"ok"|"warn"|"fail", detail:str）
  - `check_deps()`, `check_chromium()`, `check_xvfb()`,
    `check_env(base: Path)`, `check_proxy_env(environ: dict|None=None)`, `check_login(base: Path)` → 均返回 `Check`
  - `run_doctor(base=None) -> int`（打印 + 返回退出码：有 fail 返回 1，否则 0）

- [ ] **Step 1: 写失败测试**

`tests/test_doctor.py`：
```python
import shutil
from pathlib import Path
import paperdl.doctor as doc


def test_check_proxy_env_warns_when_set():
    c = doc.check_proxy_env({"https_proxy": "http://127.0.0.1:7897"})
    assert c.status == "warn"


def test_check_proxy_env_ok_when_clean():
    assert doc.check_proxy_env({}).status == "ok"


def test_check_env_missing_file(tmp_path):
    assert doc.check_env(tmp_path).status == "fail"


def test_check_env_missing_required(tmp_path):
    (tmp_path / ".paperdl.env").write_text("ELSEVIER_API_KEY=k\n", encoding="utf-8")
    assert doc.check_env(tmp_path).status == "fail"


def test_check_env_ok(tmp_path):
    (tmp_path / ".paperdl.env").write_text("CSTCLOUD_ID=a@b\nCSTCLOUD_PASSWORD=p\n", encoding="utf-8")
    assert doc.check_env(tmp_path).status == "ok"


def test_check_xvfb_uses_which(monkeypatch):
    monkeypatch.setattr(doc.shutil, "which", lambda n: "/usr/bin/Xvfb")
    assert doc.check_xvfb().status == "ok"
    monkeypatch.setattr(doc.shutil, "which", lambda n: None)
    assert doc.check_xvfb().status == "fail"


def test_run_doctor_returns_int(tmp_path):
    rc = doc.run_doctor(base=tmp_path)
    assert isinstance(rc, int)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest tests/test_doctor.py -q`
Expected: FAIL（ModuleNotFoundError: paperdl.doctor）

- [ ] **Step 3: 写实现 `paperdl/doctor.py`**

```python
"""一键自检：依赖/chromium/xvfb/.paperdl.env/代理/登录态。"""
import importlib.util
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Check:
    name: str
    status: str  # "ok" | "warn" | "fail"
    detail: str


def check_deps() -> Check:
    missing = [m for m in ("patchright", "httpx", "fastapi", "uvicorn")
               if importlib.util.find_spec(m) is None]
    if missing:
        return Check("Python 依赖", "fail", "缺少: " + ", ".join(missing) + "（跑 scripts/setup.sh）")
    return Check("Python 依赖", "ok", "patchright/httpx/fastapi/uvicorn 已装")


def check_chromium() -> Check:
    try:
        from patchright.sync_api import sync_playwright
        p = sync_playwright().start()
        try:
            exe = p.chromium.executable_path
        finally:
            p.stop()
        if exe and Path(exe).exists():
            return Check("patchright chromium", "ok", exe)
        return Check("patchright chromium", "fail", "未安装（patchright install chromium）")
    except Exception as e:
        return Check("patchright chromium", "fail", str(e)[:70])


def check_xvfb() -> Check:
    path = shutil.which("Xvfb")
    if path:
        return Check("Xvfb", "ok", path)
    return Check("Xvfb", "fail", "未安装（sudo apt install -y xvfb）")


def check_env(base: Path) -> Check:
    from paperdl.configure import parse_env
    p = Path(base) / ".paperdl.env"
    if not p.exists():
        return Check(".paperdl.env", "fail", "不存在（跑 paperdl config）")
    d = parse_env(p.read_text(encoding="utf-8"))
    missing = [k for k in ("CSTCLOUD_ID", "CSTCLOUD_PASSWORD") if not d.get(k)]
    if missing:
        return Check(".paperdl.env", "fail", "缺必填: " + ", ".join(missing))
    return Check(".paperdl.env", "ok", "通行证账号已配")


def check_proxy_env(environ: Optional[dict] = None) -> Check:
    environ = environ if environ is not None else os.environ
    leaked = sorted({v.lower() for v in ("http_proxy", "https_proxy", "all_proxy",
                                         "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
                     if environ.get(v)})
    if leaked:
        return Check("代理环境变量", "warn",
                     "检测到 " + ",".join(leaked) +
                     "：会让浏览器走境外、破坏通行证/Shibboleth 登录，建议 unset")
    return Check("代理环境变量", "ok", "无代理泄漏（机构访问靠 Shibboleth 非 IP）")


def check_login(base: Path) -> Check:
    prof = Path(base) / ".profile"
    if prof.exists() and any(prof.iterdir()):
        return Check("登录态", "ok", ".profile 存在（约 10 天有效）")
    return Check("登录态", "warn", "未登录（跑 paperdl login 完成一次性短信验证）")


def run_doctor(base: Optional[Path] = None) -> int:
    base = Path(base) if base else Path.cwd()
    checks: List[Check] = [
        check_deps(), check_chromium(), check_xvfb(),
        check_env(base), check_proxy_env(), check_login(base),
    ]
    icon = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
    for c in checks:
        print(f"{icon[c.status]} {c.name}: {c.detail}")
    failed = sum(1 for c in checks if c.status == "fail")
    print("\n" + ("全部通过" if failed == 0 else f"{failed} 项需处理"))
    return 1 if failed else 0
```

- [ ] **Step 4: 跑测试确认通过**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest tests/test_doctor.py -q`
Expected: PASS（7 passed）

- [ ] **Step 5: 验证 doctor 子命令 + 全量测试**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m paperdl doctor; /home/hoo/.conda/envs/res-agent/bin/python3 -m pytest -q`
Expected: 打印 6 行自检结果；pytest 全 PASS

- [ ] **Step 6: 提交**

```bash
git add paperdl/doctor.py tests/test_doctor.py
git commit -m "feat: paperdl doctor 环境/登录/代理自检

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 打包（pyproject）+ 一键 setup

**Files:**
- Create: `pyproject.toml`
- Create: `scripts/setup.sh`

**Interfaces:**
- Produces: 控制台入口 `paperdl`（= `paperdl.cli:main`）；`scripts/setup.sh` 一键装好可运行环境。

- [ ] **Step 1: 写 `pyproject.toml`**

```toml
[project]
name = "paperdl"
version = "0.1.0"
description = "按 DOI 批量下载文献（中科院 CSTCloud + Shibboleth + patchright）"
requires-python = ">=3.10"
dependencies = [
    "playwright>=1.44",
    "patchright>=1.50",
    "httpx>=0.27",
    "fastapi>=0.110",
    "uvicorn>=0.29",
    "python-multipart>=0.0.9",
    "openpyxl>=3.1",
    "xlrd>=2.0.1",
    "pandas>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
paperdl = "paperdl.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["paperdl*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 写 `scripts/setup.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

echo "[1/4] 建虚拟环境 .venv ..."
[ -d .venv ] || "$PY" -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate

echo "[2/4] 安装 paperdl 及依赖 ..."
pip install -q -U pip
pip install -q -e .

echo "[3/4] 安装 patchright chromium ..."
patchright install chromium

echo "[4/4] 检查 Xvfb ..."
if command -v Xvfb >/dev/null 2>&1; then
  echo "  Xvfb OK"
else
  echo "  ⚠️ 未装 Xvfb：sudo apt-get install -y xvfb"
fi

echo
echo "完成。下一步：.venv/bin/paperdl config   然后   .venv/bin/paperdl login"
```

- [ ] **Step 3: 标记可执行**

Run: `chmod +x scripts/setup.sh`

- [ ] **Step 4: 冒烟验证打包（用现有 env，不建新 venv）**

Run:
```bash
/home/hoo/.conda/envs/res-agent/bin/python3 -m pip install -e . -q && \
/home/hoo/.conda/envs/res-agent/bin/paperdl --help | grep -E "config|doctor"
```
Expected: 安装成功；`--help` 中能看到 config 与 doctor 子命令

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml scripts/setup.sh
git commit -m "build: pyproject 控制台入口 + 一键 setup.sh

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 脱敏打包成 skill / Codex 包

**Files:**
- Create: `scripts/make_skill.py`
- Create: `tests/test_make_skill.py`
- Create: `skill/SKILL.md`、`skill/AGENTS.md`
- Create: `skill/references/env.example`、`skill/references/troubleshooting.md`、`skill/references/codex-mcp.toml`

**Interfaces:**
- Produces:
  - `make_skill.APP_INCLUDE: tuple[str,...]`（白名单：进 app/ 的顶层项）
  - `make_skill.build_app(repo: Path, app_dest: Path) -> None`（白名单拷贝 + 跳过 __pycache__/.pyc）
  - `make_skill.build_skill(repo: Path, dest: Path) -> None`（app/ + skill 文档）

- [ ] **Step 1: 写失败测试**

`tests/test_make_skill.py`：
```python
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "make_skill", Path(__file__).resolve().parents[1] / "scripts" / "make_skill.py")
make_skill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_skill)


def _fake_repo(root: Path):
    (root / "paperdl").mkdir(parents=True)
    (root / "paperdl" / "cli.py").write_text("x=1\n")
    (root / "paperdl" / "__pycache__").mkdir()
    (root / "paperdl" / "__pycache__" / "cli.pyc").write_text("junk")
    (root / "pyproject.toml").write_text("[project]\n")
    # 隐私/产物：绝不能进包
    (root / ".paperdl.env").write_text("CSTCLOUD_PASSWORD=secret\n")
    (root / ".profile").mkdir()
    (root / ".profile" / "state").write_text("session")
    (root / "web_data").mkdir()
    (root / "web_data" / "users.json").write_text("{}")
    (root / "results.csv").write_text("doi\n")


def test_build_app_includes_source_excludes_secrets(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir()
    _fake_repo(repo)
    dest = tmp_path / "out"
    make_skill.build_app(repo, dest)
    assert (dest / "paperdl" / "cli.py").exists()
    assert (dest / "pyproject.toml").exists()
    # 脱敏：以下一律不存在
    assert list(dest.rglob(".paperdl.env")) == []
    assert list(dest.rglob("state")) == []          # .profile 内容
    assert list(dest.rglob("users.json")) == []
    assert list(dest.rglob("results.csv")) == []
    assert list(dest.rglob("*.pyc")) == []          # 跳过缓存
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest tests/test_make_skill.py -q`
Expected: FAIL（make_skill 无 build_app）

- [ ] **Step 3: 写实现 `scripts/make_skill.py`**

```python
"""把仓库脱敏打包成 Claude Code skill / Codex 包到目标目录。

用白名单（只拷运行所需）确保隐私/产物永不进包：根目录的 .paperdl.env/.profile/
web_data/downloads/results.csv 都不在白名单里，自然被排除。
"""
import shutil
import sys
from pathlib import Path

# 只把运行所需的顶层项拷进 app/
APP_INCLUDE = ("paperdl", "tests", "scripts", "pyproject.toml", "requirements.txt")
# 树内仍要跳过的
_SKIP_NAMES = {"__pycache__", ".pytest_cache"}
_SKIP_SUFFIX = {".pyc"}


def _scrub_copy(src_root: Path, dst_root: Path) -> None:
    for src in src_root.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)
        if any(part in _SKIP_NAMES for part in rel.parts):
            continue
        if src.suffix in _SKIP_SUFFIX:
            continue
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def build_app(repo: Path, app_dest: Path) -> None:
    app_dest.mkdir(parents=True, exist_ok=True)
    for item in APP_INCLUDE:
        src = repo / item
        if not src.exists():
            continue
        if src.is_dir():
            _scrub_copy(src, app_dest / item)
        else:
            shutil.copy2(src, app_dest / item)


def build_skill(repo: Path, dest: Path) -> None:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    build_app(repo, dest / "app")
    skilldir = repo / "skill"
    for name in ("SKILL.md", "AGENTS.md"):
        src = skilldir / name
        if src.exists():
            shutil.copy2(src, dest / name)
    refs = skilldir / "references"
    if refs.exists():
        shutil.copytree(refs, dest / "references", dirs_exist_ok=True)


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    dest = (Path(sys.argv[1]).expanduser() if len(sys.argv) > 1
            else Path.home() / ".claude" / "skills" / "paperdl")
    build_skill(repo, dest)
    print(f"已生成 skill 到 {dest}")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest tests/test_make_skill.py -q`
Expected: PASS

- [ ] **Step 5: 写 `skill/references/env.example`（带注释、无值）**

```bash
# paperdl 配置（每人填自己的；本文件可被 paperdl config 自动生成）
# —— 必填：中科院通行证 ——
CSTCLOUD_ID=
CSTCLOUD_PASSWORD=
# —— 可选：Elsevier（留空则走浏览器 Shibboleth）——
ELSEVIER_API_KEY=
ELSEVIER_INSTTOKEN=
# —— 可选：Wiley（留空则走浏览器 Shibboleth）——
WILEY_TDM_TOKEN=
# —— 可选：邮件发送 ——
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_SSL=
```

- [ ] **Step 6: 写 `skill/references/codex-mcp.toml`（阶段二 MCP 用，先放占位说明）**

```toml
# 把以下片段加入 ~/.codex/config.toml 即可让 Codex 调用 paperdl 的 MCP 工具
# （需先完成阶段二的 `paperdl mcp`；阶段一用 AGENTS.md + CLI 即可，无需本段）
# [mcp_servers.paperdl]
# command = "paperdl"      # 或 .venv/bin/paperdl 的绝对路径
# args = ["mcp"]
```

- [ ] **Step 7: 写 `skill/references/troubleshooting.md`**

内容（实打实，按本仓库经验整理）必须覆盖这些条目，每条一段：
  - **代理坑**：环境变量 http_proxy/https_proxy/all_proxy 会让浏览器走境外 → 通行证按陌生境外设备拦、短信不达、机构权限认不出。跑前 `unset`；`paperdl doctor` 会检测。
  - **一次性短信绑定**：陌生设备首次 `paperdl login` 会要求绑手机+短信；绑过后 .profile 受信任约 10 天。
  - **Elsevier/ScienceDirect 限流**：短时间反复下同一篇会触发风控、返回空壳页（elsevier_preview）；保持默认限速 8–20s/篇、别反复重试，等几十分钟到几小时自动恢复。
  - **被打断后续跑**：网页端任务被中断后用「继续下载」补 pending；CLI 用 `paperdl retry` 补失败。
  - **Shibboleth 偶发卡 IdP**：ACS/Atypon 的 SSO 偶尔卡在 IdP，已内置重建会话重试；仍失败就手动重试该篇。
  - **xvfb/有头浏览器**：无图形界面机器需 Xvfb（`paperdl doctor` 检测）；patchright 用自带 chromium 过 Cloudflare。

- [ ] **Step 8: 写 `skill/SKILL.md`（Claude Code 入口，借鉴 scansci 结构）**

YAML frontmatter：
```markdown
---
name: paperdl
description: >
  Use when the user wants to batch-download academic paper PDFs by DOI via 中科院
  CSTCloud 通行证 + las.ac.cn Shibboleth（机构订阅）. Covers setup, account config,
  login, download, web UI, resume/retry. TRIGGER: 下文献/下载论文/DOI/批量下载/
  配置账号/中科院/CSTCloud/Shibboleth/paperdl. SKIP: 非学术 PDF、纯概念讨论不涉及下载。
---
```
正文必须含这些小节（命令用真实的）：
  - **概述**：一句话定位 + 覆盖的 13 家出版商 + 兜底（crossref/unpaywall）。
  - **首次安装**：`bash app/scripts/setup.sh` → `paperdl config`（填账号）→ `paperdl doctor`（自检）→ `paperdl login`（一次性短信）。
  - **命令参考**表：`config`（配账号）、`doctor`（自检）、`login`（登录）、`run <清单.txt>`（批量下载）、`retry`（重试失败）、`serve --host 0.0.0.0 --port 8200`（网页端）。
  - **工作流配方**：①新机器从零到能下（setup→config→doctor→login→run）。②跑大清单（run；被限流则等待后再跑）。③网页端（serve→浏览器打开→上传 DOI→继续下载/单条重试）。
  - **能力边界**：能下机构订阅 + OA；不能下机构没订的（→ NSTL 文献传递）、不做 Sci-Hub/arXiv/搜索。
  - **排障**：指向 `references/troubleshooting.md`。
  - **安全**：密钥只存本机 .paperdl.env（chmod 600），不上传、不进包。

- [ ] **Step 9: 写 `skill/AGENTS.md`（Codex 入口，与 SKILL.md 同源）**

与 SKILL.md 正文相同（去掉 Claude 专属 frontmatter），开头加一段：
```markdown
# paperdl（Codex 使用说明）

你是在用 shell 直接驱动 paperdl CLI（无需 MCP）。所有命令在本 app/ 目录下用
`.venv/bin/paperdl ...` 或激活 venv 后 `paperdl ...` 运行。先按"首次安装"配好再下载。
```
其余小节（命令参考/工作流/边界/排障/安全）复制 SKILL.md 正文，保持一致。

- [ ] **Step 10: 端到端生成 skill 并核验脱敏**

Run:
```bash
/home/hoo/.conda/envs/res-agent/bin/python3 scripts/make_skill.py /tmp/paperdl_skill && \
echo "--- 检查隐私是否泄漏 ---" && \
( find /tmp/paperdl_skill \( -name ".paperdl.env" -o -name "users.json" -o -name "results.csv" \) | grep . && echo "❌ 泄漏!" || echo "✅ 无泄漏" ) && \
ls /tmp/paperdl_skill && ls /tmp/paperdl_skill/app/paperdl | head
```
Expected: 打印「✅ 无泄漏」；`/tmp/paperdl_skill` 下有 SKILL.md/AGENTS.md/app/references；app/paperdl 里有源码

- [ ] **Step 11: 全量测试 + 提交**

Run: `/home/hoo/.conda/envs/res-agent/bin/python3 -m pytest -q`
Expected: 全 PASS
```bash
git add scripts/make_skill.py tests/test_make_skill.py skill/
git commit -m "feat: 脱敏打包成 Claude Code skill + Codex 包(SKILL.md/AGENTS.md/make_skill)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage（阶段一）：**
- ① config → Task 1 ✅
- ② doctor → Task 2 ✅（代理检查按 spec 修正版：只警告代理泄漏，不要求机构 IP ✅）
- ③ 打包 + setup → Task 3 ✅
- ④ skill/Codex 包（SKILL.md + AGENTS.md + 脱敏 + references + env.example + codex-mcp.toml）→ Task 4 ✅
- 脱敏排除清单（.paperdl.env/.profile/downloads/web_data/results.csv/缓存）→ Task 4 用白名单天然排除 + 测试断言 ✅
- 机构常量集中放一处的注释级说明 → 归入 SKILL.md/troubleshooting，未单列代码任务（仅注释级，YAGNI）。
- ⑤ MCP → 阶段二，单独计划（本计划不含）✅

**Placeholder 扫描：** 代码步骤均含完整代码；文档步骤（Step 7/8/9）给出必含小节 + 真实命令清单，非 TBD。

**类型一致性：** `Check(name,status,detail)` 在 doctor 内一致；`parse_env/merge_env/render_env/write_env` 签名 Task 1 定义、Task 2 仅消费 `parse_env`，一致；`build_app/build_skill` 命名一致。

（如执行中发现 cli.py 已被改动导致行号偏移，按"在 retry 分支后追加"的语义定位即可。）
