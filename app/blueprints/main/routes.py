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
import tempfile
from app.blueprints.analyzer import analyze_enhanced_topic_repetitions


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

@bp.route('/report.html')
def report():

    try:
        # Collect images AND pdfs
        all_files = [
            os.path.join(image_folder_path, f)
            for f in os.listdir(image_folder_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.pdf'))
        ]
    except OSError as e:
        current_app.logger.error(f"Error accessing upload folder: {e}")
        return render_template('error.html', message="Upload folder access error.")

    if not all_files:
        return render_template('error.html', message="No valid files found (PDF or image).")

    # Prepare final list of image paths
    final_image_files = []

    from app.utils.helpers import convert_pdf_to_images  # import your function

    for file_path in all_files:
        if file_path.lower().endswith(".pdf"):
            try:
                images = convert_pdf_to_images(file_path)
                final_image_files.extend(images)
            except Exception as e:
                current_app.logger.error(f"PDF conversion failed: {e}")
        else:
            final_image_files.append(file_path)

    if not final_image_files:
        return render_template('error.html', message="No valid images available for analysis after processing.")

    # Temporarily override: analyze_enhanced_topic_repetitions only accepts folder,
    # so put converted images in a temp folder and pass that folder instead
    from tempfile import TemporaryDirectory
    import shutil

    with TemporaryDirectory() as temp_dir:
        for img_path in final_image_files:
            shutil.copy(img_path, temp_dir)

        try:
            analysis_result = analyze_enhanced_topic_repetitions(
                temp_dir,
                use_lemmatization=True,
                verbose=False
            )
        except Exception as e:
            current_app.logger.error(f"Analysis failed: {e}")
            return render_template('error.html', message="Analysis failed.")

    if not analysis_result:
        return render_template('error.html', message="Analysis returned no results.")

    extracted_texts = analysis_result['analyzer'].extracted_texts

    confidence_stats = {
        'high_confidence_count': len([f for f in extracted_texts if f['confidence'] >= 85]),
        'medium_confidence_count': len([f for f in extracted_texts if 70 <= f['confidence'] < 85]),
        'low_confidence_count': len([f for f in extracted_texts if f['confidence'] < 70])
    }

    total_words = sum(f['word_count'] for f in extracted_texts)
    avg_words_per_doc = total_words // len(extracted_texts)
    avg_ocr_confidence = sum(f['confidence'] for f in extracted_texts) / len(extracted_texts)

    return render_template('report.html',
        analysis_result=analysis_result,
        generation_date=datetime.now().strftime("%B %d, %Y"),
        confidence_stats=confidence_stats,
        total_words=total_words,
        avg_words_per_doc=avg_words_per_doc,
        avg_ocr_confidence=avg_ocr_confidence
    )


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
    
@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    files = request.files.getlist('paper_files')

    if not files or all(f.filename == '' for f in files):
        if request.is_json or request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']:
            return jsonify({'status': 'error', 'message': 'No files provided'}), 400
        return render_template('report.html', error="No files provided")


    saved_filenames = []

    for file in files:
        if file and file.filename != '':
            if not allowed_file(file.filename):
                return jsonify({'status': 'error', 'message': f'File type not allowed: {file.filename}'}), 400
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(image_folder_path, filename)

            try:
                file.save(file_path)
                saved_filenames.append(filename)
            except Exception as e:
                current_app.logger.error(f"Failed to save file {filename}: {e}")
                return jsonify({'status': 'error', 'message': 'File saving failed'}), 500

    extract_questions = request.form.get('extract_questions') == 'on'
    difficulty_analysis = request.form.get('difficulty_analysis') == 'on'
    topic_classification = request.form.get('topic_classification') == 'on'
    answer_suggestions = request.form.get('answer_suggestions') == 'on'

    # Run analysis on the permanent upload folder
    result = analyze_enhanced_topic_repetitions(
        image_folder_path,
        debug=False,
        use_lemmatization=True,
        verbose=False
    )

    if not result:
        return jsonify({'status': 'error', 'message': 'Analysis failed or no valid files'}), 500

    return jsonify({
        'status': 'success',
        'message': f'Analysis complete! Uploaded {len(saved_filenames)} files.',
        'summary': result.get("summary", {}),
        'predictions': result.get("predictions", []),
        'redirect_url': '/report.html'
    }), 200






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

