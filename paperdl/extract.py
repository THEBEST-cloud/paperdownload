import re

# DOI: 10.<registrant>/<suffix>; registrant is 4–9 digits per standard (relax to 1+ for test DOIs).
# Suffix runs until whitespace/quote/comma/angle. Strip trailing punctuation.
_DOI_RE = re.compile(r'10\.\d+/[^\s"\'<>,]+', re.I)


def extract_dois_from_text(text: str) -> list:
    out, seen = [], set()
    for m in _DOI_RE.finditer(text or ""):
        doi = m.group(0).rstrip(".,;)]}")
        if doi not in seen:
            seen.add(doi)
            out.append(doi)
    return out


def extract_dois_from_excel(path) -> list:
    """读 .xls/.xlsx：优先 DOI 列，否则全表扫描文本。"""
    import pandas as pd
    engine = "xlrd" if str(path).lower().endswith(".xls") else "openpyxl"
    df = pd.read_excel(path, engine=engine, dtype=str)
    # 优先名为 DOI 的列
    for col in df.columns:
        if str(col).strip().lower() == "doi":
            vals = [str(v).strip() for v in df[col] if str(v).strip() and str(v).strip().lower() != "nan"]
            joined = "\n".join(vals)
            got = extract_dois_from_text(joined)
            if got:
                return got
    # 兜底：全表扫描
    return extract_dois_from_text("\n".join(df.fillna("").astype(str).agg(" ".join, axis=1)))
