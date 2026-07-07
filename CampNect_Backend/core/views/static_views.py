from django.shortcuts import render, redirect
from django.contrib import messages


def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


def index(request):
    return render(request, 'index.html')


def privacy(request):
    return render(request, 'privacy.html')


def terms(request):
    return render(request, 'terms.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not all([name, email, subject, message_text]):
            messages.error(request, 'All fields are required.')
            return render(request, 'contact.html')

        from ..models import ContactMessage
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message_text,
        )

        from .utils import send_email_brevo
        admin_html = f"<h2>New Contact Message</h2><p><strong>From:</strong> {name} ({email})</p><p><strong>Subject:</strong> {subject}</p><p><strong>Message:</strong></p><p>{message_text}</p>"
        send_email_brevo(admin_html, f'New message from {name} ({email})\n\nSubject: {subject}\n\n{message_text}', f'CampNect Contact: {subject}', 'admin@campnect.com')

        messages.success(request, 'Thank you! Your message has been sent. We will get back to you soon.')
        return redirect('contact')
    return render(request, 'contact.html')
