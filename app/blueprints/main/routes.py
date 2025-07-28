from flask import render_template, request, redirect, flash, url_for, session, jsonify, abort, current_app
from app.blueprints.main import bp
from werkzeug.utils import secure_filename
from app.extensions import db, mail
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.utils.token import generate_reset_token
from app.utils.send_email import send_reset_email
from app.utils.helpers import ping_database, login_required
from app.models import User, Subscriber
from flask_mail import Message
from datetime import datetime
import os
import uuid

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    return render_template('main/index.html',user=user, title='Home')

@bp.route('/contact.html', methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        try:
            # Send to Papalyze Gmail
            owner_msg = Message(
                subject="New Contact Form Message",
                sender=("Papalyze", "papalyze@gmail.com"),
                recipients=["papalyze@gmail.com"],
                body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
            )
            mail.send(owner_msg)

            # Auto-reply to the user
            user_msg = Message(
                subject="Thanks for contacting Papalyze",
                sender=("Papalyze", "papalyze@gmail.com"),
                recipients=[email],
                body=f"Hi {name},\n\nThanks for reaching out to Papalyze! We'll get back to you shortly.\n\nYour message:\n\"{message}\"\n\n- Team Papalyze"
            )
            mail.send(user_msg)

            flash("Thanks! Your message has been sent.", "success")
        except Exception as e:
            print(f"[Mail Error] {e}")  # Optional: log the error to console or file
            flash("❌ Something went wrong while sending your message. Please try again later.", "danger")

        return redirect(url_for("main.contact"))

    return render_template("main/contact.html", title="Contact")

@bp.route('/subscribe', methods=["POST"]) 
def subscribe():
    email = request.form.get('email')

    if not email:
        flash("Please provide an email address.", "danger")
        return redirect(url_for('main.index'))

    # Check for existing subscriber
    if Subscriber.query.filter_by(email=email).first():
        flash("You are already subscribed!", "info")
        return redirect(url_for('main.index'))

    try:
        # Save to database
        new_subscriber = Subscriber(email=email)
        db.session.add(new_subscriber)
        db.session.commit()

        # Notify Papalyze
        notify_msg = Message(
            subject="New Papalyze Email Signup",
            sender=("Papalyze", "papalyze@gmail.com"),
            recipients=["papalyze@gmail.com"],
            body=f"New email signup: {email}"
        )
        mail.send(notify_msg)

        # Auto-reply to user
        auto_reply = Message(
            subject="Thanks for subscribing to Papalyze!",
            sender=("Papalyze", "papalyze@gmail.com"),
            recipients=[email],
            body=f"Hi,\n\nThanks for subscribing to Papalyze! We'll keep you updated and contact you if needed.\n\nBest regards,\nTeam Papalyze"
        )
        mail.send(auto_reply)

        flash("Thanks for signing up! A confirmation email has been sent to you.", "success")

    except Exception as e:
        db.session.rollback()
        print(f"Error processing subscription: {e}")
        flash("Failed to process signup. Please try again.", "danger")

    return redirect(url_for('main.index'))


@bp.route('/about.html')
def about():
    return render_template('main/about.html', title='About')

@bp.route('/privacy.html')
def privacy():
    return render_template('main/privacy.html', title='Privacy Policy')

@bp.route('/license.html')
def license():
    return render_template('main/license.html', title='LICENSE')

@bp.route('/term.html')
def term():
    return render_template('main/term.html',title='Term & Condition')

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
    return render_template(
        'main/dashboard.html',
        recent_activities=recent_activities,
        title='Dashboard',
        user=user,
    )

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
@login_required
def upload():
    # Get list of uploaded files from the key 'paper_files' (matches your frontend)
    files = request.files.getlist('paper_files')

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files provided'}), 400

    # Set upload folder based on environment
    if os.environ.get('RENDER'):
        upload_folder = '/tmp'
    else:
        upload_folder = os.path.join(os.getcwd(), 'uploaded_files')
        os.makedirs(upload_folder, exist_ok=True)

    saved_filenames = []

    for file in files:
        if file and file.filename != '':
            if not allowed_file(file.filename):
                return jsonify({'error': f'File type not allowed: {file.filename}'}), 400

            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)

            try:
                file.save(file_path)
                saved_filenames.append(filename)
                print("✅ File saved at:", file_path)
            except Exception as e:
                print("❌ Error saving file:", e)
                return jsonify({'error': 'File saving failed'}), 500

    # Handle checkboxes (for analysis)
    extract_questions = request.form.get('extract_questions') == 'on'
    difficulty_analysis = request.form.get('difficulty_analysis') == 'on'
    topic_classification = request.form.get('topic_classification') == 'on'
    answer_suggestions = request.form.get('answer_suggestions') == 'on'

    # Placeholder for analysis logic on saved_filenames list
    print("Received files:", saved_filenames)
    print("Options:", extract_questions, difficulty_analysis, topic_classification, answer_suggestions)

    return jsonify({"message": f"Analysis complete! Uploaded {len(saved_filenames)} files.", "redirect_url": "/upload"})




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

@bp.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    user = User.query.get(session["user_id"])
    
    name = request.form.get("name")
    if name:
        user.fullname = name

    file = request.files.get('avatar')

    if file and file.filename:
        filename = secure_filename(file.filename)
        if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in current_app.config['ALLOWED_EXTENSIONS']:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400

        ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{ext}"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        upload_path = os.path.join(upload_folder, unique_filename)

        try:
            os.makedirs(upload_folder, exist_ok=True)  # <---- Add this here to create folder if missing
            file.save(upload_path)
            avatar_url = f"/{upload_path.replace(os.sep, '/')}"
            user.avatar_url = avatar_url
        except Exception as e:
            print(f"[Avatar Upload Error] {e}")
            return jsonify({'success': False, 'message': 'Upload failed'}), 500

    db.session.commit()
    return redirect(url_for('main.dashboard'))

