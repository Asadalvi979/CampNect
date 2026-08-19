import json
import calendar as _cal
from datetime import timedelta
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import ExtractYear, ExtractMonth
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from ..models import User, Community, CommunityMember, Note, Announcement, CollaborationPost, CollaborationPostInterest, Message, Mentorship, Connection
from ..permissions import is_admin


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
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(cms__icontains=q) | Q(email__icontains=q) |
            Q(department__icontains=q) | Q(role__icontains=q)
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
    notes = Note.objects.select_related('uploaded_by').all()
    notes_subjects = Note.objects.values_list('subject', flat=True).distinct().order_by('subject')
    if q and tbl == 'notes':
        notes = notes.filter(
            Q(title__icontains=q) | Q(subject__icontains=q) |
            Q(uploaded_by__first_name__icontains=q) | Q(uploaded_by__last_name__icontains=q)
        )
    announcements = Announcement.objects.select_related('posted_by').all()
    if q and tbl == 'announcements':
        announcements = announcements.filter(title__icontains=q)
    collab_posts = CollaborationPost.objects.annotate(
        interest_count=Count('interests'),
        comment_count=Count('comments'),
    ).select_related('posted_by', 'mentor').prefetch_related('interests__user', 'comments__user')
    messages_list = Message.objects.select_related('sender', 'receiver').all()
    mentorships = Mentorship.objects.select_related('mentor', 'mentee').all()

    total_users = User.objects.count()
    active_users_count = User.objects.filter(is_active=True).count()
    mentorships_count = Mentorship.objects.count()
    connections_total = Connection.objects.count()

    last_7 = timezone.now() - timedelta(days=7)

    recent_users = User.objects.all().order_by('-date_joined')[:8]
    recent_communities = Community.objects.select_related('created_by').order_by('-created_at')[:5]
    recent_notes = Note.objects.select_related('uploaded_by').order_by('-upload_date')[:5]
    recent_collab = CollaborationPost.objects.select_related('posted_by', 'mentor').order_by('-date_posted')[:5]
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

    twelve_months_ago = timezone.now() - timedelta(days=365)

    months_12 = []
    for i in range(11, -1, -1):
        m = (timezone.now().month - i - 1) % 12 + 1
        months_12.append(_cal.month_abbr[m])

    mq = User.objects.filter(date_joined__gte=twelve_months_ago).annotate(
        y=ExtractYear('date_joined'), mo=ExtractMonth('date_joined')
    ).values('y', 'mo').annotate(c=Count('id')).order_by('y', 'mo')
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

    mn_qs = Note.objects.filter(upload_date__gte=twelve_months_ago).annotate(
        y=ExtractYear('upload_date'), mo=ExtractMonth('upload_date')
    ).values('y', 'mo').annotate(c=Count('id')).order_by('y', 'mo')
    nm_map = {}
    for m in mn_qs:
        if m['y'] and m['mo']:
            nm_map[_cal.month_abbr[int(m['mo'])]] = m['c']

    mc_qs = CollaborationPost.objects.filter(date_posted__gte=twelve_months_ago).annotate(
        y=ExtractYear('date_posted'), mo=ExtractMonth('date_posted')
    ).values('y', 'mo').annotate(c=Count('id')).order_by('y', 'mo')
    cm_map = {}
    for m in mc_qs:
        if m['y'] and m['mo']:
            cm_map[_cal.month_abbr[int(m['mo'])]] = m['c']

    all_months_set = set(ug_map.keys()) | set(nm_map.keys()) | set(cm_map.keys())
    all_months = sorted(all_months_set, key=lambda x: list(_cal.month_abbr).index(x)) if all_months_set else months_12[:]
    eg_new_users = [ug_map.get(m, 0) for m in all_months]
    eg_notes = [nm_map.get(m, 0) for m in all_months]
    eg_collab = [cm_map.get(m, 0) for m in all_months]

    role_map = dict(User.Role.choices)
    role_qs = list(User.objects.values('role').annotate(c=Count('id')))
    role_labels = [role_map.get(r['role'], r['role']) for r in role_qs]
    role_data = [r['c'] for r in role_qs]

    top_communities_lb = Community.objects.select_related('created_by').annotate(mc=Count('members')).order_by('-mc')[:20]
    communities_lb = [{
        'name': c.name, 'category': c.get_category_display(), 'members': c.mc,
        'creator': f'{c.created_by.first_name} {c.created_by.last_name}' if c.created_by else '-',
        'created': c.created_at.strftime('%b %Y') if c.created_at else '-',
    } for c in top_communities_lb]

    dept_agg = User.objects.values('department').exclude(department='').annotate(
        total=Count('id'),
        students=Count('id', filter=Q(role='student')),
        seniors=Count('id', filter=Q(role='senior')),
        alumni=Count('id', filter=Q(role='alumni')),
    ).order_by('-total')[:20]
    departments_lb = [d for d in dept_agg]

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
        insights.append(f'Platform has reached {total_users} total users with {active_users_count} active members, a {growth_rate}% month-over-month growth rate.')
    if total_communities and communities_lb:
        insights.append(f'{total_communities} communities exist with an average of {avg_members} members each. Top community "{communities_lb[0]["name"]}" leads with {communities_lb[0]["members"]} members.')
    if total_notes_count:
        top_subj = Note.objects.values('subject').annotate(c=Count('id')).order_by('-c').first()
        insights.append(f'{total_notes_count} notes have been shared across the platform. Most popular subject: {top_subj["subject"]} ({top_subj["c"]} notes).')
    if total_collab:
        insights.append(f'{total_collab} collaboration projects posted, fostering cross-disciplinary teamwork.')
    if total_seniors and total_students:
        ratio = round(total_seniors / max(total_students, 1) * 100, 1)
        insights.append(f'Seniors represent {ratio}% of the student body, indicating strong mentoring pipeline.')
    if total_alumni and dept_agg:
        insights.append(f'{total_alumni} alumni remain connected to the platform, with top engagement from the "{dept_agg[0]["department"]}" department.')

    analytics = {
        'userGrowth': {'labels': ug_labels, 'monthly': ug_monthly, 'cumulative': ug_cum},
        'engagementTrends': {'labels': all_months, 'newUsers': eg_new_users, 'notes': eg_notes, 'collab': eg_collab},
        'roleDist': {'labels': role_labels, 'data': role_data},
        'topCommunities': communities_lb,
        'topDepartments': [{'department': d['department'], 'total': d['total'], 'students': d['students'], 'seniors': d['seniors'], 'alumni': d['alumni']} for d in departments_lb],
        'insights': insights,
    }

    context = {
        'users': users, 'communities': communities, 'notes': notes, 'notes_subjects': notes_subjects,
        'announcements': announcements, 'pinned_announcements': announcements.filter(is_pinned=True),
        'analytics': analytics, 'analytics_json': json.dumps(analytics),
        'collab_posts': collab_posts,
        'projects_json': json.dumps([{
            'id': p.id, 'title': p.title, 'description': p.description[:200] if p.description else '',
            'skills': p.get_skills_list(), 'roles': p.get_roles_list(),
            'postedBy': f'{p.posted_by.first_name} {p.posted_by.last_name}', 'postedById': p.posted_by.id,
            'date': p.date_posted.strftime('%b %d, %Y') if p.date_posted else '',
            'interestCount': p.interest_count, 'commentCount': p.comment_count,
            'mentorId': p.mentor_id,
            'mentorName': f'{p.mentor.first_name} {p.mentor.last_name}' if p.mentor else None,
        } for p in collab_posts]),
        'available_mentors_json': json.dumps([{
            'id': u.id, 'name': f'{u.first_name} {u.last_name}',
            'role': u.get_role_display(), 'department': u.department,
        } for u in User.objects.filter(role__in=['senior', 'alumni', 'admin']).order_by('first_name')]),
        'mentorships': mentorships, 'messages_list': messages_list,
        'total_users': total_users, 'active_users_count': active_users_count,
        'mentorships_count': mentorships_count, 'connections_total': connections_total,
        'all_activities': all_activities, 'new_users_week': new_users_week,
        'inactive_users_count': inactive_users_count, 'empty_communities_count': empty_communities_count,
        'recent_notes_count': recent_notes_count, 'recent_collab_count': recent_collab_count,
        'tab': request.GET.get('tab', 'dashboard'), 'q': q, 'tbl': tbl, 'departments': departments,
        'selected_role': role_filter, 'selected_dept': dept_filter, 'selected_sem': sem_filter,
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

    if action == 'update_user':
        user_id = request.POST.get('user_id')
        try:
            u = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        if u.id == request.user.id:
            role = request.POST.get('role')
            is_active_raw = request.POST.get('is_active')
            if (role and role != 'admin') or (is_active_raw is not None and is_active_raw != '1'):
                return JsonResponse({'error': 'You cannot demote or deactivate your own account.'}, status=400)
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
        if str(user_id) == str(request.user.id):
            return JsonResponse({'error': 'You cannot delete your own account.'}, status=400)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        for note in Note.objects.filter(uploaded_by=user):
            if note.file:
                note.file.delete(save=False)
        user.delete()
        return JsonResponse({'ok': True})

    if action == 'create_community':
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)
        c = Community.objects.create(
            name=name, description=request.POST.get('description', '').strip(),
            category=request.POST.get('category', 'general'), created_by=request.user,
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
            'id': m.id, 'user_id': m.user.id, 'name': f"{m.user.first_name} {m.user.last_name}",
            'cms': m.user.cms, 'is_admin': m.is_admin,
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

    if action == 'create_announcement':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        by_line = request.POST.get('by_line', '').strip()
        if not title or not content:
            return JsonResponse({'error': 'Title and content are required'}, status=400)
        a = Announcement.objects.create(title=title, content=content, by_line=by_line, posted_by=request.user)
        return JsonResponse({'ok': True, 'id': a.id, 'title': a.title, 'author': a.get_by_line(), 'date': a.date_posted.strftime('%b %d, %Y')})

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

    if action == 'delete_note':
        note_id = request.POST.get('note_id')
        try:
            note = Note.objects.get(id=note_id)
        except Note.DoesNotExist:
            return JsonResponse({'error': 'Note not found'}, status=404)
        if note.file:
            note.file.delete(save=False)
        note.delete()
        return JsonResponse({'ok': True})

    if action == 'get_project_detail':
        pid = request.POST.get('project_id')
        try:
            p = CollaborationPost.objects.prefetch_related('interests__user', 'comments__user', 'likes__user').get(id=pid)
        except CollaborationPost.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        interests = [{
            'id': i.id, 'userId': i.user.id, 'name': f'{i.user.first_name} {i.user.last_name}',
            'role': i.user.get_role_display(), 'status': i.status,
        } for i in p.interests.all()]
        comments = [{
            'id': c.id, 'userId': c.user.id, 'name': f'{c.user.first_name} {c.user.last_name}',
            'text': c.text, 'date': c.created_at.strftime('%b %d') if c.created_at else '',
        } for c in p.comments.all()]
        return JsonResponse({'ok': True, 'project': {
            'id': p.id, 'title': p.title, 'description': p.description,
            'skills': p.get_skills_list(), 'roles': p.get_roles_list(),
            'postedBy': f'{p.posted_by.first_name} {p.posted_by.last_name}',
            'date': p.date_posted.strftime('%b %d, %Y') if p.date_posted else '',
            'mentorId': p.mentor_id, 'mentorName': f'{p.mentor.first_name} {p.mentor.last_name}' if p.mentor else None,
            'interests': interests, 'teamMembers': [i for i in interests if i['status'] == 'team'],
            'comments': comments,
        }})

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
