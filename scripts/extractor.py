import pdfplumber
import os
import json
import re
from pathlib import Path

# Setup paths
BASE_DIR = Path(r"d:\AI_works\雙北議會財產申報")
DATA_DIR = BASE_DIR / "data"
POLITICIANS_DIR = DATA_DIR / "politicians"
COUNCILS_JSON = DATA_DIR / "councils.json"

os.makedirs(POLITICIANS_DIR, exist_ok=True)

# Regex patterns for KPIs
RE_DEPOSITS = re.compile(r'（七）存款.*?總金額：新臺幣\s*([\d,]+)\s*元')
RE_SECURITIES = re.compile(r'（八）有價證券.*?總價額：新臺幣\s*([\d,]+)\s*元')
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
                                
                            council_name = council_name.replace("1.", "").strip()
                            title = title.replace("1.", "").strip()
                            
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
                                    'stats': {
                                        'deposits': '0',
                                        'securities': '0',
                                        'debt': '0',
                                        'realEstate': '0筆'
                                    },
                                    'chartData': [0, 0, 0, 0],
                                    'transactions': [],
                                    'insurance': [],
                                    'investments': [],
                                    'automobiles': [],
                                    'real_estate': [],
                                    '_real_estate_count': 0
                                }
                                politicians_dict[p_id] = current_person
                    
                    if current_person:
                        # 2. Extract KPIs from text
                        dep_match = RE_DEPOSITS.search(text)
                        if dep_match: current_person['stats']['deposits'] = dep_match.group(1)
                        
                        sec_match = RE_SECURITIES.search(text)
                        if sec_match: current_person['stats']['securities'] = sec_match.group(1)
                        
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
            
                            # Insurance
                            if '保險公司' in header_str and '保險名稱' in header_str:
                                for row in table[1:]:
                                    clean_r = [clean_str(c) for c in row]
                                    if len(clean_r) >= 6 and clean_r[0] and '本欄空白' not in clean_r[0]:
                                        current_person['insurance'].append({
                                            'company': clean_r[0],
                                            'name': clean_r[1],
                                            'owner': clean_r[3] if len(clean_r) > 3 else '',
                                            'type': clean_r[4] if len(clean_r) > 4 else '',
                                            'status': clean_r[5] if len(clean_r) > 5 else ''
                                        })
                            
                            # Investments
                            if '投資事業名稱' in header_str and '投資金額' in header_str:
                                for row in table[1:]:
                                    clean_r = [clean_str(c) for c in row]
                                    if len(clean_r) >= 4 and clean_r[0] and '本欄空白' not in clean_r[0]:
                                        current_person['investments'].append({
                                            'owner': clean_r[0],
                                            'investor': clean_r[0], # same as owner here
                                            'business': clean_r[1],
                                            'amount': clean_r[3]
                                        })
                
                # No need to explicitly save the last person since it's already in the dictionary by reference

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            
    # Process Chart Data
    for p in politicians_dict.values():
        dep = int(p['stats']['deposits'].replace(',', '') or 0)
        sec = int(p['stats']['securities'].replace(',', '') or 0)
        # Assuming each real estate is roughly 10M for chart weighting (just for visualization)
        re_val = p['_real_estate_count'] * 10000000 
        
        total = dep + sec + re_val
        if total > 0:
            p['chartData'] = [
                round((dep / total) * 100),
                round((sec / total) * 100),
                round((re_val / total) * 100),
                0
            ]
        else:
            p['chartData'] = [0, 0, 0, 0]
        
        del p['_real_estate_count'] # Clean up internal temp field

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
        sidebar_politicians[pid] = {
            "id": p["id"],
            "councilId": p["councilId"],
            "name": p["name"],
            "title": p["title"]
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
    pdf_files = [
        BASE_DIR / "【廉政專刊第294期】電子書.pdf",
        BASE_DIR / "【廉政專刊第295期】電子書.pdf"
    ]
    
    existing_pdfs = [p for p in pdf_files if p.exists()]
    if not existing_pdfs:
        print("No PDF files found!")
        exit(1)
        
    councils_dict, politicians_dict = process_pdfs(existing_pdfs)
    export_json(councils_dict, politicians_dict)
    print("Data extraction complete.")
