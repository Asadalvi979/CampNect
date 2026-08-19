from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.template.loader import render_to_string
from ..models import CollaborationPost, CollaborationPostInterest, CollaborationMessage, Connection, CommunityMember
from ..forms import CollaborationPostForm
from .utils import validate_uploaded_file
from ..consumers import broadcast_message


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

        form = CollaborationPostForm(request.POST)
        if form.is_valid():
            collab = form.save(commit=False)
            collab.posted_by = request.user
            collab.save()
            messages.success(request, 'Project posted successfully.')
            return redirect('collaboration')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
            return redirect('collaboration')

    posts = CollaborationPost.objects.select_related('posted_by', 'mentor').annotate(interest_count=Count('interests')).order_by('-date_posted')
    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
    communities_count = CommunityMember.objects.filter(user=request.user).count()
    interested_ids = list(CollaborationPostInterest.objects.filter(user=request.user).values_list('post_id', flat=True))
    context = {
        'posts': posts,
        'connections_count': connections_count,
        'communities_count': communities_count,
        'interested_ids': interested_ids,
    }
    return render(request, 'collaboration.html', context)


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
            msg = CollaborationMessage.objects.create(post=post, sender=request.user, text=text, file=uploaded_file)
            broadcast_message(f'collaboration_{post.id}', msg)
        return redirect('collaboration_chat', post_id=post.id)

    messages_list = CollaborationMessage.objects.filter(post=post).select_related('sender').order_by('timestamp')
    connections_count = Connection.objects.filter(Q(follower=request.user) | Q(following=request.user)).count()
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
