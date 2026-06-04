from paperdl.adapters.ieee import arnumber, getpdf_url


def test_arnumber_from_document_url():
    assert arnumber("https://ieeexplore.ieee.org/document/771073") == "771073"


def test_arnumber_with_trailing():
    assert arnumber("https://ieeexplore.ieee.org/document/7780459/?foo=1") == "7780459"


def test_arnumber_none():
    assert arnumber("https://ieeexplore.ieee.org/") is None


def test_getpdf_url():
    assert getpdf_url("771073") == "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=771073"
