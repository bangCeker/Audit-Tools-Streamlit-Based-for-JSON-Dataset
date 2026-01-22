import re
import unicodedata

def normalize_text(t: str) -> str:
    t = t or ""
    t = unicodedata.normalize("NFKC", t).strip()
    t = re.sub(r"\s+", " ", t).strip()
    return t
