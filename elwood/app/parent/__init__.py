from flask import Blueprint
bp = Blueprint('parent', __name__)
from app.parent import routes
