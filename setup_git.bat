@echo off
cd /d d:\epub-metadata-editor-py

echo [1/7] Inisialisasi git...
git init

echo [2/7] Konfigurasi git user...
git config user.name "Developer"
git config user.email "dev@example.com"

echo [3/7] Membuat .gitignore...
(
echo __pycache__/
echo *.pyc
echo *.pyo
echo *.egg-info/
echo .eggs/
echo dist/
echo build/
echo *.epub
echo *.tmp
echo .vscode/
echo .idea/
echo *.spec
echo *.log
echo .DS_Store
echo Thumbs.db
echo .git
echo ) > .gitignore

echo [4/7] Membuat README.md...
(
echo # EPUB Metadata Editor
echo.
echo A desktop application for editing EPUB e-book metadata, built with Python and PyQt6.
echo.
echo ## Features
echo.
echo - Read and edit EPUB metadata ^(title, author, publisher, date, description, subjects, series, etc.^)
echo - Support for EPUB2 and EPUB3 formats
echo - Cover image replacement and removal
echo - Edit auxiliary files ^(TOC, NCX, page-map^)
echo - Modern UI with gradient background and card-style layout
echo - Metadata search prompt template for AI assistants
echo.
echo ## Requirements
echo.
echo - Python 3.10+
echo - PyQt6 ^>= 6.5.0^
echo - qtawesome
echo.
echo ## Installation
echo.
echo ```bash
echo pip install -r requirements.txt
echo python main.py
echo ```
echo.
echo ## Running Tests
echo.
echo ```bash
echo python -m pytest tests/
echo ```
echo.
echo ## License
echo.
echo MIT
echo ) > README.md

echo [5/7] Staging files...
git add -A

echo [6/7] Commit...
git commit -m "Initial commit"

echo [7/7] Setup selesai!
git log --oneline -1

echo.
echo Repo lokal siap. Untuk push ke GitHub, jalankan:
echo   gh repo create epub-metadata-editor --public --source=. --push
echo atau buat repo manual di github.com lalu:
echo   git remote add origin https://github.com/USERNAME/epub-metadata-editor.git
echo   git push -u origin main
