from flask import render_template, request, redirect, flash, url_for, session, jsonify
from app.blueprints.main import bp

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