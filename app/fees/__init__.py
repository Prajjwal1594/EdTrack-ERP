from flask import Blueprint
bp = Blueprint('fees', __name__)
from app.fees import routes
