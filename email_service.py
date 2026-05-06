import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Email configuration
EMAIL_SERVICE = os.getenv('EMAIL_SERVICE', 'smtp')
SMTP_HOST = os.getenv('SMTP_HOST', 'sandbox.smtp.mailtrap.io')
SMTP_PORT = int(os.getenv('SMTP_PORT', '2525'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@rsvpevent.com')
SEND_CONFIRMATION_EMAIL = os.getenv('SEND_CONFIRMATION_EMAIL', 'true').lower() == 'true'


def send_email(to_email, subject, html_content, attachments=None):
    """Send email using SMTP"""
    if not SEND_CONFIRMATION_EMAIL:
        print(f"Email sending disabled - skipping {subject}")
        return True
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email

        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))

        # Attach files if provided
        if attachments:
            for filename, content, content_type in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                msg.attach(part)

        # Send email via SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()  
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())


        print(f"Email sent to {to_email} - {subject}")
        return True

    except Exception as e:
        print(f" Error sending email: {e}")
        return False


def send_confirmation_email(registration, event=None):
    """Send confirmation email with event details"""
    try:
        if not registration.get('email'):
            print("No email address provided")
            return False
        
        html_content = generate_confirmation_email_html(registration, event)
        event_name = event.get('name', 'Event') if event else 'Event'
        
        send_email(
            registration['email'],
            f'Registration Confirmed - {event_name} ',
            html_content
        )
        return True
    except Exception as e:
        print(f"Error sending confirmation email: {e}")
        return False


def send_ticket_email(registration):
    """Send ticket email with Google Wallet support"""
    try:
        html_content = generate_ticket_email_html(registration)
        send_email(
            registration['email'],
            f"Your {registration['ticket']} Ticket - Event Registration",
            html_content
        )
    except Exception as e:
        print(f"Error sending ticket email: {e}")
        raise


def send_admin_notification(registration):
    """Send admin notification"""
    try:
        admin_emails = os.getenv('ADMIN_EMAILS', EMAIL_FROM).split(',')
        html_content = generate_admin_notification_html(registration)

        for admin_email in admin_emails:
            send_email(
                admin_email.strip(),
                f"New Registration: {registration['name']}",
                html_content
            )
    except Exception as e:
        print(f"Error sending admin notification: {e}")



# EMAIL TEMPLATES


def generate_confirmation_email_html(reg, event=None):
    """Generate confirmation email HTML"""
    timestamp = datetime.fromisoformat(reg.get('timestamp', datetime.now().isoformat()))
    date_str = timestamp.strftime('%A, %B %d, %Y at %I:%M %p')
    ticket_id = reg.get('id', 'N/A')[:8].upper()
    
    event_name = event.get('name', 'Event') if event else 'Event'
    event_desc = event.get('description', '') if event else ''
    
    # Build registration details table
    details_html = ""
    
    # Standard fields
    standard_fields = ['name', 'email', 'ticket', 'dietary']
    for field in standard_fields:
        if field in reg and reg[field]:
            label = field.replace('_', ' ').title()
            value = escape_html(str(reg[field]))
            if field == 'dietary':
                label = 'Dietary Requirements'
            details_html += f"""
            <tr>
                <td style="padding: 10px; font-weight: bold; background: #f5f3ee; width: 150px;">{label}:</td>
                <td style="padding: 10px;">{value}</td>
            </tr>
            """
    
    # Custom fields
    if 'custom_fields' in reg and reg['custom_fields']:
        for key, value in reg['custom_fields'].items():
            key_display = key.replace('_', ' ').title()
            value_display = escape_html(str(value)) if value else 'N/A'
            details_html += f"""
            <tr>
                <td style="padding: 10px; font-weight: bold; background: #f5f3ee; width: 150px;">{key_display}:</td>
                <td style="padding: 10px;">{value_display}</td>
            </tr>
            """

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; }}
          .container {{ max-width: 600px; margin: 0 auto; background: #fff; }}
          .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center; border-radius: 8px 8px 0 0; }}
          .header h1 {{ margin: 0; font-size: 28px; }}
          .content {{ padding: 30px; }}
          .event-info {{ background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #667eea; }}
          .ticket-box {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center; }}
          .ticket-id {{ font-size: 32px; font-weight: bold; letter-spacing: 2px; margin: 10px 0; font-family: 'Courier New', monospace; }}
          .ticket-id-label {{ font-size: 12px; opacity: 0.9; }}
          table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
          .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #ddd; background: #f9f9f9; border-radius: 0 0 8px 8px; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🎉 Registration Confirmed!</h1>
            <p>Thank you for registering</p>
          </div>
          
          <div class="content">
            <p>Hello <strong>{escape_html(reg.get('name', 'Attendee'))}</strong>,</p>
            
            <p>We're excited to have you! Your registration for <strong>{escape_html(event_name)}</strong> has been confirmed.</p>
            
            <div class="event-info">
              <h3 style="margin-top: 0;">{escape_html(event_name)}</h3>
              {f'<p>{escape_html(event_desc)}</p>' if event_desc else ''}
            </div>
            
            <div class="ticket-box">
              <div class="ticket-id-label">Your Ticket ID</div>
              <div class="ticket-id">{ticket_id}</div>
              <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.9;">Please keep this ID handy for check-in</p>
            </div>
            
            <h3>Your Registration Details:</h3>
            <table>
              {details_html}
            </table>
            
            <p style="background: #f0f4ff; padding: 15px; border-radius: 5px; border-left: 4px solid #667eea;">
              <strong>Next Steps:</strong> Please check your email for additional information and instructions before the event. 
              If you have any questions, please reply to this email.
            </p>
            
            <p>See you at the event!</p>
            <p>Best regards,<br/><strong>The Event Team</strong></p>
          </div>
          
          <div class="footer">
            <p>&copy; {datetime.now().year} Event Registration System | All rights reserved</p>
          </div>
        </div>
      </body>
    </html>
    """


def generate_ticket_email_html(reg):
    """Generate ticket email HTML"""
    qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={reg['id']}"

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; }}
          .container {{ max-width: 600px; margin: 0 auto; }}
          .ticket {{ background: linear-gradient(135deg, #c8441c 0%, #a5350f 100%); color: white; padding: 30px; border-radius: 8px; margin: 20px 0; }}
          .ticket-header {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
          .ticket-detail {{ display: flex; justify-content: space-between; margin: 10px 0; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.3); }}
          .ticket-label {{ opacity: 0.9; }}
          .ticket-value {{ font-weight: bold; }}
          .qr-code {{ text-align: center; margin: 20px 0; }}
          .content {{ padding: 30px; border: 1px solid #ddd; }}
          .wallet-button {{ display: inline-block; background: #000; color: white; padding: 12px 24px; border-radius: 5px; margin: 10px 0; text-decoration: none; font-weight: bold; }}
          .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="content">
            <h1>Your Event Ticket</h1>
            <p>Hi <strong>{escape_html(reg['name'])}</strong>,</p>
            <p>Your ticket is ready! Here are your details:</p>
          </div>
          
          <div class="ticket">
            <div class="ticket-header">Event Ticket</div>
            <div class="ticket-detail">
              <span class="ticket-label">Name:</span>
              <span class="ticket-value">{escape_html(reg['name'])}</span>
            </div>
            <div class="ticket-detail">
              <span class="ticket-label">Ticket Type:</span>
              <span class="ticket-value">{reg['ticket']}</span>
            </div>
            <div class="ticket-detail">
              <span class="ticket-label">Ticket ID:</span>
              <span class="ticket-value">{reg['id'][:8].upper()}</span>
            </div>
            {f"<div class='ticket-detail'><span class='ticket-label'>Dietary:</span><span class='ticket-value'>{escape_html(reg['dietary'])}</span></div>" if reg['dietary'] and reg['dietary'] != 'None' else ''}
            
            <div class="qr-code">
              <p style="font-size: 12px; opacity: 0.9;">Show this QR code at entry:</p>
              <img src="{qr_code_url}" alt="Ticket QR Code" />
              <p style="font-size: 12px; opacity: 0.9;">{reg['id']}</p>
            </div>
          </div>
          
          <div class="content">
            <p><strong>Add to Your Digital Wallet:</strong></p>
            <p>
              <a href="#" class="wallet-button">Add to Apple Wallet</a><br>
              <a href="#" class="wallet-button">▶Add to Google Wallet</a>
            </p>
            
            <p><strong>Your Sessions:</strong></p>
            <ul>
              {''.join([f"<li>{escape_html(session)}</li>" for session in reg['sessions']])}
            </ul>
            
            <p>See you at the event!</p>
          </div>
          
          <div class="footer">
            <p>&copy; 2026 Event Registration System</p>
          </div>
        </div>
      </body>
    </html>
    """


def generate_admin_notification_html(reg):
    """Generate admin notification HTML"""
    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body {{ font-family: Arial, sans-serif; color: #333; }}
          .container {{ max-width: 600px; margin: 0 auto; }}
          .header {{ background: #1a1714; color: white; padding: 20px; text-align: center; }}
          .content {{ padding: 20px; border: 1px solid #ddd; }}
          table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
          td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
          .label {{ font-weight: bold; width: 150px; background: #f5f3ee; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2>New Registration Received</h2>
          </div>
          
          <div class="content">
            <table>
              <tr>
                <td class="label">Name:</td>
                <td>{escape_html(reg['name'])}</td>
              </tr>
              <tr>
                <td class="label">Email:</td>
                <td>{escape_html(reg['email'])}</td>
              </tr>
              <tr>
                <td class="label">Ticket Type:</td>
                <td>{reg['ticket']}</td>
              </tr>
              <tr>
                <td class="label">Payment Status:</td>
                <td>{reg.get('paymentStatus', 'N/A')}</td>
              </tr>
              <tr>
                <td class="label">Dietary:</td>
                <td>{reg.get('dietary', 'None')}</td>
              </tr>
              <tr>
                <td class="label">Sessions:</td>
                <td>{', '.join(reg['sessions'])}</td>
              </tr>
              <tr>
                <td class="label">Timestamp:</td>
                <td>{datetime.fromisoformat(reg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}</td>
              </tr>
            </table>
          </div>
        </div>
      </body>
    </html>
    """


def escape_html(text):
    """Escape HTML special characters"""
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    }
    result = str(text)
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)
    return result


def test_email_connection():
    """Test email connection"""
    if not SEND_CONFIRMATION_EMAIL:
        print("Email sending is disabled in .env")
        return False
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        print(f"Email service connected to {SMTP_HOST}:{SMTP_PORT}")
        return True
    except Exception as e:
        print(f"Email service connection failed: {e}")
        print(f"   Check your .env settings:")
        print(f"   SMTP_HOST={SMTP_HOST}")
        print(f"   SMTP_PORT={SMTP_PORT}")
        print(f"   SMTP_USER={'***' if SMTP_USER else 'NOT SET'}")
        print(f"   SMTP_PASSWORD={'***' if SMTP_PASSWORD else 'NOT SET'}")
        return False
