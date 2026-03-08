import pdfplumber
import sys

pdf_path = r"d:\AI_works\雙北議會財產申報\【廉政專刊第295期】電子書.pdf"

print(f"Opening: {pdf_path}")
try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        # Read a few pages to see the structure
        for i in range(10): # Let's see pages 0 to 9
            if i >= len(pdf.pages): break
            page = pdf.pages[i]
            text = page.extract_text()
            print(f"\n--- Page {i+1} ---")
            if text:
                print(text[:500] + "..." if len(text) > 500 else text)
            else:
                print("(No text extracted)")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
