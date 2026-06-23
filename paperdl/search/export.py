# paperdl/search/export.py
# 论文数据导出格式转换（DOI 列表、CSV、BibTeX）
import csv
import io
import re

from paperdl.search.base import Paper


def to_doi_list(papers: list[Paper]) -> str:
    """提取所有论文的 DOI 列表。"""
    lines = [p.doi for p in papers if p.doi]
    return "\n".join(lines) + ("\n" if lines else "")


def to_csv(papers: list[Paper]) -> str:
    """导出论文列表为 CSV 格式。"""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["title", "authors", "year", "venue", "doi", "cited_by", "is_oa", "type"])
    for p in papers:
        w.writerow([p.title, "; ".join(p.authors), p.year or "", p.venue,
                    p.doi or "", p.cited_by, p.is_oa, p.type])
    return buf.getvalue()


def _cite_key(p: Paper) -> str:
    """生成 BibTeX cite key（作者姓氏_年份_标题首词）。"""
    surname = "anon"
    if p.authors:
        parts = p.authors[0].split()
        surname = re.sub(r"\W+", "", parts[-1]) if parts else ""
        surname = surname or "anon"
    year = str(p.year) if p.year else "nd"
    first = re.sub(r"\W+", "", (p.title.split()[0] if p.title else "")) or "x"
    return "%s_%s_%s" % (surname, year, first)


def to_bibtex(papers: list[Paper]) -> str:
    """导出论文列表为 BibTeX 格式。"""
    blocks = []
    for p in papers:
        fields = []
        if p.title:
            fields.append("  title = {%s}" % p.title)
        if p.authors:
            fields.append("  author = {%s}" % " and ".join(p.authors))
        if p.venue:
            fields.append("  journal = {%s}" % p.venue)
        if p.year:
            fields.append("  year = {%d}" % p.year)
        if p.doi:
            fields.append("  doi = {%s}" % p.doi)
        blocks.append("@article{%s,\n%s\n}" % (_cite_key(p), ",\n".join(fields)))
    return "\n\n".join(blocks) + ("\n" if blocks else "")
