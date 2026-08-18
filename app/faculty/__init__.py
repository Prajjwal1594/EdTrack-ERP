from flask import Blueprint
bp = Blueprint('faculty', __name__)
from app.faculty import routes
