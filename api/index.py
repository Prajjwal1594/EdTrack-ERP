import sys
import os

base_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.dirname(base_dir)

sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'elwood'))
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('./elwood'))

try:
    from app import create_app
except ImportError:
    from elwood.app import create_app

app = create_app()
handler = app
