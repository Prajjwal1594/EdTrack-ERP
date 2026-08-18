import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'edtrack-secret-key-change-in-production'

    # Postgres connections (Neon/Railway/Render) use 'postgres://' or 'postgresql://'
    # SQLAlchemy 2.x requires 'postgresql://' (uses psycopg2-binary by default)
    is_vercel = bool(os.environ.get('VERCEL'))
    if is_vercel:
        instance_dir = "/tmp"
    else:
        instance_dir = os.path.join(basedir, "instance")
        try:
            os.makedirs(instance_dir, exist_ok=True)
        except OSError:
            instance_dir = "/tmp"

    _db_url = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(instance_dir, "elwood.db")}'

    _engine_options = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
        'pool_timeout': 20,
    }

    # Convert all postgresql / postgres URLs to use pg8000 driver
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql+pg8000://', 1)
    elif _db_url.startswith('postgresql://') and '+pg8000' not in _db_url and '+psycopg2' not in _db_url:
        _db_url = _db_url.replace('postgresql://', 'postgresql+pg8000://', 1)

    # When using pg8000, strip sslmode/ssl query parameters and configure ssl_context
    if '+pg8000' in _db_url:
        import re
        import ssl
        has_ssl = 'sslmode' in _db_url or 'ssl' in _db_url
        _db_url = re.sub(r'[?&]sslmode=[^&]*', '', _db_url)
        _db_url = re.sub(r'[?&]ssl=[^&]*', '', _db_url)
        if '?' not in _db_url and '&' in _db_url:
            _db_url = _db_url.replace('&', '?', 1)
        _db_url = _db_url.rstrip('?').replace('?&', '?').rstrip('&')
        if has_ssl:
            ctx = ssl.create_default_context()
            _engine_options['connect_args'] = {'ssl_context': ctx}

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options

    # Mail config
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@gmail.com')

    # Razorpay config
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'placeholder_id')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'placeholder_secret')

    # App settings
    # NOTE: COLLEGE_NAME has been removed — each college's name comes from the
    # College model (current_user.college.name) to support multi-tenancy.
    LOW_GRADE_THRESHOLD = 40  # % below which notification fires
    ITEMS_PER_PAGE = 20
