from flask import render_template, redirect, url_for, session
from app.blueprints.auth import auth_bp

@auth_bp.route('/login.html')
def login():
    return render_template('login.html', show_navbar=False)

@auth_bp.route('/signin.html')
def signin():
    return render_template('signin.html', show_navbar=False)

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None) 
    return redirect(url_for('main.index'))  