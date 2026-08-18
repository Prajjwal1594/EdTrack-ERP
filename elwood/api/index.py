"""
Vercel serverless entry point.
Exposes the Flask WSGI app as `app` for Vercel's Python runtime.
"""
import sys
import os

# Ensure the project root (one level up from api/) is on the Python path
# so that `from app import create_app` and `import config` resolve correctly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
