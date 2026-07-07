from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from ..models import User, Notification, Connection, CommunityMember
from ..permissions import is_sem1to4_student


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
