import os
from flask import Flask, session
from dotenv import load_dotenv
from app.models import User
from app.extensions import db, limiter, mail
from flask_login import current_user
from app.config import config_by_name
from sqlalchemy.exc import OperationalError, DisconnectionError
import logging

if os.environ.get('FLASK_ENV') == 'development':
    print("Debug mode ON. Doing development-specific setup...")
load_dotenv()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Get config name
    config_name = os.getenv('FLASK_ENV', 'default')
    if os.environ.get('RENDER'):
        config_name = 'production'

    # Load configuration
    config_class = config_by_name.get(config_name, config_by_name['default'])
    # Create an instance of the config class
    config_instance = config_class()
    app.config.from_object(config_instance)

    # Call init_app if it exists
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)

    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    # Log important paths
    app.logger.info(f"Starting app with {config_name} configuration")
    app.logger.info(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")

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

    # Enhanced context processor with error handling
    @app.context_processor
    def inject_user():
        user = None
        if 'user_id' in session:
            try:
                # Add retry logic for database connection issues
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        user = User.query.get(session['user_id'])
                        break  # Success, exit retry loop
                    except (OperationalError, DisconnectionError) as e:
                        app.logger.warning(f"Database connection error on attempt {attempt + 1}: {e}")
                        if attempt == max_retries - 1:
                            # Last attempt failed, log error and continue without user
                            app.logger.error(f"Failed to load user after {max_retries} attempts: {e}")
                            user = None
                        else:
                            # Wait a bit before retrying
                            import time
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            
                            # Try to dispose the connection pool to force new connections
                            try:
                                db.engine.dispose()
                            except Exception as dispose_error:
                                app.logger.debug(f"Could not dispose connection pool: {dispose_error}")
                                
            except Exception as e:
                # Catch any other unexpected errors
                app.logger.error(f"Unexpected error in inject_user: {e}")
                user = None
                
        return dict(user=user)

    # Add database error handlers
    @app.errorhandler(OperationalError)
    def handle_db_connection_error(e):
        app.logger.error(f"Database operational error: {e}")
        # Try to dispose and recreate connections
        try:
            db.engine.dispose()
        except:
            pass
        return "Database connection error. Please try again.", 503

    @app.errorhandler(DisconnectionError)
    def handle_db_disconnection_error(e):
        app.logger.error(f"Database disconnection error: {e}")
        # Try to dispose and recreate connections
        try:
            db.engine.dispose()
        except:
            pass
        return "Database disconnection error. Please try again.", 503

    # Add a health check route for monitoring
    @app.route('/health')
    def health_check():
        try:
            # Simple database connectivity check
            db.session.execute('SELECT 1')
            db.session.commit()
            return {'status': 'healthy', 'database': 'connected'}, 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return {'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}, 503

    # Add before_request handler to ensure database connections are healthy
    @app.before_request
    def ensure_db_connection():
        try:
            # Ping the database to ensure connection is alive
            # This uses the pool_pre_ping setting from config but adds extra safety
            db.session.execute('SELECT 1')
        except (OperationalError, DisconnectionError):
            # Connection is stale, dispose and let SQLAlchemy create new ones
            try:
                db.engine.dispose()
                app.logger.info("Disposed stale database connections")
            except Exception as e:
                app.logger.warning(f"Could not dispose connections: {e}")
        except Exception as e:
            # Log but don't fail the request for other database issues
            app.logger.debug(f"Database ping failed: {e}")

    app.debug = config_name == 'development'
    return app