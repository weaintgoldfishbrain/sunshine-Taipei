import pdfplumber
import os

pdf_path = r"d:\AI_works\雙北議會財產申報\【廉政專刊第295期】電子書.pdf"
output_path = r"d:\AI_works\雙北議會財產申報\data\sample_295.txt"

os.makedirs(os.path.dirname(output_path), exist_ok=True)

print(f"Opening: {pdf_path}")
try:
    with pdfplumber.open(pdf_path) as pdf:
        with open(output_path, "w", encoding="utf-8") as f:
            for i in range(15): # Read 15 pages
                if i >= len(pdf.pages): break
                page = pdf.pages[i]
                text = page.extract_text()
                f.write(f"\n{'='*20} Page {i+1} {'='*20}\n")
                if text:
                    f.write(text + "\n")
                else:
                    f.write("(No text extracted)\n")
                
                tables = page.extract_tables()
                if tables:
                    f.write("\n--- Tables ---\n")
                    for t_idx, table in enumerate(tables):
                        f.write(f"Table {t_idx+1}:\n")
                        for row in table:
                            # Clean up None values
                            clean_row = [str(cell).replace('\n', ' ') if cell is not None else '' for cell in row]
                            f.write(" | ".join(clean_row) + "\n")
                        f.write("-" * 20 + "\n")
        print(f"Successfully wrote to {output_path}")
except Exception as e:
    print(f"Error: {e}")
