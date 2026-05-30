from dataclasses import dataclass
from typing import Optional, Protocol

from paperdl.resolver import Metadata


@dataclass
class DownloadResult:
    ok: bool
    pdf_bytes: Optional[bytes] = None
    reason: str = ""  # 失败原因分类: no_access | blocked | no_pdf | timeout | error


class Adapter(Protocol):
    key: str

    def download(self, page, md: Metadata) -> DownloadResult:
        """用已登录的 Playwright page 把 md 对应文章的 PDF 抓下来。"""
        ...
