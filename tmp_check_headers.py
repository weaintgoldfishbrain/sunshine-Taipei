import pdfplumber
from pathlib import Path
import json

BASE_DIR = Path(r"d:\AI_works\雙北議會財產申報")
pdf_path = BASE_DIR / "【廉政專刊第294期】電子書.pdf"

headers_found = set()
with open(BASE_DIR / "tmp_headers.txt", "w", encoding="utf-8") as out:
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:100]): # Check first 100 pages
            tables = page.extract_tables()
            if tables:
                for t in tables:
                    if t and len(t) > 0:
                        header = [str(c).replace('\n', '') for c in t[0] if c is not None]
                        header_key = "|".join(header)
                        if header_key not in headers_found:
                            headers_found.add(header_key)
                            out.write(f"--- Page {i} ---\n")
                            out.write(f"Header : {header}\n")
                            if len(t) > 1:
                                row1 = [str(c).replace('\n', '') for c in t[1] if c is not None]
                                out.write(f"Row 1  : {row1}\n")
