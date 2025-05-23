from flask import Blueprint

bp = Blueprint('analyzer', __name__)

from app.blueprints.analyzer import routes
