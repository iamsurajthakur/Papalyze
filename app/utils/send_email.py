import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_reset_email(to_email, reset_url):
    """
    Sends a password reset email via SendGrid.

    Args:
        to_email (str): Recipient's email address.
        reset_url (str): Unique reset URL for the user.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    message = Mail(
        from_email='suraj.tech.in@gmail.com',
        to_emails=to_email,
        subject='Password Reset for Papalyze',
        html_content=f"""
            <p>Hello,</p>
            <p>You requested a password reset. Click the link below to reset your password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>If you did not request this, please ignore this email.</p>
        """
    )

    try:
        sg = SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        
        # Optionally log for diagnostics (remove in prod if not needed)
        print(f"[SendGrid] Status: {response.status_code}")
        return response.status_code in (200, 202)
    
    except Exception as e:
        print(f"[SendGrid] Email sending failed: {e}")
        return False
