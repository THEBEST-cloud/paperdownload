from paperdl.search.base import Paper
from paperdl.search.export import to_doi_list, to_csv, to_bibtex

P1 = Paper(title="Microplastics in water", authors=["Jane Doe", "Li Wei"],
           year=2021, venue="Water Research", doi="10.1016/j.watres.2021.117056",
           cited_by=42, is_oa=True, type="article")
P2 = Paper(title="No DOI here", authors=[], year=2019, venue="Unknown", doi=None)


def test_to_doi_list_skips_missing():
    out = to_doi_list([P1, P2])
    assert out.strip() == "10.1016/j.watres.2021.117056"


def test_to_csv_has_header_and_row():
    out = to_csv([P1])
    lines = out.strip().splitlines()
    assert lines[0] == "title,authors,year,venue,doi,cited_by,is_oa,type"
    assert "Microplastics in water" in lines[1]
    assert "Jane Doe; Li Wei" in lines[1]


def test_to_bibtex():
    out = to_bibtex([P1])
    assert "@article{" in out
    assert "title = {Microplastics in water}" in out
    assert "doi = {10.1016/j.watres.2021.117056}" in out
    assert "year = {2021}" in out
