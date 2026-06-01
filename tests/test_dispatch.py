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


def test_nature_by_doi_prefix_beats_springer_publisher():
    # Nature 的 Crossref 出版商也是 "Springer..."，但 10.1038 必须路由到 nature
    assert adapter_key_for("Springer Science and Business Media LLC", "10.1038/nature14539") == "nature"


def test_acs_by_doi_prefix():
    assert adapter_key_for("American Chemical Society (ACS)", "10.1021/jacs.9b13402") == "acs"


def test_acs_by_publisher_string():
    assert adapter_key_for("American Chemical Society (ACS)", "10.9999/x") == "acs"


def test_rsc_by_doi_prefix():
    assert adapter_key_for("Royal Society of Chemistry (RSC)", "10.1039/d0sc01746a") == "rsc"


def test_rsc_by_publisher_string():
    assert adapter_key_for("Royal Society of Chemistry (RSC)", "10.9999/x") == "rsc"
