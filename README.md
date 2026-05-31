# EPUB Metadata Editor

A desktop application for editing EPUB e-book metadata, built with Python and PyQt6.  
Also includes a **web app** (Flask) for mobile-friendly editing via browser.

## Features

- Read and edit EPUB metadata (title, author, publisher, date, description, subjects, series, etc.)
- Support for EPUB2 and EPUB3 formats
- Cover image replacement and removal
- Edit auxiliary files (TOC, NCX, page-map)
- Modern desktop UI with gradient background and card-style layout
- Mobile-friendly web UI for editing on any device
- Metadata search prompt template for AI assistants

## Requirements

- Python 3.10+
- PyQt6 >= 6.5.0
- qtawesome
- Flask >= 2.3.0 (for web app)

## Desktop App

```bash
pip install -r requirements.txt
python main.py
```

## Web App (Local)

```bash
cd web_app
pip install -r requirements.txt
python app.py
```

Open browser to `http://localhost:5000`.

## Deploy to PythonAnywhere (Free, No Credit Card)

### 1. Sign Up
- Go to [pythonanywhere.com](https://www.pythonanywhere.com)
- Sign up with email (free tier)
- Confirm your email address

### 2. Clone the Repository
Open a **Bash console** in PythonAnywhere and run:

```bash
cd ~
git clone https://github.com/wopxrr/epub-metadata-editor.git
cd epub-metadata-editor
pip install --user -r web_app/requirements.txt
```

### 3. Create Web App
1. Go to the **Web** tab in PythonAnywhere
2. Click **"Add a new web app"**
3. Choose **"Manual configuration"**
4. Select **Python 3.10** (or the latest available)
5. Click **Next** to finish the wizard

### 4. Configure WSGI File
1. In the Web tab, click the link to your **WSGI configuration file**
   (e.g. `/var/www/USERNAME_pythonanywhere_com_wsgi.py`)
2. **Delete all existing content** and paste this exact code:

```python
import sys
import os

# Add project paths
sys.path.insert(0, '/home/USERNAME/epub-metadata-editor/web_app/src')
sys.path.insert(0, '/home/USERNAME/epub-metadata-editor/web_app')

from app import app as application
```

**Important:** Replace `USERNAME` with your actual PythonAnywhere username!

### 5. Set Virtualenv (Optional but Recommended)
1. In the Web tab, find the **Virtualenv** section
2. Enter: `/home/USERNAME/.local` (or leave blank if you used `--user` install)

### 6. Reload
Click the **Reload** button on the Web tab.

Your app will be live at: `https://USERNAME.pythonanywhere.com`

Open it on your phone and **Add to Home Screen** for an app-like experience!

## Running Tests

```bash
python -m pytest tests/
```

## License

MIT
