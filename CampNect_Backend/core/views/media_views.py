from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.static import serve
from django.conf import settings

from ..models import Message, CommunityMessage, CollaborationMessage, MentorshipMessage, Note, CommunityMember


@login_required
def protected_media(request, path):
    """Serve uploaded media only to authorized users.

    Uploaded files are grouped by upload directory, so authorization is
    decided from the owning record before delegating to Django's static
    ``serve`` view (which still performs ``safe_join`` path traversal
    protection, content-type detection and 404 handling).

    * ``chat_files/``          - only the sender/receiver of the 1:1 message
    * ``community_chat/``      - only members of the community
    * ``collaboration_chat/``  - any authenticated user (matches the open
                                 collaboration chat view)
    * ``mentorship_chat/``     - only the mentor and mentee
    * ``notes/`` ``profiles/`` - any authenticated user
    """
    if path.startswith('chat_files/'):
        msg = Message.objects.filter(file=path).first()
        if msg is None:
            raise Http404('File not found.')
        if request.user not in (msg.sender, msg.receiver):
            return HttpResponse('Forbidden', status=403)
    elif path.startswith('community_chat/'):
        msg = CommunityMessage.objects.filter(file=path).first()
        if msg is None:
            raise Http404('File not found.')
        if not CommunityMember.objects.filter(user=request.user, community=msg.community).exists():
            return HttpResponse('Forbidden', status=403)
    elif path.startswith('collaboration_chat/'):
        msg = CollaborationMessage.objects.filter(file=path).first()
        if msg is None:
            raise Http404('File not found.')
    elif path.startswith('mentorship_chat/'):
        msg = MentorshipMessage.objects.filter(file=path).first()
        if msg is None:
            raise Http404('File not found.')
        if request.user not in (msg.mentorship.mentor, msg.mentorship.mentee):
            return HttpResponse('Forbidden', status=403)
    elif path.startswith('notes/') or path.startswith('profiles/'):
        # Notes and profile pictures are readable by any authenticated user.
        pass
    else:
        raise Http404('File not found.')

    return serve(request, path, document_root=settings.MEDIA_ROOT)
