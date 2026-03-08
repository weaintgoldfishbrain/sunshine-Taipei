import json
import os
import hashlib
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
POLITICIANS_DIR = DATA_DIR / "politicians"
POLITICIANS_LIST_JSON = DATA_DIR / "politicians_list.json"

def normalize_name(name):
    return name.replace(' ', '').replace('　', '').strip()

def merge_records(primary, duplicate):
    # Merge stats (prefer non-zero values)
    p_stats = primary.get('stats', {})
    d_stats = duplicate.get('stats', {})
    for k in ['cash', 'deposits', 'securities', 'jewelry', 'credit', 'debt']:
        p_val = int(str(p_stats.get(k, '0')).replace(',', '') or 0)
        d_val = int(str(d_stats.get(k, '0')).replace(',', '') or 0)
        if d_val > p_val:
            p_stats[k] = d_stats.get(k, '0')
    
    # Merge counts for real estate
    p_re_str = p_stats.get('realEstate', '0筆')
    d_re_str = d_stats.get('realEstate', '0筆')
    p_re_count = int(p_re_str.replace('筆', '') or 0)
    d_re_count = int(d_re_str.replace('筆', '') or 0)
    # This is tricky since individual items might be duplicates, but for now we take the larger count
    # Ideally we'd merge the lists and recount
    
    # Merge lists
    for attr in ['transactions', 'automobiles', 'real_estate']:
        p_list = primary.get(attr, [])
        d_list = duplicate.get(attr, [])
        # Simple deduplication based on string representation
        seen = {json.dumps(i, sort_keys=True) for i in p_list}
        for item in d_list:
            item_json = json.dumps(item, sort_keys=True)
            if item_json not in seen:
                p_list.append(item)
                seen.add(item_json)
        primary[attr] = p_list

    # Recount real estate from merged list
    if primary.get('real_estate'):
        primary['stats']['realEstate'] = f"{len(primary['real_estate'])}筆"
    
    # Merge source
    p_source = primary.get('source', '')
    d_source = duplicate.get('source', '')
    sources = set()
    if p_source: sources.update([s.strip() for s in p_source.split(',')])
    if d_source: sources.update([s.strip() for s in d_source.split(',')])
    primary['source'] = ", ".join(sorted(list(sources)))
    
    # Keep the more informative title (avoid "未知職稱")
    if '未知職稱' in primary.get('title', '') and '未知職稱' not in duplicate.get('title', ''):
        primary['title'] = duplicate['title']
    
    return primary

def cleanup():
    if not POLITICIANS_DIR.exists():
        print("Politicians directory not found.")
        return

    # 1. Group files by (Normalized Name, Council ID)
    groups = {} # (norm_name, council_id) -> [list of data]
    
    for p_path in POLITICIANS_DIR.glob("*.json"):
        try:
            with open(p_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                name = normalize_name(data['name'])
                cid = data['councilId']
                key = (name, cid)
                if key not in groups:
                    groups[key] = []
                groups[key].append(data)
        except Exception as e:
            print(f"Error reading {p_path}: {e}")

    # 2. Merge and Save
    new_politicians_list = {}
    
    # First, delete all old files to avoid confusion
    for p_path in POLITICIANS_DIR.glob("*.json"):
        os.remove(p_path)
    
    print(f"Processing {len(groups)} unique politicians...")
    
    for (name, cid), records in groups.items():
        # Generate new ID based on normalized name
        cid_hash = cid.split('_')[1] if '_' in cid else cid
        p_hash = hashlib.md5(name.encode()).hexdigest()[:10]
        new_id = f"p_{cid_hash}_{p_hash}"
        
        # Merge all records in the group
        primary = records[0]
        for i in range(1, len(records)):
            primary = merge_records(primary, records[i])
        
        primary['id'] = new_id
        # Thoroughly clean name in the object
        primary['name'] = primary['name'].replace(' ', '').replace('　', '').strip()
        
        # Save merged record
        dest_path = POLITICIANS_DIR / f"{new_id}.json"
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(primary, f, ensure_ascii=False, indent=2)
            
        # Add to sidebar list (sidebar needs constituency)
        new_politicians_list[new_id] = {
            "id": new_id,
            "councilId": cid,
            "name": primary['name'],
            "title": primary['title'],
            "constituency": primary.get('constituency', '其他/不詳')
        }

    # 3. Update politicians_list.json
    with open(POLITICIANS_LIST_JSON, "w", encoding="utf-8") as f:
        json.dump(new_politicians_list, f, ensure_ascii=False, indent=2)
        
    print(f"Cleanup complete. Processed {len(groups)} politicians.")

if __name__ == "__main__":
    cleanup()
