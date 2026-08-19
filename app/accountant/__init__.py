from flask import Blueprint

bp = Blueprint('accountant', __name__)

from app.accountant import routes
