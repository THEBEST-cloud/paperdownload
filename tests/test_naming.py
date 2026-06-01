from paperdl.naming import build_filename
from paperdl.resolver import Metadata


def test_build_filename_normal():
    md = Metadata(doi="10.1007/abc", first_author="Zhang", year=2021,
                  title="A Study of Something Interesting")
    assert build_filename(md) == "Zhang-2021-A Study of Something Interesting.pdf"


def test_build_filename_strips_illegal_chars():
    md = Metadata(doi="10.1/x", first_author="O'Neil", year=2020,
                  title="Title: with / illegal \\ chars?")
    name = build_filename(md)
    for ch in '/\\:?*"<>|':
        assert ch not in name
    assert name.endswith(".pdf")


def test_build_filename_truncates_long_title():
    md = Metadata(doi="10.1/x", first_author="Li", year=2019, title="x" * 200)
    name = build_filename(md)
    assert len(name) <= 100  # 留余量


def test_build_filename_falls_back_to_doi_when_empty():
    md = Metadata(doi="10.1007/abc.def")
    name = build_filename(md)
    assert name == "10.1007_abc.def.pdf"
