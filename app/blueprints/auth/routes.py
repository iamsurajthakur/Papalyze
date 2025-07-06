from flask import render_template, redirect, url_for, session, request, flash
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import OperationalError
from app.utils.helpers import ping_database
from app.blueprints.auth import auth_bp
from app.extensions import db
from app.models import User

@auth_bp.route('/login.html', methods=['GET', 'POST'])
def login():
    try:
        ping_database()
    except OperationalError:
        return "Database is waking up, please try again in a few seconds.", 503
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))  
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))


    return render_template('login.html', show_navbar=False)



@auth_bp.route('/signin.html', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash("Passwords do not match.", "warning")
            return redirect(url_for('auth.signin'))

        existing_user = User.query.filter((User.email == email)).first()
        if existing_user:
            flash("User already exists.", "danger") 
            return redirect(url_for('auth.login'))
        
        hashed_password = generate_password_hash(password)

        new_user = User(email=email, fullname=fullname,password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Signup successful! Please log in.", "success")
        return redirect(url_for('auth.login'))
        

    return render_template('signin.html', show_navbar=False)



@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
