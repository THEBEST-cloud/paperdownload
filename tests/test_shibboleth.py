from paperdl.shibboleth import fetch_entries, ENTRY_MATCH


class FakePage:
    def __init__(self, oncs):
        self._oncs = oncs
    def goto(self, *a, **k): pass
    def wait_for_load_state(self, *a, **k): pass
    def wait_for_timeout(self, *a, **k): pass
    def eval_on_selector_all(self, sel, js): return self._oncs


def test_fetch_entries_classifies():
    oncs = [
        "getInUrl('https://sp.nature.com/saml/login?idp=x&targetUrl=y')",
        "getInUrl('https://fsso.springer.com/federation/init?entityId=x')",
        "javascript:void(0)",
    ]
    out = fetch_entries(FakePage(oncs))
    assert out["nature"] == "https://sp.nature.com/saml/login?idp=x&targetUrl=y"
    assert out["springer"] == "https://fsso.springer.com/federation/init?entityId=x"


def test_fetch_entries_empty():
    assert fetch_entries(FakePage([])) == {}
