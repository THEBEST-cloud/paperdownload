from paperdl.dispatch import adapter_key_for


def test_springer_by_publisher_string():
    assert adapter_key_for("Springer Science and Business Media LLC", "10.1007/x") == "springer"


def test_springer_by_doi_prefix():
    assert adapter_key_for("", "10.1007/s00339-021-04567-w") == "springer"


def test_unknown_publisher_returns_none():
    assert adapter_key_for("Some Tiny Press", "10.9999/x") is None


def test_elsevier_by_publisher_string():
    assert adapter_key_for("Elsevier BV", "10.1016/x") == "elsevier"


def test_elsevier_by_doi_prefix():
    assert adapter_key_for("", "10.1016/j.cell.2020.02.052") == "elsevier"
