import sys
import os

# Add web_app/src to path so epub_handler can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_app', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_app'))

from app import app
application = app
