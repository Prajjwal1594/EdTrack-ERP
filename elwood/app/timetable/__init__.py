from flask import Blueprint

bp = Blueprint('timetable', __name__)

from app.timetable import routes
