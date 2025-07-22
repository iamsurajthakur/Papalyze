from app import create_app
from app.config import Config
from flask import flash, redirect, url_for
import re


app = create_app(Config)


@app.errorhandler(429)
def ratelimit_handler(e):
    print(">>> Entered 429 error handler")

    print(f">>> Exception description: {e.description}")
    print(f">>> Exception type: {type(e)}")
    
    cooldown_seconds = 300
    print(">>> Default fallback cooldown: 300 seconds")

    if hasattr(e, "description"):
        match = re.search(r'(\d+)\s+per\s+(\d+)\s+(second|minute|hour)', str(e.description))
        print(f">>> Regex match result: {match}")
        if match:
            limit_count = int(match.group(1))     
            time_value = int(match.group(2))     
            time_unit = match.group(3)            

            print(f">>> Parsed values - limit_count: {limit_count}, time_value: {time_value}, time_unit: {time_unit}")

            if time_unit == "second":
                cooldown_seconds = time_value
            elif time_unit == "minute":
                cooldown_seconds = time_value * 60
            elif time_unit == "hour":
                cooldown_seconds = time_value * 3600

            print(f">>> Updated cooldown_seconds: {cooldown_seconds}")
        else:
            print(">>> No match found in description, using fallback.")
    else:
        print(">>> No description found on exception.")

    minutes = cooldown_seconds // 60
    seconds = cooldown_seconds % 60

    if cooldown_seconds < 60:
        time_msg = f"{cooldown_seconds} second(s)"
    elif seconds == 0:
        time_msg = f"{minutes} minute(s)"
    else:
        time_msg = f"{minutes} minute(s) and {seconds} second(s)"

    print(f">>> Final time_msg: {time_msg}")

    flash(f"Too many login attempts. Try again in {time_msg}.", "danger")
    return redirect(url_for('auth.signin'))

if __name__ == "__main__":
    app.run(debug=True)
