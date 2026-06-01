from paperdl.session import (
    find_verification_frame, needs_device_verification, complete_device_verification,
)


class FakeFrame:
    def __init__(self):
        self.has_phone = True
        self.calls = []
    def query_selector(self, sel):
        if sel == "#phoneNumber":
            return object() if self.has_phone else None
        return None
    def fill(self, sel, val):
        self.calls.append(("fill", sel, val))
    def click(self, sel):
        self.calls.append(("click", sel))
        if sel == "#registBtn":
            self.has_phone = False  # 提交后离开验证页


class FakePage:
    def __init__(self, frame):
        self._frame = frame
        self.waited = []
    def query_selector(self, sel):
        return None  # 表单在 frame 里，不在顶层
    @property
    def frames(self):
        return [self._frame]
    def wait_for_timeout(self, ms):
        self.waited.append(ms)


def test_needs_device_verification_true_when_form_present():
    assert needs_device_verification(FakePage(FakeFrame())) is True


def test_needs_device_verification_false_when_absent():
    class Empty:
        def query_selector(self, sel):
            return None
        @property
        def frames(self):
            return []
    assert needs_device_verification(Empty()) is False


def test_complete_device_verification_fills_and_submits_in_order():
    frame = FakeFrame()
    page = FakePage(frame)
    answers = iter(["18600000000", "123456"])
    ok = complete_device_verification(page, input_fn=lambda prompt="": next(answers))
    assert ok is True
    assert frame.calls == [
        ("fill", "#phoneNumber", "18600000000"),
        ("click", "#sendValidateCode"),
        ("fill", "#validateCode", "123456"),
        ("click", "#registBtn"),
    ]


def test_complete_device_verification_returns_false_when_no_form():
    class Empty:
        def query_selector(self, sel):
            return None
        @property
        def frames(self):
            return []
    assert complete_device_verification(Empty(), input_fn=lambda prompt="": "x") is False
