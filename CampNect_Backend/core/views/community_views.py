from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.template.loader import render_to_string
from ..models import User, Community, CommunityMember, CommunityMessage, Connection
from ..forms import CommunityCreateForm
from .utils import validate_uploaded_file


@login_required
def communities_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            form = CommunityCreateForm(request.POST)
            if form.is_valid():
                community = form.save(commit=False)
                community.created_by = request.user
                community.save()
                membership, _ = CommunityMember.objects.get_or_create(user=request.user, community=community)
                membership.is_admin = True
                membership.save()
                messages.success(request, 'Community created successfully.')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
            return redirect('communities')

        if action == 'join_community':
            community = get_object_or_404(Community, id=request.POST.get('community_id'))
            _, created = CommunityMember.objects.get_or_create(user=request.user, community=community)
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
            deleted, _ = CommunityMember.objects.filter(user=request.user, community=community).delete()
            if deleted:
                messages.success(request, f'You left {community.name}.')
            else:
                messages.error(request, 'You are not a member of this community.')
            return redirect('communities')

    communities = Community.objects.annotate(member_count=Count('members'))
    my_communities = Community.objects.filter(members__user=request.user).annotate(member_count=Count('members')).distinct()
    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    context = {
        'communities': communities,
        'my_communities': my_communities,
        'connections_count': connections_count,
        'communities_count': communities_count,
    }
    return render(request, 'communities.html', context)


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
            CommunityMessage.objects.create(community=community, sender=request.user, text=text, file=uploaded_file)
        return redirect('community_chat', community_id=community.id)

    messages_list = CommunityMessage.objects.filter(community=community).order_by('timestamp')
    all_members = CommunityMember.objects.filter(community=community).select_related('user')
    admin_ids = set(m.user_id for m in all_members if m.is_admin)
    members = all_members.exclude(user__is_superuser=True)
    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
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
