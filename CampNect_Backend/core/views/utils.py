import secrets
import os
import requests
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    return f'{secrets.randbelow(900000) + 100000}'


def validate_uploaded_file(uploaded_file, allowed_extensions=None, max_size_mb=10):
    if not uploaded_file:
        return None
    if allowed_extensions:
        ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        if ext not in allowed_extensions:
            return f'File type .{ext} is not allowed. Allowed: {", ".join(allowed_extensions)}'
    if uploaded_file.size > max_size_mb * 1024 * 1024:
        return f'File size exceeds {max_size_mb}MB limit.'
    return None


def send_email_brevo(html_content: str, text_content: str, subject: str, recipient_email: str) -> bool:
    api_key = os.getenv('BREVO_API_KEY', '')
    if not api_key:
        return False
    try:
        sender_email = settings.DEFAULT_FROM_EMAIL.split('<')[-1].rstrip('>') if '<' in settings.DEFAULT_FROM_EMAIL else settings.DEFAULT_FROM_EMAIL
        resp = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json={
                'sender': {'name': 'CampNect', 'email': sender_email},
                'to': [{'email': recipient_email}],
                'subject': subject,
                'htmlContent': html_content,
                'textContent': text_content,
            },
            timeout=15,
        )
        return resp.ok
    except Exception:
        logger.exception(f'Brevo API error for {recipient_email}')
        return False


def send_otp_email(subject: str, recipient_email: str, otp_code: str, resend: bool = False) -> bool:
    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
    <tr><td align="center">
      <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
        <tr><td style="background:linear-gradient(135deg,#1C3353,#2c7a5e);padding:32px 24px;text-align:center;">
          <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:800;">CampNect</h1>
          <p style="margin:4px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">Connect \u00b7 Collaborate \u00b7 Grow</p>
        </td></tr>
        <tr><td style="padding:32px 24px;text-align:center;">
          <h2 style="margin:0 0 8px;color:#1C3353;font-size:20px;">{'Resend: ' if resend else ''}Verify Your Email</h2>
          <p style="margin:0 0 20px;color:#5a7a8c;font-size:14px;line-height:1.5;">
            Use the code below to complete your verification. This code expires in <strong>5 minutes</strong>.
          </p>
          <div style="background:#f0f4f8;border-radius:12px;padding:16px 24px;display:inline-block;letter-spacing:8px;font-size:32px;font-weight:700;color:#1C3353;font-family:monospace;">
            {otp_code}
          </div>
          <p style="margin:20px 0 0;color:#8aa99b;font-size:12px;">
            If you didn't request this, please ignore this email.
          </p>
        </td></tr>
        <tr><td style="background:#f8faf9;padding:16px 24px;text-align:center;">
          <p style="margin:0;color:#8aa99b;font-size:11px;">CampNect &mdash; Riphah International University</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    text = f'Your OTP code is: {otp_code}\n\nThis code expires in 5 minutes.'

    if send_email_brevo(html, text, subject, recipient_email):
        return True

    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [recipient_email])
    msg.attach_alternative(html, 'text/html')
    try:
        msg.send(fail_silently=False)
        return True
    except Exception:
        logger.exception(f'Failed to send email to {recipient_email}')
        return False


def _escape_json(s: str) -> str:
    return s.replace('</script>', '<\\/script>').replace('</SCRIPT>', '<\\/SCRIPT>')
