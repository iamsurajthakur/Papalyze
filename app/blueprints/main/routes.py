from flask import render_template, request, redirect, flash, url_for, session, jsonify, abort
from app.blueprints.main import bp
from app.extensions import db
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import os

@bp.route('/')
def index():
    return render_template('main/index.html', title='Home')

@bp.route('/contact.html', methods=["GET","POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        flash("Thanks! Your message has been sent.", "success")
        return redirect(url_for("main.contact"))

    return render_template('main/contact.html', title='Contact')

@bp.route('/about.html')
def about():
    return render_template('main/about.html', title='About')

@bp.route('/features')
def feature():
    if not session.get('user_id'):
        flash("You must be logged in to access this feature.", "warning")
        return redirect(url_for('auth.login'))

    feature_name = request.args.get('type', 'upload')
    return render_template('main/features.html', feature=feature_name)

@bp.route('/ping')
def ping():
    return jsonify({"status": "ok"}), 200

@bp.route('/db_test')
def db_test():
    result = db.session.execute(text('SELECT current_database()'))
    db_name = result.scalar()
    return f"Connected to: {db_name}"

@bp.route('/admin/db_check')
def db_check():
    token = request.args.get('token')
    secret_token = os.getenv('DB_CHECK_TOKEN')  

    # Decode if needed:
    from urllib.parse import unquote
    decoded_token = unquote(secret_token)  

    if token != decoded_token:
        abort(403)  # Forbidden if token invalid

    try:
        db_name = db.session.execute(text('SELECT current_database()')).scalar()
        db_user = db.session.execute(text('SELECT current_user')).scalar()
        db_version = db.session.execute(text('SHOW server_version')).scalar()
        conn_info = db.session.execute(text("""
            SELECT inet_client_addr() as client_ip, inet_server_addr() as server_ip
        """)).first()

        client_ip = conn_info.client_ip
        server_ip = conn_info.server_ip

        return (
            f"<h3>Database Connection Info</h3>"
            f"<ul>"
            f"<li>Connected Database: <b>{db_name}</b></li>"
            f"<li>Current DB User: <b>{db_user}</b></li>"
            f"<li>PostgreSQL Version: <b>{db_version}</b></li>"
            f"<li>Client IP: <b>{client_ip}</b></li>"
            f"<li>Server IP: <b>{server_ip}</b></li>"
            f"</ul>"
        )
    except OperationalError as oe:
        return (
            "<h3 style='color:red;'>Database Connection Error</h3>"
            "<p>Unable to connect to the database. Please check your database service.</p>"
            f"<p>Error details: {oe}</p>"
        )
    except Exception as e:
        return (
            "<h3 style='color:red;'>Unexpected Error</h3>"
            f"<p>{e}</p>"
        )
