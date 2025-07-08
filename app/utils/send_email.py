import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_reset_email(to_email, reset_url):
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
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(f"Email sent, status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
