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


def test_run_config_collects_openalex_mailto(tmp_path):
    def inp(prompt):
        if "通行证账号" in prompt:
            return "acct@cas.cn"
        if "OpenAlex" in prompt:
            return "researcher@example.com"
        return ""

    run_config(base=tmp_path, input_fn=inp,
               getpass_fn=lambda prompt: "secretpw" if "通行证密码" in prompt else "")
    d = parse_env((tmp_path / ".paperdl.env").read_text(encoding="utf-8"))
    assert d["OPENALEX_MAILTO"] == "researcher@example.com"
