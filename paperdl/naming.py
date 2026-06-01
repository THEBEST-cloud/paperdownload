import re

from paperdl.resolver import Metadata

ILLEGAL = r'[\/\\:\?\*"<>\|]'
TITLE_MAX = 80


def _clean(text: str) -> str:
    text = re.sub(ILLEGAL, "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_filename(md: Metadata) -> str:
    author = _clean(md.first_author)
    title = _clean(md.title)
    if author and md.year and title:
        title = title[:TITLE_MAX].strip()
        return f"{author}-{md.year}-{title}.pdf"
    # 缺字段时退回 DOI（DOI 里的 / 换成 _）
    safe_doi = re.sub(ILLEGAL, "_", md.doi)
    return f"{safe_doi}.pdf"
