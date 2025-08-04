from flask import Blueprint

bp = Blueprint('analyzer', __name__, template_folder='templates')

from app.blueprints.analyzer import routes
from .analyze import analyze_enhanced_topic_repetitions
