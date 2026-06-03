from paperdl.extract import extract_dois_from_text


def test_extract_from_plain_lines():
    assert extract_dois_from_text("10.1007/abc\n10.1016/xyz\n") == ["10.1007/abc", "10.1016/xyz"]


def test_extract_dedups_preserving_order():
    assert extract_dois_from_text("10.1/a\n10.1/a\n10.2/b") == ["10.1/a", "10.2/b"]


def test_extract_finds_dois_in_messy_text():
    txt = "see https://doi.org/10.1038/nature14539 and DOI: 10.1021/jacs.9b13402 ."
    assert extract_dois_from_text(txt) == ["10.1038/nature14539", "10.1021/jacs.9b13402"]


def test_extract_ignores_non_dois():
    assert extract_dois_from_text("hello world\nno doi here") == []
