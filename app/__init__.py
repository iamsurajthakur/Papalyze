import os
from flask import Flask, session
from dotenv import load_dotenv
from app.models import User
from app.extensions import db, limiter, mail

load_dotenv()


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Load the instance config, if it exists
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_pyfile('config.py', silent=True)

    print(f"SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    mail.init_app(app) 
    
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

    @app.context_processor
    def inject_user():
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        return dict(user=user)
    
    app.debug = True

    return app
