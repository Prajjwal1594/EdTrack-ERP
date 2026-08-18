import threading
from flask import current_app
from flask_mail import Message
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        try:
            # If current_app has no MAIL_USERNAME config or it is a placeholder, print to terminal
            if not app.config.get('MAIL_USERNAME') or app.config['MAIL_USERNAME'].startswith('your-email'):
                print("\n" + "="*50)
                print(f"📧 EMAIL GENERATED (Not Sent - SMTP Unconfigured)")
                print(f"To: {', '.join(msg.recipients)}")
                print(f"Subject: {msg.subject}")
                print(f"Body:\n{msg.body}")
                print("="*50 + "\n")
            else:
                mail.send(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")

def send_email(subject, recipients, text_body, sender=None, html_body=None):
    if not recipients:
        return
    if sender is None:
        sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@gmail.com')
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
    
    # Run email sending in a background thread so the UI is not blocked
    app = current_app._get_current_object()
    thread = threading.Thread(target=send_async_email, args=(app, msg))
    thread.start()
