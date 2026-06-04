from paperdl.web.auth import hash_password, verify_password, Auth


def test_hash_verify_roundtrip():
    h = hash_password("secret123")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


def test_register_and_login(tmp_path):
    a = Auth(base=tmp_path)
    ok, msg = a.register("alice", "secret123")
    assert ok
    sid = a.login("alice", "secret123")
    assert sid and a.user_for_sid(sid) == "alice"
    assert a.login("alice", "bad") is None


def test_register_duplicate(tmp_path):
    a = Auth(base=tmp_path)
    a.register("bob", "secret123")
    ok, msg = a.register("bob", "another1")
    assert not ok and "已存在" in msg


def test_short_password_rejected(tmp_path):
    a = Auth(base=tmp_path)
    ok, msg = a.register("carol", "123")
    assert not ok


def test_logout_invalidates(tmp_path):
    a = Auth(base=tmp_path)
    a.register("dan", "secret123")
    sid = a.login("dan", "secret123")
    a.logout(sid)
    assert a.user_for_sid(sid) is None


def test_sessions_persist_across_instances(tmp_path):
    a = Auth(base=tmp_path)
    a.register("eve", "secret123")
    sid = a.login("eve", "secret123")
    a2 = Auth(base=tmp_path)
    assert a2.user_for_sid(sid) == "eve"
