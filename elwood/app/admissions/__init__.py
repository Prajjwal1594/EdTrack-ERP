from flask import Blueprint

bp = Blueprint('admissions', __name__)

from app.admissions import routes
