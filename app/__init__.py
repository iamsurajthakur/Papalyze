import os
from flask import Flask

def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Load the default configuration
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'pap.sqlite'),
        DEBUG=True,
    )
    
    # Load the instance config, if it exists
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_pyfile('config.py', silent=True)
    
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
