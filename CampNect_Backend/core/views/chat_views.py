import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from ..models import User, Message, Connection, Mentorship, MentorshipRequest, CommunityMember, Notification
from ..permissions import is_alumni, is_sem1to4_student, is_senior_student, is_student_to_alumni
from .utils import validate_uploaded_file, _escape_json


@login_required
def chat_view(request):
    if request.method == 'GET' and request.GET.get('ajax') == '1':
        user_id = request.GET.get('user_id')
        if user_id:
            partner = get_object_or_404(User, id=user_id)
            msgs = Message.objects.filter(
                Q(sender=request.user, receiver=partner) | Q(sender=partner, receiver=request.user)
            ).order_by('timestamp')
            msgs_data = [{
                'id': m.id,
                'sender_id': m.sender.id,
                'text': m.text,
                'file': m.file.url if m.file else None,
                'timestamp': m.timestamp.isoformat(),
            } for m in msgs]
            return JsonResponse({'ok': True, 'messages': msgs_data})
        return JsonResponse({'ok': False, 'error': 'No user_id provided'})

    if request.method == 'POST':
        _is_ajax = request.POST.get('_ajax') == '1'

        if request.POST.get('action') == 'delete_message':
            try:
                msg = Message.objects.get(id=request.POST.get('message_id'))
            except Message.DoesNotExist:
                if _is_ajax:
                    return JsonResponse({'ok': False, 'error': 'Message not found.'})
                messages.error(request, 'Message not found.')
                return redirect('chat')
            if msg.sender != request.user:
                if _is_ajax:
                    return JsonResponse({'ok': False, 'error': 'You can only delete your own messages.'})
                messages.error(request, 'You can only delete your own messages.')
            else:
                msg.delete()
                if _is_ajax:
                    return JsonResponse({'ok': True})
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
            if _is_ajax:
                return JsonResponse({'ok': False, 'error': err})
            messages.error(request, err)
            return redirect('chat')

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
            if _is_ajax:
                return JsonResponse({'ok': False, 'error': 'Semester 1-4 students cannot directly message alumni.'})
            messages.error(request, 'Semester 1-4 students cannot directly message alumni. You can interact with alumni through community discussions.')
            return redirect('chat')

        user_comms = CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True)
        shared_comm = CommunityMember.objects.filter(user=receiver, community_id__in=user_comms).exists()
        can_message = connected or mentorship_exists or mentorship_request_accepted or shared_comm

        if is_student_to_alumni(request.user, receiver) and not can_message:
            if _is_ajax:
                return JsonResponse({'ok': False, 'error': 'Students and alumni can only message through an active mentorship or shared community.'})
            messages.error(request, 'Students and alumni can only message each other through an active mentorship or shared community.')
            return redirect('chat')

        if not can_message:
            if _is_ajax:
                return JsonResponse({'ok': False, 'error': 'You can only message users you are connected with, share a community with, or have an active mentorship with.'})
            messages.error(request, 'You can only message users you are connected with, share a community with, or have an active mentorship with.')
            return redirect('chat')

        if text or uploaded_file:
            if uploaded_file:
                file_error = validate_uploaded_file(uploaded_file, allowed_extensions=['pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt'], max_size_mb=10)
                if file_error:
                    if _is_ajax:
                        return JsonResponse({'ok': False, 'error': file_error})
                    messages.error(request, file_error)
                    return redirect('chat')
            msg = Message.objects.create(sender=request.user, receiver=receiver, text=text, file=uploaded_file)

            Notification.objects.create(
                recipient=receiver,
                sender=request.user,
                notification_type=Notification.Type.NEW_MESSAGE,
                title=f'New message from {request.user.get_full_name() or request.user.cms}',
                message=text[:100] if text else 'Sent a file',
                related_object_id=msg.id,
            )

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
            if _is_ajax:
                return JsonResponse({'ok': False, 'error': 'Message cannot be empty.'})
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
    raw_messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-timestamp')

    messages_by_partner = {}
    for msg in raw_messages:
        partner = msg.receiver if msg.sender == request.user else msg.sender
        conversation_partner_ids.add(partner.id)
        if partner.id not in messages_by_partner:
            messages_by_partner[partner.id] = {'partner': partner, 'messages': []}
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

    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
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

    context = {
        'users': users,
        'conversations_json': _escape_json(json.dumps(conversations_list)),
        'all_users_json': _escape_json(json.dumps(all_users)),
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'chat.html', context)
