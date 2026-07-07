from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.hashers import make_password
from datetime import timedelta
from ..models import User, OTP
from .utils import generate_otp, send_otp_email


@ratelimit(key='ip', rate='10/m', method='POST')
def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('/admin-panel/?tab=dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        cms = request.POST.get('cms')
        password = request.POST.get('password')
        user = authenticate(request, username=cms, password=password)
        if user is not None:
            login(request, user)
            if user.role == 'admin':
                return redirect('/admin-panel/?tab=dashboard')
            return redirect('dashboard')
        try:
            existing_user = User.objects.get(cms=cms)
            if not existing_user.is_active:
                if existing_user.is_email_verified:
                    messages.error(request, 'Your account has been deactivated. Please contact the administrator.')
                else:
                    messages.error(request, 'Email not verified. Please check your email for the OTP.')
                return render(request, 'login.html')
        except User.DoesNotExist:
            pass
        messages.error(request, 'Invalid CMS or password.')
        return render(request, 'login.html')

    return render(request, 'login.html')


@ratelimit(key='ip', rate='5/m', method='POST')
def register_view(request):
    if request.method == 'POST':
        cms = request.POST.get('cms')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        department = request.POST.get('department', '')
        semester_raw = request.POST.get('semester', '')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html')

        if User.objects.filter(cms=cms).exists():
            messages.error(request, 'CMS already registered.')
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'register.html')

        role = 'student'
        semester = None
        if semester_raw == 'alumni':
            role = 'alumni'
        elif semester_raw.isdigit():
            semester = int(semester_raw)
            role = 'senior' if semester >= 5 else 'student'

        code = generate_otp()
        expires_at = timezone.now() + timedelta(seconds=300)
        OTP.objects.create(email=email, code=code, expires_at=expires_at)
        send_otp_email('Your CampNect OTP Code', email, code)

        request.session.flush()
        request.session['otp_email'] = email
        pending_data = {
            'cms': cms,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'department': department,
            'role': role,
            'semester': semester,
            'password_hash': make_password(password),
        }
        request.session['pending_registration'] = pending_data
        return redirect('verify_otp')

    return render(request, 'register.html')


@ratelimit(key='ip', rate='10/m', method='POST')
def verify_otp_view(request):
    email = request.session.get('otp_email')
    pending = request.session.get('pending_registration')
    if not email or not pending:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register')

    if request.method == 'POST':
        if request.POST.get('action') == 'resend_otp':
            OTP.objects.filter(email=email, user__isnull=True).delete()
            code = generate_otp()
            expires_at = timezone.now() + timedelta(seconds=300)
            OTP.objects.create(email=email, code=code, expires_at=expires_at)
            send_otp_email('Your CampNect OTP Code (Resend)', email, code, resend=True)
            return redirect('verify_otp')

        code = request.POST.get('code', '').strip()
        otp = OTP.objects.filter(email=email, code=code, user__isnull=True).order_by('-created_at').first()

        if otp and not otp.is_expired():
            user = User(
                cms=pending['cms'],
                email=pending['email'],
                password=pending['password_hash'],
                first_name=pending['first_name'],
                last_name=pending['last_name'],
                role=pending['role'],
                semester=pending['semester'],
                department=pending['department'],
                is_active=True,
                is_email_verified=True,
            )
            user.save()
            otp.user = user
            otp.save(update_fields=['user'])
            OTP.objects.filter(email=email, user__isnull=True).delete()
            login(request, user)
            request.session.pop('otp_email', None)
            request.session.pop('pending_registration', None)
            messages.success(request, 'Email verified successfully!')
            return redirect('dashboard')
        else:
            if otp and otp.is_expired():
                OTP.objects.filter(email=email, user__isnull=True).delete()
                messages.error(request, 'OTP has expired. Please register again.')
                request.session.pop('otp_email', None)
                request.session.pop('pending_registration', None)
                return redirect('register')
            else:
                messages.error(request, 'Invalid OTP. Try again.')
            return redirect('verify_otp')

    otp_obj = OTP.objects.filter(email=email, user__isnull=True).order_by('-created_at').first()
    remaining = 0
    if otp_obj and not otp_obj.is_expired():
        delta = otp_obj.expires_at - timezone.now()
        remaining = int(delta.total_seconds())
    elif otp_obj and otp_obj.is_expired():
        messages.error(request, 'OTP has expired. Please register again.')
        OTP.objects.filter(email=email, user__isnull=True).delete()
        request.session.pop('otp_email', None)
        request.session.pop('pending_registration', None)
        return redirect('register')

    return render(request, 'verify_otp.html', {'email': email, 'remaining_seconds': remaining})


@ratelimit(key='ip', rate='5/m', method='POST')
def forgot_password_view(request):
    if request.method == 'POST':
        cms_or_email = request.POST.get('cms_or_email', '').strip()
        user = User.objects.filter(Q(cms=cms_or_email) | Q(email=cms_or_email)).first()
        if not user:
            messages.error(request, 'No account found with that CMS or email.')
            return render(request, 'forgot_password.html')

        if not user.email:
            messages.error(request, 'This account has no email address. Contact admin.')
            return render(request, 'forgot_password.html')

        OTP.objects.filter(user=user).delete()
        code = generate_otp()
        expires_at = timezone.now() + timedelta(seconds=300)
        OTP.objects.create(user=user, code=code, expires_at=expires_at)

        sent = send_otp_email('CampNect - Password Reset OTP', user.email, code)

        if sent:
            request.session['reset_user_id'] = user.id
            messages.success(request, 'OTP sent to your email.')
            return redirect('reset_password')
        else:
            messages.error(request, 'Failed to send OTP. Try again.')
            return render(request, 'forgot_password.html')

    return render(request, 'forgot_password.html')


@ratelimit(key='ip', rate='10/m', method='POST')
def reset_password_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        if request.POST.get('action') == 'resend_otp':
            OTP.objects.filter(user=user).delete()
            code = generate_otp()
            expires_at = timezone.now() + timedelta(seconds=300)
            OTP.objects.create(user=user, code=code, expires_at=expires_at)
            send_otp_email('CampNect - Password Reset OTP (Resend)', user.email, code, resend=True)
            messages.success(request, 'New OTP sent to your email.')
            return redirect('reset_password')

        code = request.POST.get('code', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not new_password or len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return redirect('reset_password')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('reset_password')

        otp = OTP.objects.filter(user=user, code=code).order_by('-created_at').first()
        if otp and not otp.is_expired():
            user.set_password(new_password)
            user.save()
            OTP.objects.filter(user=user).delete()
            if 'reset_user_id' in request.session:
                del request.session['reset_user_id']
            messages.success(request, 'Password reset successfully! Login with your new password.')
            return redirect('login')
        else:
            if otp and otp.is_expired():
                OTP.objects.filter(user=user).delete()
                messages.error(request, 'OTP has expired. Request a new one.')
                return redirect('forgot_password')
            else:
                messages.error(request, 'Invalid OTP. Try again.')
                return redirect('reset_password')

    otp_obj = OTP.objects.filter(user=user).order_by('-created_at').first()
    remaining = 0
    if otp_obj and not otp_obj.is_expired():
        delta = otp_obj.expires_at - timezone.now()
        remaining = int(delta.total_seconds())
    else:
        if otp_obj and otp_obj.is_expired():
            OTP.objects.filter(user=user).delete()
            messages.error(request, 'OTP has expired. Please request a new one.')
        else:
            messages.error(request, 'No OTP found. Please request a new one.')
        return redirect('forgot_password')

    return render(request, 'reset_password.html', {'email': user.email, 'remaining_seconds': remaining})


def logout_view(request):
    logout(request)
    return redirect('index')
