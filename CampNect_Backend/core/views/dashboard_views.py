import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q

from ..models import (
    User, Announcement, AnnouncementLike, AnnouncementComment,
    CollaborationPost, CollaborationPostLike, CollaborationPostComment,
    Note, Community, CommunityMember, Connection, Mentorship,
    MentorshipRequest, Discussion, CareerOpportunity, Notification,
)
from ..permissions import is_admin, is_alumni, is_sem1to4_student, is_senior_student, is_student_to_alumni
from .utils import validate_uploaded_file


@login_required
def dashboard(request):
    # AJAX handlers
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
                    try:
                        parent = AnnouncementComment.objects.get(id=parent_id, announcement=ann)
                    except AnnouncementComment.DoesNotExist:
                        pass
                c = AnnouncementComment.objects.create(user=request.user, announcement=ann, text=text, parent=parent)
                return JsonResponse({'id': c.id, 'user': request.user.get_full_name() or request.user.cms, 'text': c.text, 'parent_id': c.parent_id, 'created_at': c.created_at.isoformat()})
            elif post_type == 'collaboration':
                post = get_object_or_404(CollaborationPost, id=post_id)
                parent = None
                if parent_id:
                    try:
                        parent = CollaborationPostComment.objects.get(id=parent_id, post=post)
                    except CollaborationPostComment.DoesNotExist:
                        pass
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

    # Regular POST
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
                Notification.objects.create(
                    recipient=target, sender=request.user,
                    notification_type=Notification.Type.CONNECTION,
                    title=f'{request.user.get_full_name() or request.user.cms} connected with you',
                )
            else:
                Connection.objects.get_or_create(follower=request.user, following=target)
                messages.success(request, f'Connected with {target.get_full_name() or target.cms}.')
                Notification.objects.create(
                    recipient=target, sender=request.user,
                    notification_type=Notification.Type.CONNECTION,
                    title=f'{request.user.get_full_name() or request.user.cms} connected with you',
                )
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

    # GET
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

    connections_count = Connection.objects.filter(Q(follower=user) | Q(following=user)).count()
    communities_count = CommunityMember.objects.filter(user=user).count()
    notes_count = Note.objects.filter(uploaded_by=user).count()
    projects_count = CollaborationPost.objects.filter(posted_by=user).count()

    user_notes = Note.objects.filter(uploaded_by=user).order_by('-upload_date')[:5]
    user_memberships = CommunityMember.objects.filter(user=user).select_related('community').order_by('-joined_at')[:5]
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
    connections_count = Connection.objects.filter(Q(follower=profile_user) | Q(following=profile_user)).count()
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
