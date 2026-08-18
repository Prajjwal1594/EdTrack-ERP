from flask import Blueprint

bp = Blueprint('infra', __name__)

from app.infra import routes
