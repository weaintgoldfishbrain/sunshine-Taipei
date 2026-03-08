# 📂 廉政專刊 PDF → JSON 自動化抽取工具

## 使用教學

### 前置需求

- **Python 3.8+**（已安裝）
- **pdfplumber** 套件：
  ```bash
  pip install pdfplumber
  ```

---

### 快速上手（三步驟）

#### Step 1：放入 PDF
將監察院下載的廉政專刊 PDF 放入專案的 `pdfs/` 資料夾：

```
雙北議會財產申報/
└── pdfs/
    ├── 【廉政專刊第294期】電子書.pdf  ← 放這裡
    └── 【廉政專刊第295期】電子書.pdf  ← 放這裡
```

#### Step 2：執行抽取
**方法 A — 雙擊批次檔（推薦）**
直接雙擊專案根目錄的 `run_extract.bat`

**方法 B — 終端機執行**
```bash
cd d:\AI_works\雙北議會財產申報
python scripts/extractor.py
```

**方法 C — 指定特定 PDF**
```bash
python scripts/extractor.py "pdfs/【廉政專刊第296期】電子書.pdf"
```

#### Step 3：完成！
JSON 自動產出至 `data/` 資料夾，已處理的 PDF 會自動移至 `pdfs/processed/`：

```
pdfs/
├── 新的未處理.pdf     ← 放這裡
└── processed/         ← 處理完自動移入
    ├── 第294期.pdf
    └── 第295期.pdf
```

```
data/
├── councils.json          ← 議會清單
├── politicians_list.json  ← 側邊欄名單索引
└── politicians/           ← 每位民代的詳細資料
    ├── p_efab41_fe4d16.json
    ├── p_efab41_be361d.json
    └── ...（自動生成）
```

重新載入網頁即可看到最新資料。

---

### 資料夾結構說明

```
雙北議會財產申報/
├── index.html           → 前端儀表板
├── run_extract.bat      → 一鍵執行（雙擊即用）
├── sitemap.xml          → SEO sitemap
├── robots.txt           → 搜尋引擎指引
├── CNAME                → GitHub Pages 自訂域名
├── pdfs/                → 📥 PDF 輸入資料夾
│   ├── *.pdf            ← 放入新 PDF
│   └── processed/      ← 處理完自動移入
├── data/                → 📤 JSON 輸出資料夾
│   ├── councils.json
│   ├── politicians_list.json
│   └── politicians/
├── scripts/
│   ├── extractor.py     → 核心解析器
│   ├── export_pages.py  → PDF 內容偵錯工具
│   └── test_pdf.py      → 測試腳本
```

---

### 常見問題

**Q：新增一期專刊後，舊資料會被覆蓋嗎？**
> 不會。程式會合併所有 PDF 的資料。相同人名會自動合併，不同期的數據以最新偵測到的為準。

**Q：只想處理某一期怎麼辦？**
> 將 `pdfs/` 中只保留該期的 PDF，或用指令指定：
> ```bash
> python scripts/extractor.py "pdfs/特定檔案.pdf"
> ```

**Q：出現 `ModuleNotFoundError: pdfplumber` 怎麼辦？**
> 執行 `pip install pdfplumber` 安裝套件即可。

**Q：資料有誤差怎麼辦？**
> 本工具依賴 PDF 掃描品質，數據可能存在解析誤差。請以監察院官方原始文檔為準。
