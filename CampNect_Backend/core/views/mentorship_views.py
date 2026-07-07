import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from ..models import User, Mentorship, MentorshipRequest, MentorshipMessage, Connection, CommunityMember
from ..permissions import is_alumni, is_senior_student
from ..forms import MentorshipRequestForm
from .utils import validate_uploaded_file


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

    mentors = User.objects.filter(Q(role='alumni') | Q(role='senior')).exclude(id=request.user.id)

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

    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
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
            MentorshipMessage.objects.create(mentorship=mentorship, sender=request.user, text=text, file=uploaded_file)
        return redirect('mentorship_chat', mentorship_id=mentorship.id)

    messages_list = MentorshipMessage.objects.filter(mentorship=mentorship).order_by('timestamp')
    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
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
def alumni_list_api(request):
    alumni = User.objects.filter(role='alumni', is_active=True).exclude(id=request.user.id)
    q = request.GET.get('q', '')
    dept = request.GET.get('department', '')
    industry = request.GET.get('industry', '')
    grad_year = request.GET.get('grad_year', '')
    if q:
        alumni = alumni.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(current_company__icontains=q) | Q(skills__icontains=q)
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
            existing_mentorship = Mentorship.objects.filter(mentor=request.user, mentee=mentorship_request.student).first()
            if not existing_mentorship:
                Mentorship.objects.create(mentor=request.user, mentee=mentorship_request.student, status='accepted')
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
            Mentorship.objects.filter(mentor=request.user, mentee=mentorship_request.student).update(status='rejected')
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
