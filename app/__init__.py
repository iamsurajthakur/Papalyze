import os
from flask import Flask
from dotenv import load_dotenv
from app.extensions import db, limiter

load_dotenv()


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Load the instance config, if it exists
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_pyfile('config.py', silent=True)
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Register blueprints
    from app.blueprints.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.blueprints.analyzer import bp as analyzer_bp
    app.register_blueprint(analyzer_bp, url_prefix='/analyzer')
    
    from app.blueprints.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')  
    
    app.debug = True

    return app
