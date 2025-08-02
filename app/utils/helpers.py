from functools import wraps

from flask import session, redirect, url_for, flash
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_fixed

from app.extensions import db


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def ping_database():
    """
    Ping the database to ensure it's responsive.
    Retries up to 3 times with a 2-second wait between attempts.
    
    Raises:
        SQLAlchemyError: If the DB query fails even after retries.
    """
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        db.session.rollback()
        raise e


def login_required(f):
    """
    Decorator that restricts access to logged-in users only.

    If the user is not logged in (i.e. 'user_id' not in session),
    they will be redirected to the login page with a flash message.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    
    return decorated_function
