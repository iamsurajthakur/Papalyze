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
from app.blueprints.analyzer import analyze_enhanced_topic_repetitions
from app.centralizepath import config
from pathlib import Path
import PyPDF2
from app.services.summarize import generate_summary
import pytesseract
from PIL import Image
from keybert import KeyBERT

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if os.environ.get('RENDER'):
        image_folder_path = '/tmp'
else:
    image_folder_path = os.path.join(os.getcwd(), 'uploaded_files')

os.makedirs(image_folder_path, exist_ok=True)

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

@bp.route('/error.html')
def error():
    return render_template('error.html', title='Error')

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

@bp.route("/api/summarize", methods=["POST"])
def summarize():
    input_mode = request.form.get("input_mode")

    # Get text input
    if input_mode == "text":
        text = request.form.get("noteInput", "")
        if not text.strip():
            return jsonify({"error": "No text provided"}), 400

    # Get file input
    elif input_mode == "file":
        file = request.files.get("fileUpload")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400
        if file.filename.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file)
            text = "".join([page.extract_text() for page in reader.pages])
        else:
            return jsonify({"error": "Unsupported file type"}), 400
    else:
        return jsonify({"error": "Invalid input mode"}), 400

    # Generate real AI summary
    summary_result = generate_summary(text)
    return jsonify({"summary": summary_result})

@bp.route('/extract_text', methods=["POST"])
@login_required  # optional, if you want only logged-in users
def extract_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(image_folder_path, unique_filename)

    try:
        # Save the uploaded file
        file.save(filepath)

        # Extract text with pytesseract
        if filename.lower().endswith('pdf'):
            from pdf2image import convert_from_path
            pages = convert_from_path(filepath, dpi=300)
            text = ""
            for page in pages:
                text += pytesseract.image_to_string(page)
        else:
            text = pytesseract.image_to_string(Image.open(filepath))

        return jsonify({"text": text})

    except Exception as e:
        print(f"[OCR Error] {e}")
        return jsonify({"error": str(e)}), 500
    
@bp.route('/predict_topics', methods=['POST'])
@login_required
def predict_topics():


    data = request.get_json()
    text = data.get('text', '')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    kw_model = KeyBERT()
    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 2),  # allow single + bi-grams
        stop_words='english',
        top_n=10
    )
    topics = [k[0] for k in keywords]

    return jsonify({"topics": topics})
