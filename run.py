import re
from flask import flash, redirect, url_for
from app import create_app
from app.config import Config

# Initialize the Flask app using the provided config
app = create_app(Config)

@app.errorhandler(429)
def ratelimit_handler(e):
    """
    Custom handler for HTTP 429 Too Many Requests.
    Calculates cooldown period from rate limit description,
    formats a human-readable time message, and flashes it to the user.
    """
    default_cooldown = 300  # fallback in seconds (5 minutes)
    cooldown_seconds = default_cooldown

    # Attempt to extract rate limit info using regex from the error description
    if hasattr(e, "description"):
        match = re.search(r'(\d+)\s+per\s+(\d+)\s+(second|minute|hour)', str(e.description))
        if match:
            _, time_value, time_unit = match.groups()
            time_value = int(time_value)

            if time_unit == "second":
                cooldown_seconds = time_value
            elif time_unit == "minute":
                cooldown_seconds = time_value * 60
            elif time_unit == "hour":
                cooldown_seconds = time_value * 3600
            # else keep default cooldown
    # else keep default cooldown

    # Format cooldown time into a human-readable message
    minutes, seconds = divmod(cooldown_seconds, 60)
    if cooldown_seconds < 60:
        time_msg = f"{cooldown_seconds} second(s)"
    elif seconds == 0:
        time_msg = f"{minutes} minute(s)"
    else:
        time_msg = f"{minutes} minute(s) and {seconds} second(s)"

    flash(f"Too many login attempts. Try again in {time_msg}.", "danger")
    return redirect(url_for('auth.signin'))

if __name__ == "__main__":
    app.run(debug=True)
