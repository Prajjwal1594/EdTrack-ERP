from flask import Blueprint

bp = Blueprint('it_admin', __name__)

from app.it_admin import routes
