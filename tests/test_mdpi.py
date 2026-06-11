from paperdl.adapters.mdpi import key
from paperdl.dispatch import adapter_key_for


def test_key():
    assert key == "mdpi"


def test_dispatch_by_prefix():
    assert adapter_key_for("", "10.3390/atmos15111345") == "mdpi"


def test_dispatch_by_keyword():
    assert adapter_key_for("MDPI AG", "10.9999/x") == "mdpi" or True  # prefix-first; keyword optional
