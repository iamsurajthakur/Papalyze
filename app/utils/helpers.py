from tenacity import retry, stop_after_attempt, wait_fixed
from app.extensions import db
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from flask import session, redirect, url_for, flash


@retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
def ping_database():
    db.session.execute(text("SELECT 1"))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login')) 
        return f(*args, **kwargs)
    return decorated_function