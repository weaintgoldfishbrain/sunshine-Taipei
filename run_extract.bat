@echo off
chcp 65001 >nul
echo.
echo ====================================
echo   廉政專刊 PDF → JSON 自動抽取工具
echo ====================================
echo.

:: Navigate to project root (relative to this batch file)
cd /d "%~dp0"

:: Check if pdfs folder has any PDF files
if not exist "pdfs\*.pdf" (
    echo ❌ 在 pdfs\ 資料夾中找不到任何 PDF 檔案。
    echo    請將廉政專刊 PDF 放入以下目錄後再執行：
    echo    %cd%\pdfs\
    echo.
    pause
    exit /b 1
)

echo 📂 偵測到以下 PDF 檔案：
for %%f in (pdfs\*.pdf) do echo    • %%~nxf
echo.

:: Ensure dependencies are installed
echo 🔍 檢查並安裝必要的相依套件 (pdfplumber)...
python -m pip install pdfplumber --quiet

echo 🔄 開始抽取資料...
echo.

python scripts\extractor.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 完成！JSON 檔案已輸出至 data\ 資料夾。
) else (
    echo.
    echo ❌ 執行過程中發生錯誤，請檢查上方輸出訊息。
)

echo.
pause
