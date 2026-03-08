import pdfplumber
import os
import json
import re
import sys
from pathlib import Path

# Setup paths - use relative paths from this script's location
BASE_DIR = Path(__file__).resolve().parent.parent
PDFS_DIR = BASE_DIR / "pdfs"
DATA_DIR = BASE_DIR / "data"
POLITICIANS_DIR = DATA_DIR / "politicians"
COUNCILS_JSON = DATA_DIR / "councils.json"
MAP_JSON = BASE_DIR / "scripts" / "constituency_map.json"

# Load constituency map
CONSTITUENCY_MAP = {} # council_name -> zone_name -> set of clean_names
if MAP_JSON.exists():
    with open(MAP_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
        for c_name, zones in data.items():
            CONSTITUENCY_MAP[c_name] = {}
            for z_name, names in zones.items():
                CONSTITUENCY_MAP[c_name][z_name] = [n.replace(" ", "").replace("　", "") for n in names]

os.makedirs(POLITICIANS_DIR, exist_ok=True)
os.makedirs(PDFS_DIR, exist_ok=True)

# Regex patterns for KPIs
RE_CASH = re.compile(r'（六）現金.*?總金額：新臺幣\s*([\d,]+)\s*元')
RE_DEPOSITS = re.compile(r'（七）存款.*?總金額：新臺幣\s*([\d,]+)\s*元')
RE_SECURITIES = re.compile(r'（八）有價證券.*?總價額：新臺幣\s*([\d,]+)\s*元')
RE_JEWELRY = re.compile(r'（九）珠寶、古董、字畫.*?總價額：新臺幣\s*([\d,]+)\s*元')
RE_CREDIT = re.compile(r'（十）債權.*?總金額：新臺幣\s*([\d,]+)\s*元')
RE_DEBT = re.compile(r'（十一）債務.*?總金額：新臺幣\s*([\d,]+)\s*元')

def clean_str(s):
    if s is None:
        return ""
    return str(s).replace('\n', ' ').strip()

def process_pdfs(pdf_paths):
    councils_dict = {} # council_name -> id
    politicians_dict = {} # p_id -> details
    import hashlib
    
    for pdf_path in pdf_paths:
        print(f"Processing {pdf_path.name}...")
        # Extract issue number from filename like "【廉政專刊第295期】電子書.pdf"
        issue_match = re.search(r'第(\d+)期', pdf_path.name)
        issue_no = f"第{issue_match.group(1)}期" if issue_match else ""

        try:
            with pdfplumber.open(pdf_path) as pdf:
                current_person = None
                
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    tables = page.extract_tables() or []
                    
                    # 1. Detect New Report
                    # Look for basic info table
                    if tables:
                        t0 = tables[0]
                        if len(t0) > 0 and '申報人姓名' in clean_str(t0[0][0]):
                            # New person started!
                            name = clean_str(t0[0][1])
                            council_name = clean_str(t0[0][4]) if len(t0[0]) > 4 else "未知機關"
                            title = clean_str(t0[0][9]) if len(t0[0]) > 9 else "未知職稱"
                            if not title and len(t0) > 1 and len(t0[1]) > 9:
                                title = clean_str(t0[1][9]) # sometimes spans rows
                                
                            # Deep clean council name and title (remove "1.", "2.", " 1.", " 2." etc.)
                            council_name = re.sub(r'\s*\d+\.?\s*$', '', council_name).strip()
                            council_name = re.sub(r'^\s*\d+\.?\s*', '', council_name).strip()
                            title = re.sub(r'^\s*\d+\.?\s*', '', title).strip()
                            
                            # Standardize council ID
                            cid_hash = hashlib.md5(council_name.encode()).hexdigest()[:6]
                            council_id = "council_" + cid_hash
                            if council_name not in councils_dict:
                                councils_dict[council_name] = council_id
                            
                            # Clean name thoroughly for hash to eliminate spaces
                            clean_name_hash = name.replace(' ', '').replace('　', '')
                            p_hash = hashlib.md5(clean_name_hash.encode()).hexdigest()[:6]
                            p_id = f"p_{cid_hash}_{p_hash}"
                            
                            if p_id in politicians_dict:
                                current_person = politicians_dict[p_id]
                                if '未知職稱' in current_person['title']:
                                    current_person['title'] = f"{council_name} {title}"
                            else:
                                current_person = {
                                    'id': p_id,
                                    'councilId': council_id,
                                    'name': name,
                                    'title': f"{council_name} {title}",
                                    'source': issue_no,
                                    'stats': {
                                        'cash': '0',
                                        'deposits': '0',
                                        'securities': '0',
                                        'jewelry': '0',
                                        'credit': '0',
                                        'debt': '0',
                                        'realEstate': '0筆'
                                    },
                                    'chartData': [0, 0, 0, 0, 0, 0, 0],
                                    'transactions': [],
                                    'automobiles': [],
                                    'real_estate': [],
                                    '_real_estate_count': 0
                                }
                                politicians_dict[p_id] = current_person
                            
                            # Update source if new information arrives
                            if issue_no and not current_person.get('source'):
                                current_person['source'] = issue_no
                    
                    if current_person:
                        # 2. Extract KPIs from text
                        cash_match = RE_CASH.search(text)
                        if cash_match: current_person['stats']['cash'] = cash_match.group(1)
                        
                        dep_match = RE_DEPOSITS.search(text)
                        if dep_match: current_person['stats']['deposits'] = dep_match.group(1)
                        
                        sec_match = RE_SECURITIES.search(text)
                        if sec_match: current_person['stats']['securities'] = sec_match.group(1)

                        jewel_match = RE_JEWELRY.search(text)
                        if jewel_match: current_person['stats']['jewelry'] = jewel_match.group(1)

                        credit_match = RE_CREDIT.search(text)
                        if credit_match: current_person['stats']['credit'] = credit_match.group(1)
                        
                        debt_match = RE_DEBT.search(text)
                        if debt_match: current_person['stats']['debt'] = debt_match.group(1)
                            
                        # 3. Extract Transactions and Real Estate counts from tables
                        for table in tables:
                            # Heuristic for table type
                            header_row = [clean_str(c) for c in table[0]] if table else []
                            header_str = "".join(header_row)
                            
                            # Real estate count & details
                            if '土地坐落' in header_str or '建 物 標 示' in header_str or '土 地 坐 落' in header_str or '建物標示' in header_str:
                                type_name = '土地' if '土地' in header_str or '土 地' in header_str else '建物'
                                for row in table[1:]:
                                    clean_r = [clean_str(c) for c in row]
                                    if len(clean_r) > 0 and clean_r[0] and '本欄空白' not in clean_r[0]:
                                        current_person['_real_estate_count'] += 1
                                        if len(clean_r) >= 4:
                                            current_person['real_estate'].append({
                                                'type': type_name,
                                                'location': clean_r[0],
                                                'area': clean_r[1],
                                                'portion': clean_r[2],
                                                'owner': clean_r[3]
                                            })
                                current_person['stats']['realEstate'] = f"{current_person['_real_estate_count']}筆"
                            
                            # Transactions
                            if '證券交易商名稱' in header_str and '變動時之價額' in header_str:
                                # It's a transaction table
                                for row in table[1:]:
                                    clean_r = [clean_str(c) for c in row]
                                    if len(clean_r) >= 8 and clean_r[0] and clean_r[0] != '名 稱' and '本欄空白' not in clean_r[0]:
                                        stock = clean_r[0]
                                        broker = clean_r[1]
                                        owner = clean_r[2]
                                        tx_type = clean_r[6]
                                        price = clean_r[4]
                                        date = clean_r[5]
                                        amount = clean_r[7]
                                        
                                        type_color = 'bg-slate-100 text-slate-700'
                                        if '買' in tx_type: type_color = 'bg-red-100 text-red-700' # 台股買是紅
                                        elif '賣' in tx_type: type_color = 'bg-green-100 text-green-700' # 台股賣是綠
                                        
                                        current_person['transactions'].append({
                                            'stock': stock,
                                            'broker': broker,
                                            'owner': owner,
                                            'type': tx_type,
                                            'typeColor': type_color,
                                            'price': price,
                                            'date': date,
                                            'amount': amount
                                        })
                                        
                            # Automobile
                            if '汽 缸 容 量' in header_str or '牌照號碼' in header_str:
                                for row in table[1:]:
                                    clean_r = [clean_str(c) for c in row]
                                    if len(clean_r) >= 3 and clean_r[0] and '本欄空白' not in clean_r[0]:
                                        current_person['automobiles'].append({
                                            'brand': clean_r[0],
                                            'cc': clean_r[1] if len(clean_r) > 1 else '',
                                            'owner': clean_r[2] if len(clean_r) > 2 else '',
                                            'license': clean_r[3] if len(clean_r) > 3 else '' # license might be missing or merged depending on format
                                        })
            
                # No need to explicitly save the last person since it's already in the dictionary by reference

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            
    # Process Chart Data
    for p in politicians_dict.values():
        cash = int(p['stats']['cash'].replace(',', '') or 0)
        dep = int(p['stats']['deposits'].replace(',', '') or 0)
        sec = int(p['stats']['securities'].replace(',', '') or 0)
        jewel = int(p['stats']['jewelry'].replace(',', '') or 0)
        credit = int(p['stats']['credit'].replace(',', '') or 0)
        debt = int(p['stats']['debt'].replace(',', '') or 0)
        
        # Assuming each real estate is roughly 10M for chart weighting
        re_val = p['_real_estate_count'] * 10000000 
        
        # We calculate the total absolute value of all items to determine chart proportions
        total = cash + dep + sec + jewel + credit + re_val + debt
        if total > 0:
            p['chartData'] = [
                round((cash / total) * 100),
                round((dep / total) * 100),
                round((sec / total) * 100),
                round((re_val / total) * 100),
                round(((jewel + credit) / total) * 100), # 合併計算其他動產與債權
                round((debt / total) * 100), # 債務
                0 # other
            ]
        else:
            p['chartData'] = [0, 0, 0, 0, 0, 0, 0]
        
        del p['_real_estate_count'] 

    return councils_dict, politicians_dict

def export_json(councils_dict, politicians_dict):
    # Filter out non-Taipei/New Taipei councils
    filtered_c = {}
    for name, cid in councils_dict.items():
        if '臺北市' in name or '新北市' in name:
            filtered_c[name] = cid
    councils_dict = filtered_c

    filtered_p = {}
    for pid, p in politicians_dict.items():
        if p["councilId"] in councils_dict.values():
            filtered_p[pid] = p
    politicians_dict = filtered_p

    # Create councils structure
    councils = [{"id": cid, "name": name} for name, cid in councils_dict.items()]
    
    with open(COUNCILS_JSON, "w", encoding="utf-8") as f:
        json.dump(councils, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(councils)} councils to {COUNCILS_JSON}")
    
    # Save a master list of basic info for sidebar (to avoid loading all details)
    sidebar_politicians = {}
    for pid, p in politicians_dict.items():
        # Tag constituency (Fuzzy match)
        clean_name = p["name"].replace(" ", "").replace("　", "")
        council_name = "臺北市議會" if p["councilId"] == "council_efab41" else "新北市議會"
        
        constituency = "其他/不詳"
        c_map = CONSTITUENCY_MAP.get(council_name, {})
        for zone, names in c_map.items():
            for m_name in names:
                if m_name in clean_name: # Simple substring match
                    constituency = zone
                    break
            if constituency != "其他/不詳": break
        
        p["constituency"] = constituency
        
        sidebar_politicians[pid] = {
            "id": p["id"],
            "councilId": p["councilId"],
            "name": p["name"],
            "title": p["title"],
            "constituency": constituency
        }
    with open(DATA_DIR / "politicians_list.json", "w", encoding="utf-8") as f:
        json.dump(sidebar_politicians, f, ensure_ascii=False, indent=2)
        
    # Save individual detailed files
    for pid, p in politicians_dict.items():
        p_path = POLITICIANS_DIR / f"{pid}.json"
        with open(p_path, "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
            
    print(f"Saved {len(politicians_dict)} politician profiles to {POLITICIANS_DIR}")

if __name__ == "__main__":
    # Support CLI args or auto-scan pdfs/ folder
    if len(sys.argv) > 1:
        # User specified specific PDF files
        pdf_files = [Path(p) for p in sys.argv[1:]]
    else:
        # Auto-scan pdfs/ folder for all .pdf files
        pdf_files = sorted(PDFS_DIR.glob("*.pdf"))
    
    existing_pdfs = [p for p in pdf_files if p.exists()]
    
    if not existing_pdfs:
        print(f"\n❌ 找不到 PDF 檔案！")
        print(f"   請將廉政專刊 PDF 放入以下目錄：")
        print(f"   {PDFS_DIR}")
        print(f"\n   或透過指令列指定路徑：")
        print(f"   python {Path(__file__).name} path/to/file.pdf")
        sys.exit(1)
    
    print(f"\n📂 找到 {len(existing_pdfs)} 個 PDF 檔案：")
    for p in existing_pdfs:
        print(f"   • {p.name}")
    print()
    
    councils_dict, politicians_dict = process_pdfs(existing_pdfs)
    export_json(councils_dict, politicians_dict)
    
    # Move processed PDFs to processed/ subfolder
    import shutil
    PROCESSED_DIR = PDFS_DIR / "processed"
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    moved_count = 0
    for pdf in existing_pdfs:
        if pdf.parent.resolve() == PDFS_DIR.resolve():  # Only move files from pdfs/ root
            dest = PROCESSED_DIR / pdf.name
            try:
                shutil.move(str(pdf), str(dest))
                moved_count += 1
            except Exception as e:
                print(f"   ⚠️ 無法移動 {pdf.name}：{e}")
    
    print(f"\n✅ 資料抽取完成！共處理 {len(existing_pdfs)} 個 PDF。")
    print(f"   JSON 已輸出至 {DATA_DIR}")
    if moved_count > 0:
        print(f"   📁 已將 {moved_count} 個 PDF 移至 {PROCESSED_DIR}")
