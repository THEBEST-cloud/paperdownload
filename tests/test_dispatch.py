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


def test_wiley_by_doi_prefix_1002():
    assert adapter_key_for("Wiley", "10.1002/anie.201915678") == "wiley"


def test_wiley_by_doi_prefix_1111():
    assert adapter_key_for("Wiley", "10.1111/jcc.12345") == "wiley"


def test_wiley_by_publisher_string():
    assert adapter_key_for("Wiley-Blackwell", "10.9999/x") == "wiley"


def test_agu_1029_routes_to_wiley():
    assert adapter_key_for("American Geophysical Union (AGU)", "10.1029/2024WR038341") == "wiley"


def test_frontiers_by_doi_prefix():
    assert adapter_key_for("Frontiers Media SA", "10.3389/feart.2015.00063") == "frontiers"


def test_frontiers_by_publisher():
    assert adapter_key_for("Frontiers Media SA", "10.9999/x") == "frontiers"


def test_ieee_by_doi_prefix():
    assert adapter_key_for("IEEE", "10.1109/5.771073") == "ieee"


def test_ieee_by_publisher():
    assert adapter_key_for("IEEE", "10.9999/x") == "ieee"
