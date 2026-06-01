from paperdl.session import (
    find_verification_frame, needs_device_verification, complete_device_verification,
)


class FakeFrame:
    def __init__(self):
        self.has_phone = True
        self.evals = []
    def query_selector(self, sel):
        if sel == "#phoneNumber":
            return object() if self.has_phone else None
        return None
    def evaluate(self, js, arg=None):
        self.evals.append((js, arg))
        # 原生 submit 后离开验证页
        if "createRequestForm" in js and "submit" in js:
            self.has_phone = False
        return "OK"


class FakePage:
    def __init__(self, frame):
        self._frame = frame
    def query_selector(self, sel):
        return None  # 表单在 frame 里，不在顶层
    @property
    def frames(self):
        return [self._frame]
    def wait_for_load_state(self, *a, **k):
        pass
    def wait_for_timeout(self, *a, **k):
        pass


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


def test_complete_device_verification_sends_then_submits():
    frame = FakeFrame()
    page = FakePage(frame)
    answers = iter(["15680575851", "694137"])
    ok = complete_device_verification(page, input_fn=lambda prompt="": next(answers))
    assert ok is True
    # 第一个 evaluate 是发短信，参数是裸手机号
    send_args = [arg for js, arg in frame.evals if "sendValidateCode" in js]
    assert send_args == ["15680575851"]
    # 第二个 evaluate 是原生提交，参数带手机号+验证码
    submit_args = [arg for js, arg in frame.evals if "createRequestForm" in js]
    assert submit_args == [{"phone": "15680575851", "code": "694137"}]


def test_complete_device_verification_returns_false_when_no_form():
    class Empty:
        def query_selector(self, sel):
            return None
        @property
        def frames(self):
            return []
    assert complete_device_verification(Empty(), input_fn=lambda prompt="": "x") is False
