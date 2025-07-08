from flask import render_template, request, redirect, flash, url_for, session, jsonify, abort
from app.blueprints.main import bp
from app.extensions import db
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.utils.token import generate_reset_token
from app.utils.send_email import send_reset_email
from app.utils.helpers import ping_database, login_required
from app.models import User
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

@bp.route('/dashboard.html')
@login_required
def dashboard():
    return render_template('main/dashboard.html', title='Dashboard')

@bp.route('/ping')
def ping():
    return jsonify({"status": "ok"}), 200

@bp.route('/db_test')
def db_test():
    try:
        ping_database() 
        result = db.session.execute(text('SELECT current_database()'))
        db_name = result.scalar()
        return f"Connected to: {db_name}"
    except OperationalError:
        return "Database is waking up or unavailable. Please refresh in a few seconds.", 503


@bp.route('/admin/db_check')
def db_check():
    token = request.args.get('token')
    secret_token = os.getenv('DB_CHECK_TOKEN')  

    from urllib.parse import unquote
    decoded_token = unquote(secret_token)  

    if token != decoded_token:
        abort(403)

    try:
        ping_database()  # wakes DB if needed

        db_name = db.session.execute(text('SELECT current_database()')).scalar()
        db_user = db.session.execute(text('SELECT current_user')).scalar()
        db_version = db.session.execute(text('SHOW server_version')).scalar()
        conn_info = db.session.execute(text("""
            SELECT inet_client_addr() as client_ip, inet_server_addr() as server_ip
        """)).first()

        return (
            f"<h3>Database Connection Info</h3>"
            f"<ul>"
            f"<li>Connected Database: <b>{db_name}</b></li>"
            f"<li>Current DB User: <b>{db_user}</b></li>"
            f"<li>PostgreSQL Version: <b>{db_version}</b></li>"
            f"<li>Client IP: <b>{conn_info.client_ip}</b></li>"
            f"<li>Server IP: <b>{conn_info.server_ip}</b></li>"
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
@bp.route('/forgot_password.html', methods=["GET", "POST"])
def forgot_password():
    reset_url = None
    email = None  # <-- Ensure email is always defined

    if request.method == "POST":
        email = request.form.get("email")

        if not email:
            flash("Please enter your email address.", "warning")
            return redirect(url_for("main.forgot_password"))

        user = User.query.filter_by(email=email).first()

        if user:
            token = generate_reset_token(email)
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            return render_template('main/forgot_password.html', reset_url=reset_url, email=email, show_navbar=False)

        flash("No account found with that email.", "warning")
        return redirect(url_for("main.forgot_password"))

    return render_template('main/forgot_password.html', reset_url=reset_url, email=email, show_navbar=False)
