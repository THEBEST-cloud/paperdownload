import re
from urllib.parse import urljoin
from typing import Optional

# 不引入额外 HTML 解析依赖：用正则在 Springer 文章页定位下载链接。
# Springer 的下载链接形如 /content/pdf/<doi>.pdf，class 含 c-pdf-download__link。
_PDF_HREF = re.compile(
    r'href="(?P<href>[^"]*?/content/pdf/[^"]+\.pdf)"', re.IGNORECASE
)


def find_pdf_url(html: str, base_url: str) -> Optional[str]:
    m = _PDF_HREF.search(html)
    if not m:
        return None
    return urljoin(base_url, m.group("href"))
