from flask import Blueprint

auth_bp = Blueprint('auth', __name__, template_folder='templates')

from app.blueprints.auth import routes  # import routes to register them
