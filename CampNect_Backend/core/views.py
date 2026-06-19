import json
import os
import secrets
import requests
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import ExtractYear, ExtractMonth
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.core.mail import EmailMultiAlternatives
from django_ratelimit.decorators import ratelimit
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password
from .models import User, Community, CommunityMember, Discussion, Note, Message, Announcement, CollaborationPost, Connection, CommunityMessage, CollaborationMessage, Mentorship, MentorshipMessage, MentorshipRequest, AnnouncementLike, AnnouncementComment, CollaborationPostLike, CollaborationPostComment, CollaborationPostInterest, OTP, CareerOpportunity, Notification
from .permissions import is_admin, is_alumni, is_sem1to4_student, is_senior_student, can_access_alumni_features, is_student_to_alumni


def generate_otp():
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


def send_email_brevo(html, text, subject, recipient_email):
    api_key = os.getenv('BREVO_API_KEY', '')
    if not api_key:
        return False
    try:
        resp = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json={
                'sender': {'name': 'CampNect', 'email': settings.DEFAULT_FROM_EMAIL.split('<')[-1].rstrip('>') if '<' in settings.DEFAULT_FROM_EMAIL else settings.DEFAULT_FROM_EMAIL},
                'to': [{'email': recipient_email}],
                'subject': subject,
                'htmlContent': html,
                'textContent': text,
            },
            timeout=15,
        )
        return resp.ok
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f'Brevo API error for {recipient_email}')
        return False


def send_otp_email(subject, recipient_email, otp_code, resend=False):
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
          <p style="margin:4px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">Connect · Collaborate · Grow</p>
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
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f'Failed to send email to {recipient_email}: {e}')
        return False


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
            role = 'senior' if semester >= 6 else 'student'

        code = generate_otp()
        expires_at = timezone.now() + timedelta(seconds=300)
        OTP.objects.create(email=email, code=code, expires_at=expires_at)

        print(f'\n========== OTP for {email} ==========')
        print(f'Code: {code}')
        print(f'Expires in: 5 minutes')
        print(f'=====================================\n')
        try:
            send_otp_email('Your CampNect OTP Code', email, code)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(f'Failed to send OTP email to {email}')

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
            print(f'\n========== OTP for {email} ==========')
            print(f'Code: {code} (RESEND)')
            print(f'Expires in: 5 minutes')
            print(f'=========================================\n')
            try:
                send_otp_email('Your CampNect OTP Code (Resend)', email, code, resend=True)
            except Exception:
                import logging
                logging.getLogger(__name__).exception(f'Failed to resend OTP email to {email}')
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

        print(f'\n========== OTP for {user.email} (PASSWORD RESET) ==========')
        print(f'Code: {code}')
        print(f'Expires in: 5 minutes')
        print(f'==========================================================\n')
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
            print(f'\n========== OTP for {user.email} (RESEND - PASSWORD RESET) ==========')
            print(f'Code: {code}')
            print(f'==========================================================\n')
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


@login_required
def admin_panel(request):
    if not is_admin(request.user):
        return redirect('dashboard')
    if request.GET.get('tab') == 'overview':
        return redirect('/admin-panel/?tab=dashboard')

    q = request.GET.get('q', '')
    tbl = request.GET.get('tbl', '')
    role_filter = request.GET.get('role', '')
    dept_filter = request.GET.get('dept', '')
    sem_filter = request.GET.get('sem', '')
    users = User.objects.all()
    if q and tbl == 'users':
        users = users.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(cms__icontains=q) |
            Q(email__icontains=q) |
            Q(department__icontains=q) |
            Q(role__icontains=q)
        )
    if role_filter:
        users = users.filter(role=role_filter)
    if dept_filter:
        users = users.filter(department=dept_filter)
    if sem_filter:
        users = users.filter(semester=sem_filter)
    departments = User.objects.values_list('department', flat=True).distinct().order_by('department')
    semester_range = range(1, 9)
    communities = Community.objects.annotate(member_count=Count('members'))
    if q and tbl == 'communities':
        communities = communities.filter(name__icontains=q)
    notes = Note.objects.all()
    notes_subjects = Note.objects.values_list('subject', flat=True).distinct().order_by('subject')
    if q and tbl == 'notes':
        notes = notes.filter(
            Q(title__icontains=q) |
            Q(subject__icontains=q) |
            Q(uploaded_by__first_name__icontains=q) |
            Q(uploaded_by__last_name__icontains=q)
        )
    announcements = Announcement.objects.all()
    if q and tbl == 'announcements':
        announcements = announcements.filter(title__icontains=q)
    collab_posts = CollaborationPost.objects.annotate(
        interest_count=Count('interests'),
        comment_count=Count('comments'),
    ).prefetch_related('interests__user', 'comments__user')
    messages_list = Message.objects.all()
    mentorships = Mentorship.objects.all()

    total_users = User.objects.count()
    active_users_count = User.objects.filter(is_active=True).count()
    mentorships_count = Mentorship.objects.count()
    connections_total = Connection.objects.count()

    last_7 = timezone.now() - timedelta(days=7)

    recent_users = User.objects.all().order_by('-date_joined')[:8]
    recent_communities = Community.objects.all().order_by('-created_at')[:5]
    recent_notes = Note.objects.all().order_by('-upload_date')[:5]
    recent_collab = CollaborationPost.objects.all().order_by('-date_posted')[:5]
    recent_ann = Announcement.objects.all().order_by('-date_posted')[:5]

    all_activities = []
    for u in recent_users:
        all_activities.append({'type': 'user', 'text': f'{u.first_name} {u.last_name}', 'detail': 'joined CampNect', 'meta': u.cms, 'time': u.date_joined})
    for c in recent_communities:
        all_activities.append({'type': 'community', 'text': c.name, 'detail': 'community was created', 'meta': f'{c.created_by.first_name} {c.created_by.last_name}', 'time': c.created_at})
    for n in recent_notes:
        all_activities.append({'type': 'note', 'text': n.title, 'detail': 'note was uploaded', 'meta': f'{n.uploaded_by.first_name} {n.uploaded_by.last_name}', 'time': n.upload_date})
    for p in recent_collab:
        all_activities.append({'type': 'collab', 'text': p.title, 'detail': 'collaboration post created', 'meta': f'{p.posted_by.first_name} {p.posted_by.last_name}', 'time': p.date_posted})
    for a in recent_ann:
        all_activities.append({'type': 'announcement', 'text': a.title, 'detail': 'announcement posted', 'meta': a.get_by_line(), 'time': a.date_posted})
    all_activities.sort(key=lambda x: x['time'], reverse=True)
    all_activities = all_activities[:20]

    new_users_week = User.objects.filter(date_joined__gte=last_7).count()
    inactive_users_count = User.objects.filter(is_active=False).count()
    empty_communities_count = Community.objects.annotate(member_count=Count('members')).filter(member_count=0).count()
    recent_notes_count = Note.objects.filter(upload_date__gte=last_7).count()
    recent_collab_count = CollaborationPost.objects.filter(date_posted__gte=last_7).count()

    # ── Analytics for Reports ──
    twelve_months_ago = timezone.now() - timedelta(days=365)
    import calendar as _cal

    # Generate 12-month labels (oldest first)
    months_12 = []
    for i in range(11, -1, -1):
        m = (timezone.now().month - i - 1) % 12 + 1
        months_12.append(_cal.month_abbr[m])

    # Growth trends - build a month→count map, fill rest with 0
    mq = User.objects.filter(date_joined__gte=twelve_months_ago).annotate(
        y=ExtractYear('date_joined'), mo=ExtractMonth('date_joined')
    ).values('y','mo').annotate(c=Count('id')).order_by('y','mo')
    ug_map = {}
    for m in mq:
        if m['y'] and m['mo']:
            ug_map[_cal.month_abbr[int(m['mo'])]] = m['c']
    ug_labels = months_12[:]
    ug_monthly = [ug_map.get(ml, 0) for ml in months_12]
    ug_cum = []
    running = 0
    for v in ug_monthly:
        running += v
        ug_cum.append(running)

    # Engagement trends - notes
    mn_qs = Note.objects.filter(upload_date__gte=twelve_months_ago).annotate(
        y=ExtractYear('upload_date'), mo=ExtractMonth('upload_date')
    ).values('y','mo').annotate(c=Count('id')).order_by('y','mo')
    nm_map = {}
    for m in mn_qs:
        if m['y'] and m['mo']:
            nm_map[_cal.month_abbr[int(m['mo'])]] = m['c']

    # Engagement trends - collab posts
    mc_qs = CollaborationPost.objects.filter(date_posted__gte=twelve_months_ago).annotate(
        y=ExtractYear('date_posted'), mo=ExtractMonth('date_posted')
    ).values('y','mo').annotate(c=Count('id')).order_by('y','mo')
    cm_map = {}
    for m in mc_qs:
        if m['y'] and m['mo']:
            cm_map[_cal.month_abbr[int(m['mo'])]] = m['c']

    # Engagement chart uses all months with data (union), fallback to 12 months
    all_months_set = set(ug_map.keys()) | set(nm_map.keys()) | set(cm_map.keys())
    all_months = sorted(all_months_set, key=lambda x: list(_cal.month_abbr).index(x)) if all_months_set else months_12[:]
    eg_new_users = [ug_map.get(m, 0) for m in all_months]
    eg_notes = [nm_map.get(m, 0) for m in all_months]
    eg_collab = [cm_map.get(m, 0) for m in all_months]

    # Role distribution
    role_map = dict(User.Role.choices)
    role_qs = list(User.objects.values('role').annotate(c=Count('id')))
    role_labels = [role_map.get(r['role'], r['role']) for r in role_qs]
    role_data = [r['c'] for r in role_qs]

    # ── Top Performing Communities leaderboard ──
    top_communities_lb = Community.objects.annotate(mc=Count('members')).order_by('-mc')[:20]
    communities_lb = [{
        'name': c.name,
        'category': c.get_category_display(),
        'members': c.mc,
        'creator': f'{c.created_by.first_name} {c.created_by.last_name}' if c.created_by else '-',
        'created': c.created_at.strftime('%b %Y') if c.created_at else '-',
    } for c in top_communities_lb]

    # ── Top Performing Departments leaderboard ──
    dept_agg = User.objects.values('department').exclude(department='').annotate(
        total=Count('id'),
        students=Count('id', filter=Q(role='student')),
        seniors=Count('id', filter=Q(role='senior')),
        alumni=Count('id', filter=Q(role='alumni')),
    ).order_by('-total')[:20]
    departments_lb = [d for d in dept_agg]

    # ── Platform Insights ──
    total_students = User.objects.filter(role='student').count()
    total_seniors = User.objects.filter(role='senior').count()
    total_alumni = User.objects.filter(role='alumni').count()
    total_admins = User.objects.filter(role='admin').count()
    total_communities = communities.count()
    avg_members = round(total_users / max(total_communities, 1), 1)
    total_notes_count = notes.count()
    total_collab = collab_posts.count()
    new_users_this_month = ug_monthly[-1] if ug_monthly else 0
    growth_rate = round((ug_monthly[-1] / max(sum(ug_monthly[:-1]), 1)) * 100, 1) if len(ug_monthly) > 1 else 0

    insights = []
    if total_users:
        insights.append(f'Platform has reached {total_users} total users with {active_users_count} active members, '
                        f'a {growth_rate}% month-over-month growth rate.')
    if total_communities and communities_lb:
        insights.append(f'{total_communities} communities exist with an average of {avg_members} members each. '
                        f'Top community "{communities_lb[0]["name"]}" leads with {communities_lb[0]["members"]} members.')
    if total_notes_count:
        top_subj = Note.objects.values('subject').annotate(c=Count('id')).order_by('-c').first()
        insights.append(f'{total_notes_count} notes have been shared across the platform. '
                        f'Most popular subject: {top_subj["subject"]} ({top_subj["c"]} notes).')
    if total_collab:
        insights.append(f'{total_collab} collaboration projects posted, fostering cross-disciplinary teamwork.')
    if total_seniors and total_students:
        ratio = round(total_seniors / max(total_students, 1) * 100, 1)
        insights.append(f'Seniors represent {ratio}% of the student body, indicating strong mentoring pipeline.')
    if total_alumni and dept_agg:
        insights.append(f'{total_alumni} alumni remain connected to the platform, '
                        f'with top engagement from the "{dept_agg[0]["department"]}" department.')

    analytics = {
        'userGrowth': {'labels': ug_labels, 'monthly': ug_monthly, 'cumulative': ug_cum},
        'engagementTrends': {'labels': all_months, 'newUsers': eg_new_users, 'notes': eg_notes, 'collab': eg_collab},
        'roleDist': {'labels': role_labels, 'data': role_data},
        'topCommunities': communities_lb,
        'topDepartments': [{
            'department': d['department'],
            'total': d['total'],
            'students': d['students'],
            'seniors': d['seniors'],
            'alumni': d['alumni'],
        } for d in departments_lb],
        'insights': insights,
    }

    context = {
        'users': users,
        'communities': communities,
        'notes': notes,
        'notes_subjects': notes_subjects,
        'announcements': announcements,
        'pinned_announcements': announcements.filter(is_pinned=True),
        'analytics': analytics,
        'analytics_json': json.dumps(analytics),
        'collab_posts': collab_posts,
        'projects_json': json.dumps([{
            'id': p.id,
            'title': p.title,
            'description': p.description[:200] if p.description else '',
            'skills': p.get_skills_list(),
            'roles': p.get_roles_list(),
            'postedBy': f'{p.posted_by.first_name} {p.posted_by.last_name}',
            'postedById': p.posted_by.id,
            'date': p.date_posted.strftime('%b %d, %Y') if p.date_posted else '',
            'interestCount': p.interest_count,
            'commentCount': p.comment_count,
            'mentorId': p.mentor_id,
            'mentorName': f'{p.mentor.first_name} {p.mentor.last_name}' if p.mentor else None,
        } for p in collab_posts]),
        'available_mentors_json': json.dumps([{
            'id': u.id,
            'name': f'{u.first_name} {u.last_name}',
            'role': u.get_role_display(),
            'department': u.department,
        } for u in User.objects.filter(role__in=['senior', 'alumni', 'admin']).order_by('first_name')]),
        'mentorships': mentorships,
        'messages_list': messages_list,
        'total_users': total_users,
        'active_users_count': active_users_count,
        'mentorships_count': mentorships_count,
        'connections_total': connections_total,
        'all_activities': all_activities,
        'new_users_week': new_users_week,
        'inactive_users_count': inactive_users_count,
        'empty_communities_count': empty_communities_count,
        'recent_notes_count': recent_notes_count,
        'recent_collab_count': recent_collab_count,
        'tab': request.GET.get('tab', 'dashboard'),
        'q': q,
        'tbl': tbl,
        'departments': departments,
        'selected_role': role_filter,
        'selected_dept': dept_filter,
        'selected_sem': sem_filter,
        'semester_range': semester_range,
    }
    return render(request, 'admin.html', context)


@login_required
@require_http_methods(['POST'])
def admin_api(request):
    if not is_admin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    action = request.POST.get('action')
    if not action:
        return JsonResponse({'error': 'No action specified'}, status=400)

    # ── User actions ──
    if action == 'update_user':
        user_id = request.POST.get('user_id')
        try:
            u = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        role = request.POST.get('role')
        is_active_raw = request.POST.get('is_active')
        if role and role in dict(User.Role.choices):
            u.role = role
        if is_active_raw is not None:
            u.is_active = is_active_raw == '1'
        u.save()
        return JsonResponse({'ok': True, 'role': u.role, 'is_active': u.is_active})

    if action == 'delete_user':
        user_id = request.POST.get('user_id')
        try:
            User.objects.get(id=user_id).delete()
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        return JsonResponse({'ok': True})

    # ── Community actions ──
    if action == 'create_community':
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)
        c = Community.objects.create(
            name=name,
            description=request.POST.get('description', '').strip(),
            category=request.POST.get('category', 'general'),
            created_by=request.user,
        )
        CommunityMember.objects.create(user=request.user, community=c, is_admin=True)
        return JsonResponse({'ok': True, 'id': c.id, 'name': c.name})

    if action == 'update_community':
        community_id = request.POST.get('community_id')
        try:
            c = Community.objects.get(id=community_id)
        except Community.DoesNotExist:
            return JsonResponse({'error': 'Community not found'}, status=404)
        name = request.POST.get('name', '').strip()
        if name:
            c.name = name
        c.description = request.POST.get('description', '').strip()
        c.category = request.POST.get('category', c.category)
        c.save()
        return JsonResponse({'ok': True, 'name': c.name})

    if action == 'delete_community':
        community_id = request.POST.get('community_id')
        try:
            Community.objects.get(id=community_id).delete()
        except Community.DoesNotExist:
            return JsonResponse({'error': 'Community not found'}, status=404)
        return JsonResponse({'ok': True})

    if action == 'get_community_members':
        community_id = request.POST.get('community_id')
        try:
            comm = Community.objects.get(id=community_id)
        except Community.DoesNotExist:
            return JsonResponse({'error': 'Community not found'}, status=404)
        members = CommunityMember.objects.filter(community=comm).select_related('user')
        members_data = [{
            'id': m.id,
            'user_id': m.user.id,
            'name': f"{m.user.first_name} {m.user.last_name}",
            'cms': m.user.cms,
            'is_admin': m.is_admin,
            'joined_at': m.joined_at.strftime('%b %d, %Y'),
            'initials': f"{m.user.first_name[0]}{m.user.last_name[0]}".upper(),
        } for m in members]
        return JsonResponse({'ok': True, 'members': members_data, 'member_count': len(members_data)})

    if action == 'remove_community_member':
        member_id = request.POST.get('member_id')
        try:
            CommunityMember.objects.get(id=member_id).delete()
        except CommunityMember.DoesNotExist:
            return JsonResponse({'error': 'Member not found'}, status=404)
        return JsonResponse({'ok': True})

    if action == 'toggle_community_admin':
        member_id = request.POST.get('member_id')
        try:
            member = CommunityMember.objects.get(id=member_id)
        except CommunityMember.DoesNotExist:
            return JsonResponse({'error': 'Member not found'}, status=404)
        member.is_admin = not member.is_admin
        member.save()
        return JsonResponse({'ok': True, 'is_admin': member.is_admin})

    # ── Announcement actions ──
    if action == 'create_announcement':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        by_line = request.POST.get('by_line', '').strip()
        if not title or not content:
            return JsonResponse({'error': 'Title and content are required'}, status=400)
        a = Announcement.objects.create(title=title, content=content, by_line=by_line, posted_by=request.user)
        return JsonResponse({
            'ok': True, 'id': a.id,
            'title': a.title,
            'author': a.get_by_line(),
            'date': a.date_posted.strftime('%b %d, %Y'),
        })

    if action == 'update_announcement':
        announcement_id = request.POST.get('announcement_id')
        try:
            a = Announcement.objects.get(id=announcement_id)
        except Announcement.DoesNotExist:
            return JsonResponse({'error': 'Announcement not found'}, status=404)
        title = request.POST.get('title', '').strip()
        if title:
            a.title = title
        by_line = request.POST.get('by_line', '').strip()
        a.by_line = by_line
        content = request.POST.get('content', '').strip()
        if content:
            a.content = content
        a.save()
        return JsonResponse({'ok': True, 'title': a.title})

    if action == 'delete_announcement':
        announcement_id = request.POST.get('announcement_id')
        try:
            Announcement.objects.get(id=announcement_id).delete()
        except Announcement.DoesNotExist:
            return JsonResponse({'error': 'Announcement not found'}, status=404)
        return JsonResponse({'ok': True})

    if action == 'toggle_pin_announcement':
        announcement_id = request.POST.get('announcement_id')
        try:
            a = Announcement.objects.get(id=announcement_id)
        except Announcement.DoesNotExist:
            return JsonResponse({'error': 'Announcement not found'}, status=404)
        a.is_pinned = not a.is_pinned
        a.save()
        return JsonResponse({'ok': True, 'is_pinned': a.is_pinned, 'title': a.title})

    # ── Note actions ──
    if action == 'delete_note':
        note_id = request.POST.get('note_id')
        try:
            Note.objects.get(id=note_id).delete()
        except Note.DoesNotExist:
            return JsonResponse({'error': 'Note not found'}, status=404)
        return JsonResponse({'ok': True})

    # ── Project actions ──
    if action == 'get_project_detail':
        pid = request.POST.get('project_id')
        try:
            p = CollaborationPost.objects.prefetch_related('interests__user', 'comments__user', 'likes__user').get(id=pid)
        except CollaborationPost.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        interests = [{
            'id': i.id, 'userId': i.user.id,
            'name': f'{i.user.first_name} {i.user.last_name}',
            'role': i.user.get_role_display(),
            'status': i.status,
        } for i in p.interests.all()]
        comments = [{
            'id': c.id, 'userId': c.user.id,
            'name': f'{c.user.first_name} {c.user.last_name}',
            'text': c.text,
            'date': c.created_at.strftime('%b %d') if c.created_at else '',
        } for c in p.comments.all()]
        return JsonResponse({
            'ok': True,
            'project': {
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'skills': p.get_skills_list(),
                'roles': p.get_roles_list(),
                'postedBy': f'{p.posted_by.first_name} {p.posted_by.last_name}',
                'date': p.date_posted.strftime('%b %d, %Y') if p.date_posted else '',
                'mentorId': p.mentor_id,
                'mentorName': f'{p.mentor.first_name} {p.mentor.last_name}' if p.mentor else None,
                'interests': interests,
                'teamMembers': [i for i in interests if i['status'] == 'team'],
                'comments': comments,
            }
        })

    if action == 'assign_project_mentor':
        pid = request.POST.get('project_id')
        mentor_id = request.POST.get('mentor_id')
        try:
            p = CollaborationPost.objects.get(id=pid)
        except CollaborationPost.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        if mentor_id:
            try:
                p.mentor = User.objects.get(id=mentor_id)
            except User.DoesNotExist:
                return JsonResponse({'error': 'Mentor not found'}, status=404)
        else:
            p.mentor = None
        p.save(update_fields=['mentor'])
        mentor_name = f'{p.mentor.first_name} {p.mentor.last_name}' if p.mentor else None
        return JsonResponse({'ok': True, 'mentorId': p.mentor_id, 'mentorName': mentor_name})

    if action == 'set_interest_status':
        interest_id = request.POST.get('interest_id')
        status = request.POST.get('status')
        if status not in ['interested', 'team', 'declined']:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        try:
            interest = CollaborationPostInterest.objects.get(id=interest_id)
        except CollaborationPostInterest.DoesNotExist:
            return JsonResponse({'error': 'Interest not found'}, status=404)
        interest.status = status
        interest.save(update_fields=['status'])
        return JsonResponse({'ok': True, 'status': status})

    if action == 'delete_project':
        pid = request.POST.get('project_id')
        try:
            CollaborationPost.objects.get(id=pid).delete()
        except CollaborationPost.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        return JsonResponse({'ok': True})

    return JsonResponse({'error': f'Unknown action: {action}'}, status=400)


@login_required
def dashboard(request):
    # ===== AJAX handlers =====
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'like_announcement':
            ann = get_object_or_404(Announcement, id=request.POST.get('announcement_id'))
            AnnouncementLike.objects.get_or_create(user=request.user, announcement=ann)
            return JsonResponse({'liked': True, 'count': ann.likes.count()})

        if action == 'unlike_announcement':
            ann = get_object_or_404(Announcement, id=request.POST.get('announcement_id'))
            AnnouncementLike.objects.filter(user=request.user, announcement=ann).delete()
            return JsonResponse({'liked': False, 'count': ann.likes.count()})

        if action == 'like_collab':
            post = get_object_or_404(CollaborationPost, id=request.POST.get('post_id'))
            CollaborationPostLike.objects.get_or_create(user=request.user, post=post)
            return JsonResponse({'liked': True, 'count': post.likes.count()})

        if action == 'unlike_collab':
            post = get_object_or_404(CollaborationPost, id=request.POST.get('post_id'))
            CollaborationPostLike.objects.filter(user=request.user, post=post).delete()
            return JsonResponse({'liked': False, 'count': post.likes.count()})

        if action == 'add_comment':
            text = request.POST.get('text', '').strip()
            if not text:
                return JsonResponse({'error': 'Comment text is required.'}, status=400)
            post_type = request.POST.get('post_type', '')
            post_id = request.POST.get('post_id', '')
            parent_id = request.POST.get('parent_id', '')
            if post_type == 'announcement':
                ann = get_object_or_404(Announcement, id=post_id)
                parent = None
                if parent_id:
                    try: parent = AnnouncementComment.objects.get(id=parent_id, announcement=ann)
                    except AnnouncementComment.DoesNotExist: pass
                c = AnnouncementComment.objects.create(user=request.user, announcement=ann, text=text, parent=parent)
                return JsonResponse({'id': c.id, 'user': request.user.get_full_name() or request.user.cms, 'text': c.text, 'parent_id': c.parent_id, 'created_at': c.created_at.isoformat()})
            elif post_type == 'collaboration':
                post = get_object_or_404(CollaborationPost, id=post_id)
                parent = None
                if parent_id:
                    try: parent = CollaborationPostComment.objects.get(id=parent_id, post=post)
                    except CollaborationPostComment.DoesNotExist: pass
                c = CollaborationPostComment.objects.create(user=request.user, post=post, text=text, parent=parent)
                return JsonResponse({'id': c.id, 'user': request.user.get_full_name() or request.user.cms, 'text': c.text, 'parent_id': c.parent_id, 'created_at': c.created_at.isoformat()})
            return JsonResponse({'error': 'Invalid post type.'}, status=400)

        if action == 'get_comments':
            post_type = request.POST.get('post_type', '')
            post_id = request.POST.get('post_id', '')
            if post_type == 'announcement':
                ann = get_object_or_404(Announcement, id=post_id)
                comments = ann.comments.all().order_by('created_at')
            elif post_type == 'collaboration':
                post = get_object_or_404(CollaborationPost, id=post_id)
                comments = post.comments.all().order_by('created_at')
            else:
                return JsonResponse({'error': 'Invalid post type.'}, status=400)
            data = [{'id': c.id, 'user': c.user.get_full_name() or c.user.cms, 'text': c.text, 'parent_id': c.parent_id, 'created_at': c.created_at.isoformat()} for c in comments]
            return JsonResponse({'comments': data})

        return JsonResponse({'error': 'Invalid action.'}, status=400)

    # ===== Regular POST =====
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'connect' or action == 'follow':
            target = get_object_or_404(User, id=request.POST.get('user_id'))
            if target == request.user:
                messages.error(request, 'You cannot connect with yourself.')
            elif is_sem1to4_student(request.user) and target.role == 'alumni':
                messages.error(request, 'Semester 1-4 students cannot connect with alumni.')
            elif is_senior_student(request.user) and target.role == 'alumni':
                connected = Connection.objects.filter(Q(follower=request.user, following=target) | Q(follower=target, following=request.user)).exists()
                mentorship_exists = Mentorship.objects.filter(Q(mentor=request.user, mentee=target) | Q(mentor=target, mentee=request.user), status='accepted').exists()
                request_accepted = MentorshipRequest.objects.filter(Q(student=request.user, alumni=target) | Q(student=target, alumni=request.user), status='accepted').exists()
                shared_comm = CommunityMember.objects.filter(user=target, community_id__in=CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True)).exists()
                if not (connected or mentorship_exists or request_accepted or shared_comm):
                    messages.error(request, 'You can only connect with alumni through an active mentorship, accepted request, or shared community.')
                    return redirect('dashboard')
                Connection.objects.get_or_create(follower=request.user, following=target)
                messages.success(request, f'Connected with {target.get_full_name() or target.cms}.')
            else:
                Connection.objects.get_or_create(follower=request.user, following=target)
                messages.success(request, f'Connected with {target.get_full_name() or target.cms}.')
            return redirect('/chat/?user_id=' + str(target.id))
        if not is_admin(request.user):
            messages.error(request, 'Only admins can create announcements.')
            return redirect('dashboard')
        post_type = request.POST.get('post_type', 'announcement')
        content = request.POST.get('content', '').strip()
        if not content:
            messages.error(request, 'Post content is required.')
            return redirect('dashboard')
        Announcement.objects.create(title=content[:80], content=content, posted_by=request.user)
        messages.success(request, 'Announcement published successfully.')
        return redirect('dashboard')

    # ===== GET =====
    announcements = Announcement.objects.select_related('posted_by').annotate(like_count=Count('likes'), comment_count=Count('comments')).order_by('-is_pinned', '-date_posted')
    collab_posts = CollaborationPost.objects.select_related('posted_by', 'mentor').annotate(like_count=Count('likes'), comment_count=Count('comments')).order_by('-date_posted')
    recent_notes = Note.objects.select_related('uploaded_by').all().order_by('-upload_date')[:5]
    user_community_ids = CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True)
    popular_communities = Community.objects.select_related('created_by').annotate(member_count=Count('members')).exclude(id__in=user_community_ids).order_by('-member_count')[:4]
    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    connected_user_ids = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).values_list('follower_id', 'following_id')
    connected_ids = set()
    for f, g in connected_user_ids:
        connected_ids.add(f)
        connected_ids.add(g)
    can_access_alumni = not is_sem1to4_student(request.user)
    alumni_list = User.objects.filter(role='alumni', is_active=True).exclude(id__in=connected_ids).exclude(id=request.user.id)[:5] if can_access_alumni else []
    suggested_base = User.objects.filter(is_active=True).exclude(Q(id=request.user.id) | Q(role='admin') | Q(id__in=connected_ids))
    if is_sem1to4_student(request.user):
        suggested_base = suggested_base.exclude(role='alumni')
    elif is_senior_student(request.user):
        allowed = set()
        for c in Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)):
            allowed.add(c.follower_id if c.following_id == request.user.id else c.following_id)
        for m in Mentorship.objects.filter(Q(mentor=request.user) | Q(mentee=request.user), status='accepted'):
            allowed.add(m.mentor_id if m.mentee_id == request.user.id else m.mentee_id)
        for mr in MentorshipRequest.objects.filter(Q(student=request.user) | Q(alumni=request.user), status='accepted'):
            allowed.add(mr.student_id if mr.alumni_id == request.user.id else mr.alumni_id)
        user_comms = list(CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True))
        if user_comms:
            for cm in CommunityMember.objects.filter(community_id__in=user_comms).exclude(user=request.user):
                allowed.add(cm.user_id)
        suggested_base = suggested_base.filter(Q(role__in=['student', 'senior']) | (Q(role='alumni') & Q(id__in=allowed)))
    suggested_users = suggested_base.order_by('?')[:5]
    alumni_count = User.objects.filter(role='alumni').count()
    my_mentorships_dash = Mentorship.objects.filter(Q(mentor=request.user) | Q(mentee=request.user)).select_related('mentor', 'mentee')
    mentorship_pending = [ms for ms in my_mentorships_dash if ms.status == 'pending']
    mentorship_active = [ms for ms in my_mentorships_dash if ms.status == 'accepted']
    liked_ann_ids_list = list(AnnouncementLike.objects.filter(user=request.user).values_list('announcement_id', flat=True))
    liked_collab_ids_list = list(CollaborationPostLike.objects.filter(user=request.user).values_list('post_id', flat=True))

    is_senior = is_senior_student(request.user)
    alumni_announcements = Announcement.objects.filter(posted_by__role='alumni').annotate(like_count=Count('likes'), comment_count=Count('comments')).order_by('-date_posted')[:5]
    mentorship_requests_received = MentorshipRequest.objects.filter(alumni=request.user, status='pending').select_related('student').order_by('-created_at') if is_alumni(request.user) else []
    mentorship_requests_sent = MentorshipRequest.objects.filter(student=request.user).select_related('alumni').order_by('-created_at') if is_senior else []
    internship_posts = CollaborationPost.objects.filter(required_skills__icontains='intern').order_by('-date_posted')[:3]

    popular_discussions = Discussion.objects.select_related('community', 'user').order_by('-post_date')[:5]
    career_opportunities = CareerOpportunity.objects.select_related('posted_by').order_by('-created_at')[:5]

    context = {
        'announcements': announcements,
        'collab_posts': collab_posts,
        'recent_notes': recent_notes,
        'popular_communities': popular_communities,
        'connections_count': connections_count,
        'communities_count': communities_count,
        'alumni_list': alumni_list,
        'suggested_users': suggested_users,
        'alumni_count': alumni_count,
        'mentorship_pending': mentorship_pending,
        'mentorship_active': mentorship_active,
        'mentorship_pending_count': len(mentorship_pending),
        'mentorship_active_count': len(mentorship_active),
        'liked_ann_ids': json.dumps(liked_ann_ids_list),
        'liked_collab_ids': json.dumps(liked_collab_ids_list),
        'liked_ann_set': liked_ann_ids_list,
        'liked_collab_set': liked_collab_ids_list,
        'is_senior_student': is_senior,
        'alumni_announcements': alumni_announcements,
        'mentorship_requests_received': mentorship_requests_received,
        'mentorship_requests_sent': mentorship_requests_sent,
        'internship_posts': internship_posts,
        'popular_discussions': popular_discussions,
        'career_opportunities': career_opportunities,
    }
    return render(request, 'dashboard.html', context)


@login_required
@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.bio = request.POST.get('bio', user.bio)
        user.skills = request.POST.get('skills', user.skills)
        user.department = request.POST.get('department', user.department)
        semester = request.POST.get('semester')
        if semester:
            try:
                user.semester = int(semester)
            except ValueError:
                pass
        if 'profile_pic' in request.FILES:
            file_error = validate_uploaded_file(request.FILES['profile_pic'], allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'webp'], max_size_mb=5)
            if file_error:
                messages.error(request, file_error)
                return redirect('profile')
            user.profile_pic = request.FILES['profile_pic']
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')

    connections_count = Connection.objects.filter(
        Q(follower=user) | Q(following=user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=user).count()
    notes_count = Note.objects.filter(uploaded_by=user).count()
    projects_count = CollaborationPost.objects.filter(posted_by=user).count()

    user_notes = Note.objects.filter(uploaded_by=user).order_by('-upload_date')[:5]
    user_memberships = CommunityMember.objects.filter(
        user=user
    ).select_related('community').order_by('-joined_at')[:5]
    user_communities = [m.community for m in user_memberships]

    context = {
        'connections_count': connections_count,
        'communities_count': communities_count,
        'notes_count': notes_count,
        'projects_count': projects_count,
        'user_notes': user_notes,
        'user_communities': user_communities,
        'user_memberships': user_memberships,
    }
    return render(request, 'profile.html', context)


@login_required
def user_profile_view(request, user_id):
    profile_user = get_object_or_404(User, id=user_id)
    if is_sem1to4_student(request.user) and profile_user.role == 'alumni':
        messages.error(request, 'Alumni profiles are available from Semester 5.')
        return redirect('dashboard')
    connections_count = Connection.objects.filter(
        Q(follower=profile_user) | Q(following=profile_user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=profile_user).count()
    projects_count = CollaborationPost.objects.filter(posted_by=profile_user).count()
    notes_count = Note.objects.filter(uploaded_by=profile_user).count()
    context = {
        'profile_user': profile_user,
        'connections_count': connections_count,
        'communities_count': communities_count,
        'projects_count': projects_count,
        'notes_count': notes_count,
    }
    return render(request, 'user_profile.html', context)


@login_required
def user_profile_api(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if is_sem1to4_student(request.user) and u.role == 'alumni':
        return JsonResponse({'error': 'Not accessible'}, status=403)
    connections_count = Connection.objects.filter(Q(follower=u) | Q(following=u)).count()
    communities_count = CommunityMember.objects.filter(user=u).count()
    projects_count = CollaborationPost.objects.filter(posted_by=u).count()
    notes_count = Note.objects.filter(uploaded_by=u).count()
    data = {
        'id': u.id,
        'name': u.get_full_name() or u.cms,
        'cms': u.cms,
        'email': u.email,
        'role': u.get_role_display(),
        'role_slug': u.role,
        'department': u.department,
        'semester': u.semester,
        'bio': u.bio or '',
        'skills': [s.strip() for s in u.skills.split(',') if s.strip()] if u.skills else [],
        'profile_pic': u.profile_pic.url if u.profile_pic else None,
        'graduation_year': u.graduation_year,
        'current_company': u.current_company,
        'current_position': u.current_position,
        'industry': u.industry,
        'connections_count': connections_count,
        'communities_count': communities_count,
        'projects_count': projects_count,
        'notes_count': notes_count,
    }
    return JsonResponse(data)


@login_required
def notes_view(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        subject = request.POST.get('subject', '').strip()
        description = request.POST.get('description', '').strip()
        semester = request.POST.get('semester', '').strip()

        if not title or not subject:
            messages.error(request, 'Title and subject are required.')
            return redirect('notes')

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, 'A file is required.')
            return redirect('notes')
        file_error = validate_uploaded_file(uploaded_file, allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'zip', 'rar'], max_size_mb=50)
        if file_error:
            messages.error(request, file_error)
            return redirect('notes')

        Note.objects.create(
            title=title,
            subject=subject,
            description=description,
            file=uploaded_file,
            uploaded_by=request.user,
            semester=int(semester) if semester and semester.isdigit() else None,
        )
        messages.success(request, 'Notes uploaded successfully.')
        return redirect('notes')

    all_notes_list = Note.objects.all().order_by('-upload_date').select_related('uploaded_by')
    my_notes = Note.objects.filter(uploaded_by=request.user).order_by('-upload_date').select_related('uploaded_by')

    page = request.GET.get('page', 1)
    paginator = Paginator(all_notes_list, 20)
    all_notes = paginator.get_page(page)

    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    context = {
        'all_notes': all_notes,
        'my_notes': my_notes,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'notes.html', context)


@login_required
def communities_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            if not name:
                messages.error(request, 'Community name is required.')
                return redirect('communities')

            category = request.POST.get('category', 'general')
            message_permission = request.POST.get('message_permission', 'all_members')
            community = Community.objects.create(
                name=name,
                description=description,
                category=category,
                message_permission=message_permission,
                created_by=request.user,
            )
            membership, _ = CommunityMember.objects.get_or_create(user=request.user, community=community)
            membership.is_admin = True
            membership.save()
            messages.success(request, 'Community created successfully.')
            return redirect('communities')

        if action == 'join_community':
            community = get_object_or_404(Community, id=request.POST.get('community_id'))
            _, created = CommunityMember.objects.get_or_create(
                user=request.user,
                community=community,
            )
            if created:
                messages.success(request, f'You joined {community.name}!')
            else:
                messages.info(request, 'You are already a member.')
            return redirect('communities')

        if action == 'leave_community':
            community = get_object_or_404(Community, id=request.POST.get('community_id'))
            if request.user == community.created_by:
                messages.error(request, 'You cannot leave a community you created.')
                return redirect('communities')
            deleted, _ = CommunityMember.objects.filter(
                user=request.user,
                community=community,
            ).delete()
            if deleted:
                messages.success(request, f'You left {community.name}.')
            else:
                messages.error(request, 'You are not a member of this community.')
            return redirect('communities')

    communities = Community.objects.annotate(member_count=Count('members'))
    my_communities = Community.objects.filter(
        members__user=request.user
    ).annotate(member_count=Count('members')).distinct()
    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    context = {
        'communities': communities,
        'my_communities': my_communities,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'communities.html', context)


@login_required
def collaboration_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'toggle_interest':
            post_id = request.POST.get('post_id')
            post = get_object_or_404(CollaborationPost, id=post_id)
            interest, created = CollaborationPostInterest.objects.get_or_create(user=request.user, post=post)
            if not created:
                if interest.status == 'team':
                    return JsonResponse({'error': 'You are already a team member and cannot remove your interest.'}, status=400)
                interest.delete()
                interested = False
            else:
                interested = True
            return JsonResponse({'interested': interested, 'count': post.interests.count()})

        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        required_skills = request.POST.get('required_skills', '').strip()
        roles_needed = request.POST.get('roles_needed', '').strip()

        if not title or not description:
            messages.error(request, 'Project title and description are required.')
            return redirect('collaboration')

        CollaborationPost.objects.create(
            title=title,
            description=description,
            required_skills=required_skills,
            roles_needed=roles_needed,
            posted_by=request.user,
        )
        messages.success(request, 'Project posted successfully.')
        return redirect('collaboration')

    posts = CollaborationPost.objects.select_related('posted_by', 'mentor').annotate(interest_count=Count('interests')).order_by('-date_posted')
    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    interested_ids = list(CollaborationPostInterest.objects.filter(user=request.user).values_list('post_id', flat=True))
    context = {
        'posts': posts,
        'connections_count': connections_count,
        'communities_count': communities_count,
        'interested_ids': json.dumps(interested_ids),
    }
    return render(request, 'collaboration.html', context)


@login_required
def chat_view(request):
    if request.method == 'POST':
        _is_ajax = request.POST.get('_ajax') == '1'

        if request.POST.get('action') == 'delete_message':
            try:
                msg = Message.objects.get(id=request.POST.get('message_id'))
            except Message.DoesNotExist:
                if _is_ajax: return JsonResponse({'ok': False, 'error': 'Message not found.'})
                messages.error(request, 'Message not found.')
                return redirect('chat')
            if msg.sender != request.user:
                if _is_ajax: return JsonResponse({'ok': False, 'error': 'You can only delete your own messages.'})
                messages.error(request, 'You can only delete your own messages.')
            else:
                msg.delete()
                if _is_ajax: return JsonResponse({'ok': True})
                messages.success(request, 'Message deleted.')
            return redirect('chat')

        receiver = get_object_or_404(User, id=request.POST.get('receiver_id'))
        text = request.POST.get('text', '').strip()
        uploaded_file = request.FILES.get('file')
        err = None
        if receiver == request.user:
            err = 'You cannot message yourself.'
        elif receiver.role == 'admin' or receiver.is_superuser:
            err = 'Admin users cannot be messaged directly. Contact them via email or phone.'
        if err:
            if _is_ajax: return JsonResponse({'ok': False, 'error': err})
            messages.error(request, err)
            return redirect('chat')

	# Enforce that they must be connected, share a community, or have an active mentorship
        connected = Connection.objects.filter(
            Q(follower=request.user, following=receiver) | Q(follower=receiver, following=request.user)
        ).exists()
        mentorship_exists = Mentorship.objects.filter(
            Q(mentor=request.user, mentee=receiver) | Q(mentor=receiver, mentee=request.user),
            status='accepted'
        ).exists()
        mentorship_request_accepted = MentorshipRequest.objects.filter(
            Q(student=request.user, alumni=receiver) | Q(student=receiver, alumni=request.user),
            status='accepted'
        ).exists()
        if is_sem1to4_student(request.user) and receiver.role == 'alumni':
            if _is_ajax: return JsonResponse({'ok': False, 'error': 'Semester 1-4 students cannot directly message alumni.'})
            messages.error(request, 'Semester 1-4 students cannot directly message alumni. You can interact with alumni through community discussions.')
            return redirect('chat')

        user_comms = CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True)
        shared_comm = CommunityMember.objects.filter(user=receiver, community_id__in=user_comms).exists()
        can_message = connected or mentorship_exists or mentorship_request_accepted or shared_comm

        if is_student_to_alumni(request.user, receiver) and not can_message:
            if _is_ajax: return JsonResponse({'ok': False, 'error': 'Students and alumni can only message through an active mentorship or shared community.'})
            messages.error(request, 'Students and alumni can only message each other through an active mentorship or shared community.')
            return redirect('chat')

        if not can_message:
            if _is_ajax: return JsonResponse({'ok': False, 'error': 'You can only message users you are connected with, share a community with, or have an active mentorship with.'})
            messages.error(request, 'You can only message users you are connected with, share a community with, or have an active mentorship with.')
            return redirect('chat')

        if text or uploaded_file:
            if uploaded_file:
                file_error = validate_uploaded_file(uploaded_file, allowed_extensions=['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'], max_size_mb=10)
                if file_error:
                    if _is_ajax: return JsonResponse({'ok': False, 'error': file_error})
                    messages.error(request, file_error)
                    return redirect('chat')
            msg = Message.objects.create(sender=request.user, receiver=receiver, text=text, file=uploaded_file)
            if _is_ajax:
                return JsonResponse({
                    'ok': True,
                    'message': {
                        'id': msg.id,
                        'sender_id': msg.sender.id,
                        'text': msg.text,
                        'file': msg.file.url if msg.file else None,
                        'timestamp': msg.timestamp.isoformat(),
                    }
                })
            messages.success(request, 'Message sent.')
        else:
            if _is_ajax: return JsonResponse({'ok': False, 'error': 'Message cannot be empty.'})
            messages.error(request, 'Message cannot be empty.')
        return redirect('chat')

    users = User.objects.exclude(id=request.user.id).exclude(role='admin').exclude(is_superuser=True)
    if is_sem1to4_student(request.user):
        users = users.exclude(role='alumni')
    elif is_senior_student(request.user):
        allowed_alumni_ids = set()
        for c in Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)):
            allowed_alumni_ids.add(c.follower_id if c.following_id == request.user.id else c.following_id)
        for m in Mentorship.objects.filter(Q(mentor=request.user) | Q(mentee=request.user), status='accepted'):
            allowed_alumni_ids.add(m.mentor_id if m.mentee_id == request.user.id else m.mentee_id)
        for mr in MentorshipRequest.objects.filter(Q(student=request.user) | Q(alumni=request.user), status='accepted'):
            allowed_alumni_ids.add(mr.student_id if mr.alumni_id == request.user.id else mr.alumni_id)
        user_comms = list(CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True))
        if user_comms:
            for cm in CommunityMember.objects.filter(community_id__in=user_comms).exclude(user=request.user):
                allowed_alumni_ids.add(cm.user_id)
        users = users.filter(Q(role__in=['student', 'senior']) | (Q(role='alumni') & Q(id__in=allowed_alumni_ids)))
    elif is_alumni(request.user):
        users = users.exclude(role='student')

    conversation_partner_ids = set()
    raw_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-timestamp')

    messages_by_partner = {}
    for msg in raw_messages:
        partner = msg.receiver if msg.sender == request.user else msg.sender
        conversation_partner_ids.add(partner.id)
        if partner.id not in messages_by_partner:
            messages_by_partner[partner.id] = {
                'partner': partner,
                'messages': [],
            }
        messages_by_partner[partner.id]['messages'].append({
            'id': msg.id,
            'sender_id': msg.sender.id,
            'text': msg.text,
            'file': msg.file.url if msg.file else None,
            'timestamp': msg.timestamp.isoformat(),
        })

    conversations_list = []
    for pid, data in messages_by_partner.items():
        p = data['partner']
        msg_list = data['messages']
        last_msg = msg_list[0]
        last_text = last_msg['text'] or ('📎 ' + (last_msg['file'].split('/')[-1] if last_msg['file'] else 'File'))
        conversations_list.append({
            'id': p.id,
            'name': p.get_full_name() or p.cms,
            'avatar_initials': (p.get_full_name() and ''.join([x[0] for x in p.get_full_name().split()[:2]])) or p.cms[:2].upper(),
            'profile_pic': p.profile_pic.url if p.profile_pic else None,
            'last_message': last_text,
            'last_time': last_msg['timestamp'],
            'messages': sorted(msg_list, key=lambda x: x['timestamp']),
        })

    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    all_users = []
    for u in users:
        all_users.append({
            'id': u.id,
            'name': u.get_full_name() or u.cms,
            'role': u.role,
            'department': u.department,
            'avatar_initials': (u.get_full_name() and ''.join([x[0] for x in u.get_full_name().split()[:2]])) or u.cms[:2].upper(),
            'profile_pic': u.profile_pic.url if u.profile_pic else None,
        })

    def _escape_json(s):
        return s.replace('</script>', '<\\/script>').replace('</SCRIPT>', '<\\/SCRIPT>')

    context = {
        'users': users,
        'conversations_json': _escape_json(json.dumps(conversations_list)),
        'all_users_json': _escape_json(json.dumps(all_users)),
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'chat.html', context)


@login_required
def mentorship_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'start':
            mentor_id = request.POST.get('mentor_id')
            mentor = get_object_or_404(User, id=mentor_id)
            if mentor == request.user:
                messages.error(request, 'You cannot mentor yourself.')
                return redirect('mentorship')
            existing = Mentorship.objects.filter(
                Q(mentor=mentor, mentee=request.user) | Q(mentor=request.user, mentee=mentor)
            ).first()
            if existing:
                if existing.mentor == request.user:
                    if existing.status == 'pending':
                        messages.info(request, 'This user already sent you a request. Go to the My Requests tab to accept it.')
                    elif existing.status == 'accepted':
                        messages.info(request, 'Mentorship already active.')
                    elif existing.status == 'rejected':
                        existing.status = 'pending'
                        existing.save()
                        messages.success(request, 'Mentorship request re-sent from this user.')
                else:
                    if existing.status == 'pending':
                        messages.info(request, 'Request already pending.')
                    elif existing.status == 'accepted':
                        messages.info(request, 'Mentorship already active.')
                    elif existing.status == 'rejected':
                        existing.status = 'pending'
                        existing.save()
                        name = mentor.get_full_name() or mentor.cms
                        messages.success(request, f'Mentorship request re-sent to {name}.')
                        if mentor.role == 'alumni':
                            mr = MentorshipRequest.objects.filter(student=request.user, alumni=mentor).first()
                            if mr:
                                mr.status = 'pending'
                                mr.save()
                            else:
                                MentorshipRequest.objects.create(
                                    student=request.user, alumni=mentor,
                                    subject='Mentorship Request', reason='Re-sent request', status='pending'
                                )
            else:
                Mentorship.objects.create(mentor=mentor, mentee=request.user, status='pending')
                name = mentor.get_full_name() or mentor.cms
                messages.success(request, f'Mentorship request sent to {name}.')
                if mentor.role == 'alumni':
                    MentorshipRequest.objects.get_or_create(
                        student=request.user, alumni=mentor,
                        defaults={'subject': 'Mentorship Request', 'reason': 'Mentorship request from Mentorship page', 'status': 'pending'}
                    )
            return redirect('mentorship')

        elif action == 'accept':
            mentorship_id = request.POST.get('mentorship_id')
            mentorship = get_object_or_404(Mentorship, id=mentorship_id, mentor=request.user)
            mentorship.status = 'accepted'
            mentorship.save()
            messages.success(request, 'Mentorship request accepted.')
            return redirect('mentorship')

        elif action == 'reject':
            mentorship_id = request.POST.get('mentorship_id')
            mentorship = get_object_or_404(Mentorship, id=mentorship_id, mentor=request.user)
            mentorship.status = 'rejected'
            mentorship.save()
            messages.success(request, 'Mentorship request rejected.')
            return redirect('mentorship')

        return redirect('mentorship')

    mentors = User.objects.filter(
        Q(role='alumni') | Q(role='senior')
    ).exclude(id=request.user.id)

    my_mentorships = Mentorship.objects.filter(
        Q(mentor=request.user) | Q(mentee=request.user)
    ).select_related('mentor', 'mentee')

    mentor_mentorship_map = {}
    for ms in my_mentorships:
        other = ms.mentee if ms.mentor == request.user else ms.mentor
        if other.id not in mentor_mentorship_map or ms.mentor == request.user:
            mentor_mentorship_map[other.id] = {
                'id': ms.id,
                'status': ms.status,
                'is_mentor': ms.mentor == request.user,
            }

    mentors_data = []
    for m in mentors:
        info = mentor_mentorship_map.get(m.id)
        mentors_data.append({
            'id': m.id,
            'name': m.get_full_name() or m.cms,
            'avatar': m.get_full_name() and ''.join([p[0] for p in m.get_full_name().split()[:2]]) or m.cms[:2].upper(),
            'profile_pic': m.profile_pic.url if m.profile_pic else None,
            'role': m.role,
            'badge': 'Alumni',
            'dept': m.department,
            'semester': m.semester,
            'skills': [s.strip() for s in m.skills.split(',') if s.strip()] if m.skills else [],
            'bio': m.bio or '',
            'mentorship': info,
        })

    mentorship_requests_qs = MentorshipRequest.objects.filter(
        Q(student=request.user) | Q(alumni=request.user)
    ).select_related('student', 'alumni').order_by('-created_at')

    received_mentorships = Mentorship.objects.filter(
        mentor=request.user, status='pending'
    ).select_related('mentee')

    requests_data = []
    for mr in mentorship_requests_qs:
        if request.user == mr.alumni:
            other = mr.student
            is_received = True
        else:
            other = mr.alumni
            is_received = False
        requests_data.append({
            'id': mr.id,
            'other_id': other.id,
            'other_name': other.get_full_name() or other.cms,
            'other_dept': other.department,
            'other_profile_pic': other.profile_pic.url if other.profile_pic else None,
            'other_initials': ''.join([x[0] for x in other.get_full_name().split()[:2]]).upper() if other.get_full_name() else other.cms[:2].upper(),
            'subject': mr.subject,
            'reason': mr.reason,
            'status': mr.status,
            'created_at': mr.created_at.strftime('%b %d, %Y'),
            'is_received': is_received,
        })

    for ms in received_mentorships:
        other = ms.mentee
        if not any(r['other_id'] == other.id and r['status'] == 'pending' for r in requests_data):
            requests_data.append({
                'id': ms.id,
                'other_id': other.id,
                'other_name': other.get_full_name() or other.cms,
                'other_dept': other.department,
                'other_profile_pic': other.profile_pic.url if other.profile_pic else None,
                'other_initials': ''.join([x[0] for x in other.get_full_name().split()[:2]]).upper() if other.get_full_name() else other.cms[:2].upper(),
                'subject': 'Mentorship Request',
                'reason': '',
                'status': 'pending',
                'created_at': ms.created_at.strftime('%b %d, %Y'),
                'is_received': True,
            })

    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    context = {
        'mentors': mentors,
        'mentors_json': json.dumps(mentors_data),
        'my_mentorships': my_mentorships,
        'mentorship_requests_json': json.dumps(requests_data),
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'mentorship.html', context)


@login_required
def alumni_directory_view(request):
    departments = User.objects.filter(role='alumni').values_list('department', flat=True).distinct().order_by('department')
    industries = User.objects.filter(role='alumni').exclude(industry='').values_list('industry', flat=True).distinct().order_by('industry')
    grad_years = User.objects.filter(role='alumni').exclude(graduation_year__isnull=True).values_list('graduation_year', flat=True).distinct().order_by('-graduation_year')
    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    context = {
        'departments': departments,
        'industries': industries,
        'grad_years': grad_years,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'alumni_directory.html', context)


@login_required
def alumni_list_api(request):
    alumni = User.objects.filter(role='alumni', is_active=True).exclude(id=request.user.id)
    q = request.GET.get('q', '')
    dept = request.GET.get('department', '')
    industry = request.GET.get('industry', '')
    grad_year = request.GET.get('grad_year', '')
    if q:
        alumni = alumni.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(current_company__icontains=q) |
            Q(skills__icontains=q)
        )
    if dept:
        alumni = alumni.filter(department=dept)
    if industry:
        alumni = alumni.filter(industry=industry)
    if grad_year:
        try:
            alumni = alumni.filter(graduation_year=int(grad_year))
        except ValueError:
            pass
    data = []
    for a in alumni:
        existing_request = MentorshipRequest.objects.filter(student=request.user, alumni=a).first()
        request_status = None
        if existing_request:
            request_status = existing_request.status
        data.append({
            'id': a.id,
            'name': a.get_full_name() or a.cms,
            'department': a.department,
            'graduation_year': a.graduation_year,
            'current_company': a.current_company,
            'current_position': a.current_position,
            'industry': a.industry,
            'bio': a.bio or '',
            'skills': [s.strip() for s in a.skills.split(',') if s.strip()] if a.skills else [],
            'profile_pic': a.profile_pic.url if a.profile_pic else None,
            'initials': ''.join([x[0] for x in a.get_full_name().split()[:2]]).upper() if a.get_full_name() else a.cms[:2].upper(),
            'mentorship_request_status': request_status,
        })
    return JsonResponse({'alumni': data})


@login_required
@require_http_methods(['POST'])
def send_mentorship_request_api(request):
    alumni_id = request.POST.get('alumni_id')
    subject = request.POST.get('subject', '').strip()
    reason = request.POST.get('reason', '').strip()
    if not alumni_id or not subject or not reason:
        return JsonResponse({'error': 'All fields are required.'}, status=400)
    if not is_senior_student(request.user):
        return JsonResponse({'error': 'Only semester 5-8 students can send mentorship requests.'}, status=403)
    alumni = get_object_or_404(User, id=alumni_id, role='alumni')
    existing_mentorship = Mentorship.objects.filter(
        Q(mentor=alumni, mentee=request.user) | Q(mentor=request.user, mentee=alumni),
        status='accepted'
    ).first()
    if existing_mentorship:
        return JsonResponse({'error': 'You are already connected with this alumni through mentorship.'}, status=400)
    existing = MentorshipRequest.objects.filter(student=request.user, alumni=alumni).first()
    if existing:
        if existing.status == 'pending':
            return JsonResponse({'error': 'You already have a pending request with this alumni.'}, status=400)
        if existing.status == 'accepted':
            return JsonResponse({'error': 'You are already connected with this alumni.'}, status=400)
        if existing.status == 'rejected':
            existing.status = 'pending'
            existing.subject = subject
            existing.reason = reason
            existing.save()
            mentorship = Mentorship.objects.filter(
                Q(mentor=alumni, mentee=request.user) | Q(mentor=request.user, mentee=alumni)
            ).first()
            if mentorship:
                mentorship.status = 'pending'
                mentorship.save()
            else:
                Mentorship.objects.create(mentor=alumni, mentee=request.user, status='pending')
            return JsonResponse({'ok': True, 'status': 'pending', 'message': 'Request re-sent.'})
    MentorshipRequest.objects.create(student=request.user, alumni=alumni, subject=subject, reason=reason)
    Mentorship.objects.get_or_create(mentor=alumni, mentee=request.user, defaults={'status': 'pending'})
    return JsonResponse({'ok': True, 'status': 'pending', 'message': 'Mentorship request sent!'})


@login_required
def mentorship_requests_api(request):
    if is_alumni(request.user):
        requests_qs = MentorshipRequest.objects.filter(alumni=request.user).select_related('student').order_by('-created_at')
    elif is_senior_student(request.user):
        requests_qs = MentorshipRequest.objects.filter(student=request.user).select_related('alumni').order_by('-created_at')
    else:
        requests_qs = MentorshipRequest.objects.none()
    data = []
    for r in requests_qs:
        if is_alumni(request.user):
            other = r.student
        else:
            other = r.alumni
        data.append({
            'id': r.id,
            'other_id': other.id,
            'other_name': other.get_full_name() or other.cms,
            'other_department': other.department,
            'other_profile_pic': other.profile_pic.url if other.profile_pic else None,
            'other_initials': ''.join([x[0] for x in other.get_full_name().split()[:2]]).upper() if other.get_full_name() else other.cms[:2].upper(),
            'subject': r.subject,
            'reason': r.reason,
            'status': r.status,
            'created_at': r.created_at.strftime('%b %d, %Y'),
            'is_received': is_alumni(request.user),
        })
    return JsonResponse({'requests': data})


@login_required
@require_http_methods(['POST'])
def handle_mentorship_request_api(request):
    request_id = request.POST.get('request_id')
    action = request.POST.get('action')
    if not request_id or action not in ('accept', 'reject'):
        return JsonResponse({'error': 'Invalid request.'}, status=400)
    try:
        mentorship_request = MentorshipRequest.objects.get(id=request_id, alumni=request.user)
        is_mentorship_request = True
    except MentorshipRequest.DoesNotExist:
        try:
            mentorship = Mentorship.objects.get(id=request_id, mentor=request.user)
            is_mentorship_request = False
        except Mentorship.DoesNotExist:
            return JsonResponse({'error': 'Request not found.'}, status=404)

    if action == 'accept':
        if is_mentorship_request:
            mentorship_request.status = 'accepted'
            mentorship_request.save()
            existing_mentorship = Mentorship.objects.filter(
                mentor=request.user, mentee=mentorship_request.student
            ).first()
            if not existing_mentorship:
                Mentorship.objects.create(
                    mentor=request.user,
                    mentee=mentorship_request.student,
                    status='accepted'
                )
            else:
                existing_mentorship.status = 'accepted'
                existing_mentorship.save()
        else:
            mentorship.status = 'accepted'
            mentorship.save()
        return JsonResponse({'ok': True, 'status': 'accepted'})
    else:
        if is_mentorship_request:
            mentorship_request.status = 'rejected'
            mentorship_request.save()
            Mentorship.objects.filter(
                mentor=request.user, mentee=mentorship_request.student
            ).update(status='rejected')
        else:
            mentorship.status = 'rejected'
            mentorship.save()
        return JsonResponse({'ok': True, 'status': 'rejected'})


@login_required
@require_http_methods(['POST'])
def update_alumni_profile_api(request):
    if not is_alumni(request.user):
        return JsonResponse({'error': 'Only alumni can update professional info.'}, status=403)
    graduation_year = request.POST.get('graduation_year')
    current_company = request.POST.get('current_company', '').strip()
    current_position = request.POST.get('current_position', '').strip()
    industry = request.POST.get('industry', '').strip()
    if graduation_year:
        try:
            request.user.graduation_year = int(graduation_year)
        except ValueError:
            pass
    request.user.current_company = current_company
    request.user.current_position = current_position
    request.user.industry = industry
    request.user.save(update_fields=['graduation_year', 'current_company', 'current_position', 'industry'])
    return JsonResponse({'ok': True, 'message': 'Professional info updated!'})


def index(request):
    return render(request, 'index.html')


def privacy(request):
    return render(request, 'privacy.html')


def terms(request):
    return render(request, 'terms.html')


def contact(request):
    if request.method == 'POST':
        messages.success(request, 'Thank you! Your message has been sent. We will get back to you soon.')
        return redirect('contact')
    return render(request, 'contact.html')


@login_required
def community_chat_view(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    user_membership = CommunityMember.objects.filter(user=request.user, community=community).first()
    is_member = user_membership is not None

    if request.method == 'POST' and request.POST.get('action') == 'join_community':
        if is_member:
            messages.info(request, 'You are already a member of this community.')
        else:
            CommunityMember.objects.create(user=request.user, community=community)
            messages.success(request, f'You joined {community.name}!')
        return redirect('community_chat', community_id=community.id)

    if not is_member:
        messages.error(request, 'You must join this community to view the chat and messages.')
        return redirect('communities')

    is_admin = user_membership.is_admin if user_membership else False

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add_member':
            if not is_admin:
                messages.error(request, 'Only community admins can add members.')
                return redirect('community_chat', community_id=community.id)
            user_id = request.POST.get('user_id')
            target_user = get_object_or_404(User, id=user_id)
            _, created = CommunityMember.objects.get_or_create(user=target_user, community=community)
            if created:
                name = target_user.get_full_name() or target_user.cms
                messages.success(request, f'{name} added to the community.')
            else:
                messages.info(request, 'User is already a member.')
            return redirect('community_chat', community_id=community.id)

        if action == 'toggle_admin':
            if not is_admin:
                messages.error(request, 'Only community admins can manage admins.')
                return redirect('community_chat', community_id=community.id)
            member_id = request.POST.get('member_id')
            target_membership = get_object_or_404(CommunityMember, id=member_id, community=community)
            if target_membership.user == community.created_by or target_membership.user == request.user:
                messages.error(request, 'Cannot change admin status for this user.')
            else:
                target_membership.is_admin = not target_membership.is_admin
                target_membership.save()
                name = target_membership.user.get_full_name() or target_membership.user.cms
                status = 'promoted to admin' if target_membership.is_admin else 'demoted from admin'
                messages.success(request, f'{name} {status}.')
            return redirect('community_chat', community_id=community.id)


        if action == 'leave_community':
            if not is_member:
                messages.error(request, 'You are not a member of this community.')
            elif request.user == community.created_by:
                messages.error(request, 'You cannot leave a community you created. Transfer ownership first.')
            else:
                user_membership.delete()
                messages.success(request, f'You left {community.name}.')
            return redirect('community_chat', community_id=community.id)

        if action == 'delete_message':
            msg = get_object_or_404(CommunityMessage, id=request.POST.get('message_id'))
            if msg.sender != request.user:
                messages.error(request, 'You can only delete your own messages.')
            else:
                msg.delete()
                messages.success(request, 'Message deleted.')
            return redirect('community_chat', community_id=community.id)

        text = request.POST.get('text', '').strip()
        uploaded_file = request.FILES.get('file')
        if not is_member:
            messages.error(request, 'You must be a member to send messages.')
        elif community.message_permission == 'admins_only' and not is_admin:
            messages.error(request, 'Only admins can send messages in this community.')
        elif text or uploaded_file:
            if uploaded_file:
                file_error = validate_uploaded_file(uploaded_file, allowed_extensions=['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'], max_size_mb=10)
                if file_error:
                    messages.error(request, file_error)
                    return redirect('community_chat', community_id=community.id)
            CommunityMessage.objects.create(
                community=community,
                sender=request.user,
                text=text,
                file=uploaded_file,
            )
        return redirect('community_chat', community_id=community.id)

    messages_list = CommunityMessage.objects.filter(community=community).order_by('timestamp')
    all_members = CommunityMember.objects.filter(community=community).select_related('user')
    admin_ids = set(m.user_id for m in all_members if m.is_admin)
    members = all_members.exclude(is_admin=True)
    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('community_chat_messages.html', {
            'messages': messages_list,
            'user': request.user,
            'admin_ids': admin_ids,
        })
        return JsonResponse({'html': html})

    
    can_send = is_member and (community.message_permission == 'all_members' or is_admin)
    all_users_for_add = User.objects.exclude(id__in=[m.user_id for m in all_members]).exclude(id=request.user.id)

    context = {
        'community': community,
        'is_member': is_member,
        'is_admin': is_admin,
        'can_send': can_send,
        'admin_ids': admin_ids,
        'members': members,
        'messages': messages_list,
        'all_users_for_add': all_users_for_add,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'community_chat.html', context)


@login_required
def collaboration_chat_view(request, post_id):
    post = get_object_or_404(CollaborationPost, id=post_id)

    if request.method == 'POST':
        if request.POST.get('action') == 'delete_message':
            msg = get_object_or_404(CollaborationMessage, id=request.POST.get('message_id'))
            if msg.sender != request.user:
                messages.error(request, 'You can only delete your own messages.')
            else:
                msg.delete()
                messages.success(request, 'Message deleted.')
            return redirect('collaboration_chat', post_id=post.id)

        text = request.POST.get('text', '').strip()
        uploaded_file = request.FILES.get('file')
        if text or uploaded_file:
            if uploaded_file:
                file_error = validate_uploaded_file(uploaded_file, allowed_extensions=['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'], max_size_mb=10)
                if file_error:
                    messages.error(request, file_error)
                    return redirect('collaboration_chat', post_id=post.id)
            CollaborationMessage.objects.create(
                post=post,
                sender=request.user,
                text=text,
                file=uploaded_file,
            )
        return redirect('collaboration_chat', post_id=post.id)

    messages_list = CollaborationMessage.objects.filter(post=post).order_by('timestamp')
    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('collaboration_chat_messages.html', {
            'messages': messages_list,
            'user': request.user,
        })
        return JsonResponse({'html': html})

    context = {
        'post': post,
        'messages': messages_list,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'collaboration_chat.html', context)


@login_required
def mentorship_chat_view(request, mentorship_id):
    mentorship = get_object_or_404(Mentorship, id=mentorship_id)
    if request.user not in (mentorship.mentor, mentorship.mentee):
        messages.error(request, 'You are not part of this mentorship.')
        return redirect('mentorship')

    if mentorship.status != 'accepted':
        messages.error(request, 'Chat is only available after the mentor accepts your request.')
        return redirect('mentorship')

    if request.method == 'POST':
        if request.POST.get('action') == 'delete_message':
            msg = get_object_or_404(MentorshipMessage, id=request.POST.get('message_id'))
            if msg.sender != request.user:
                messages.error(request, 'You can only delete your own messages.')
            else:
                msg.delete()
                messages.success(request, 'Message deleted.')
            return redirect('mentorship_chat', mentorship_id=mentorship.id)

        text = request.POST.get('text', '').strip()
        uploaded_file = request.FILES.get('file')
        if text or uploaded_file:
            if uploaded_file:
                file_error = validate_uploaded_file(uploaded_file, allowed_extensions=['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'], max_size_mb=10)
                if file_error:
                    messages.error(request, file_error)
                    return redirect('mentorship_chat', mentorship_id=mentorship.id)
            MentorshipMessage.objects.create(
                mentorship=mentorship,
                sender=request.user,
                text=text,
                file=uploaded_file,
            )
        return redirect('mentorship_chat', mentorship_id=mentorship.id)

    messages_list = MentorshipMessage.objects.filter(mentorship=mentorship).order_by('timestamp')
    connections_count = Connection.objects.filter(
        Q(follower=request.user) | Q(following=request.user)
    ).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('mentorship_chat_messages.html', {
            'messages': messages_list,
            'user': request.user,
        })
        return JsonResponse({'html': html})

    context = {
        'mentorship': mentorship,
        'messages': messages_list,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'mentorship_chat.html', context)


@login_required
def notifications_api(request):
    if request.method == 'GET':
        notifications = Notification.objects.filter(recipient=request.user)[:20]
        data = []
        for n in notifications:
            data.append({
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'sender_id': n.sender_id,
                'sender_name': n.sender.get_full_name() or n.sender.cms if n.sender else '',
                'related_object_id': n.related_object_id,
                'created_at': n.created_at.strftime('%b %d, %Y %I:%M %p'),
            })
        return JsonResponse({'notifications': data})

    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            Notification.objects.filter(id=notification_id, recipient=request.user).update(is_read=True)
        else:
            Notification.objects.filter(recipient=request.user).update(is_read=True)
        return JsonResponse({'ok': True})


@login_required
def unread_notification_count_api(request):
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})
