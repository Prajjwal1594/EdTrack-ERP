import sys
import os

# Ensure both root and elwood are on sys.path
base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, 'elwood'))
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('./elwood'))

try:
    from app import create_app
except ImportError:
    from elwood.app import create_app

app = create_app()
handler = app
