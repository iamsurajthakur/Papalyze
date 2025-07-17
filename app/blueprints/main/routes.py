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
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    return render_template('main/index.html',user=user, title='Home')

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

@bp.route('/privacy.html')
def privacy():
    return render_template('main/privacy.html', title='Privacy Policy')

@bp.route('/license.html')
def license():
    return render_template('main/license.html', title='LICENSE')

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
    user = User.query.get(session["user_id"])
    recent_activities = [
        {"icon": "file-text", "message": "Math Paper 2023 analyzed", "time": "2 hours ago"},
        {"icon": "target", "message": "Physics topics predicted", "time": "5 hours ago"},
        {"icon": "bar-chart-3", "message": "Chemistry report generated", "time": "1 day ago"}
    ]
    return render_template('main/dashboard.html',recent_activities=recent_activities, title='Dashboard', user=user)

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
    
@bp.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('paper_file')
    extract_questions = request.form.get('extract_questions') == 'on'
    difficulty_analysis = request.form.get('difficulty_analysis') == 'on'
    topic_classification = request.form.get('topic_classification') == 'on'
    answer_suggestions = request.form.get('answer_suggestions') == 'on'

    # Do processing here...
    print("Received:", file.filename, extract_questions, difficulty_analysis, topic_classification, answer_suggestions)

    # Simulate success
    return jsonify({"message": "Analysis complete!", "redirect_url": "/upload"})

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
    
            email_sent = send_reset_email(user.email, reset_url)
            if email_sent:
                return render_template('main/forgot_password.html', reset_url=reset_url, email=email, show_navbar=False)
            else:
                flash("Failed to send reset email. Please try again later.", "danger")
                return redirect(url_for("main.forgot_password"))

        flash("No account found with that email.", "warning")
        return redirect(url_for("main.forgot_password"))

    return render_template('main/forgot_password.html', reset_url=reset_url, email=email, show_navbar=False)


