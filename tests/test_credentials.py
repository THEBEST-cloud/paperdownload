from paperdl.credentials import load_credentials, load_env


def test_loads_from_env_file(tmp_path):
    (tmp_path / ".paperdl.env").write_text(
        'CSTCLOUD_ID=alice@example.com\nCSTCLOUD_PASSWORD=secret123\n', encoding="utf-8")
    assert load_credentials(base=tmp_path) == ("alice@example.com", "secret123")


def test_missing_file_returns_none(tmp_path):
    assert load_credentials(base=tmp_path) is None


def test_partial_credentials_returns_none(tmp_path):
    (tmp_path / ".paperdl.env").write_text('CSTCLOUD_ID=alice@example.com\n', encoding="utf-8")
    assert load_credentials(base=tmp_path) is None


def test_env_var_overrides_file(tmp_path, monkeypatch):
    (tmp_path / ".paperdl.env").write_text(
        'CSTCLOUD_ID=file@example.com\nCSTCLOUD_PASSWORD=filepw\n', encoding="utf-8")
    monkeypatch.setenv("CSTCLOUD_ID", "env@example.com")
    monkeypatch.setenv("CSTCLOUD_PASSWORD", "envpw")
    assert load_credentials(base=tmp_path) == ("env@example.com", "envpw")


def test_ignores_comments_quotes_blanklines(tmp_path):
    (tmp_path / ".paperdl.env").write_text(
        '# comment\n\nCSTCLOUD_ID="bob@x.cn"\nCSTCLOUD_PASSWORD=\'p w\'\n', encoding="utf-8")
    assert load_credentials(base=tmp_path) == ("bob@x.cn", "p w")


def test_load_env_reads_file(tmp_path):
    (tmp_path / ".paperdl.env").write_text("ELSEVIER_API_KEY=filekey\nFOO=bar\n", encoding="utf-8")
    cfg = load_env(base=tmp_path)
    assert cfg["ELSEVIER_API_KEY"] == "filekey"
    assert cfg["FOO"] == "bar"


def test_load_env_env_overrides_file(tmp_path, monkeypatch):
    (tmp_path / ".paperdl.env").write_text("ELSEVIER_API_KEY=filekey\n", encoding="utf-8")
    monkeypatch.setenv("ELSEVIER_API_KEY", "envkey")
    assert load_env(base=tmp_path)["ELSEVIER_API_KEY"] == "envkey"


def test_load_env_missing_file_ok(tmp_path):
    assert isinstance(load_env(base=tmp_path), dict)
