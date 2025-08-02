from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def generate_reset_token(email):
    """
    Generate a time-sensitive token for password reset.

    Args:
        email (str): User's email address.

    Returns:
        str: A secure token string.
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset')


def confirm_reset_token(token, expiration=3600):
    """
    Validate a password reset token and retrieve the associated email.

    Args:
        token (str): The token to validate.
        expiration (int): Token expiration time in seconds (default: 1 hour).

    Returns:
        str | None: The email if valid, None if invalid or expired.
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return serializer.loads(token, salt='password-reset', max_age=expiration)
    except Exception:
        return None
