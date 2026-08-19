"""
WebSocket consumers for real-time chat.

Each consumer adds the authenticated user to a channel group named after
the conversation, so when a new message is created in a view it can be
broadcast instantly to all connected participants.

All Channels imports are lazy: if channels/daphne are not installed (or are
incompatible with the installed Django), the consumer classes are simply not
defined and `broadcast_message` silently no-ops — views keep working and
clients fall back to the existing HTTP polling.
"""
from django.db.models import Q

from .models import (
    User, Connection, Mentorship, MentorshipRequest,
    CommunityMember, CollaborationPost,
)
from .permissions import is_sem1to4_student


def _message_payload(msg):
    return {
        'id': msg.id,
        'sender_id': msg.sender.id,
        'text': msg.text,
        'file': msg.file.url if msg.file else None,
        'timestamp': msg.timestamp.isoformat(),
    }


def group_name_1to1(user_id_a, user_id_b):
    low, high = sorted([int(user_id_a), int(user_id_b)])
    return f'chat_{low}_{high}'


def broadcast_message(group_name, msg):
    """
    Best-effort push of a newly created message to a Channels group.

    Safe to call even when Channels is not installed / misconfigured —
    it silently no-ops so chat still works via polling.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            group_name,
            {'type': 'chat_message', 'message': _message_payload(msg)},
        )
    except Exception:
        pass


def broadcast_message_deleted(group_name, message_id):
    """
    Best-effort push of a message deletion to a Channels group.

    Safe to call even when Channels is not installed / misconfigured —
    it silently no-ops so chat still works via polling.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            group_name,
            {'type': 'chat_message_deleted', 'message_id': message_id},
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Consumers — only defined when Channels is available.
# ---------------------------------------------------------------------------
try:
    from channels.db import database_sync_to_async
    from channels.generic.websocket import AsyncJsonWebsocketConsumer
    CHANNELS_AVAILABLE = True
except Exception:
    CHANNELS_AVAILABLE = False

if CHANNELS_AVAILABLE:

    def _can_message(user, other_id):
        """Replicate chat_views permission checks for the 1:1 consumer."""
        if not user.is_authenticated:
            return False
        other = User.objects.filter(id=other_id).first()
        if not other or other.id == user.id:
            return False
        if other.role == 'admin' or other.is_superuser:
            return False
        if is_sem1to4_student(user) and other.role == 'alumni':
            return False
        if is_sem1to4_student(other) and user.role == 'alumni':
            return False
        connected = Connection.objects.filter(
            Q(follower=user, following=other) | Q(follower=other, following=user)
        ).exists()
        if connected:
            return True
        mentorship = Mentorship.objects.filter(
            Q(mentor=user, mentee=other) | Q(mentor=other, mentee=user), status='accepted'
        ).exists()
        if mentorship:
            return True
        req_accepted = MentorshipRequest.objects.filter(
            Q(student=user, alumni=other) | Q(student=other, alumni=user), status='accepted'
        ).exists()
        if req_accepted:
            return True
        user_comms = list(CommunityMember.objects.filter(user=user).values_list('community_id', flat=True))
        return CommunityMember.objects.filter(user=other, community_id__in=user_comms).exists()

    def _is_community_member(user, community_id):
        return CommunityMember.objects.filter(user=user, community_id=community_id).exists()

    def _collab_post_exists(post_id):
        return CollaborationPost.objects.filter(id=post_id).exists()

    def _is_mentorship_participant(user, mentorship_id):
        return Mentorship.objects.filter(id=mentorship_id).filter(
            Q(mentor=user) | Q(mentee=user)
        ).exists()

    class ChatConsumer(AsyncJsonWebsocketConsumer):
        async def connect(self):
            user = self.scope.get('user')
            if user is None or not user.is_authenticated:
                await self.close()
                return
            other_id = self.scope['url_route']['kwargs']['user_id']
            if not await database_sync_to_async(_can_message)(user, other_id):
                await self.close()
                return
            self.group_name = group_name_1to1(user.id, other_id)
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

        async def disconnect(self, close_code):
            group = getattr(self, 'group_name', None)
            if group:
                await self.channel_layer.group_discard(group, self.channel_name)

        async def chat_message(self, event):
            await self.send_json({'type': 'chat_message', 'message': event['message']})

        async def chat_message_deleted(self, event):
            await self.send_json({'type': 'chat_message_deleted', 'message_id': event['message_id']})

    class CommunityChatConsumer(AsyncJsonWebsocketConsumer):
        async def connect(self):
            user = self.scope.get('user')
            if user is None or not user.is_authenticated:
                await self.close()
                return
            community_id = self.scope['url_route']['kwargs']['community_id']
            if not await database_sync_to_async(_is_community_member)(user, community_id):
                await self.close()
                return
            self.group_name = f'community_{community_id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

        async def disconnect(self, close_code):
            group = getattr(self, 'group_name', None)
            if group:
                await self.channel_layer.group_discard(group, self.channel_name)

        async def chat_message(self, event):
            await self.send_json({'type': 'chat_message', 'message': event['message']})

    class CollaborationChatConsumer(AsyncJsonWebsocketConsumer):
        async def connect(self):
            user = self.scope.get('user')
            if user is None or not user.is_authenticated:
                await self.close()
                return
            post_id = self.scope['url_route']['kwargs']['post_id']
            if not await database_sync_to_async(_collab_post_exists)(post_id):
                await self.close()
                return
            self.group_name = f'collaboration_{post_id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

        async def disconnect(self, close_code):
            group = getattr(self, 'group_name', None)
            if group:
                await self.channel_layer.group_discard(group, self.channel_name)

        async def chat_message(self, event):
            await self.send_json({'type': 'chat_message', 'message': event['message']})

    class MentorshipChatConsumer(AsyncJsonWebsocketConsumer):
        async def connect(self):
            user = self.scope.get('user')
            if user is None or not user.is_authenticated:
                await self.close()
                return
            mentorship_id = self.scope['url_route']['kwargs']['mentorship_id']
            if not await database_sync_to_async(_is_mentorship_participant)(user, mentorship_id):
                await self.close()
                return
            self.group_name = f'mentorship_{mentorship_id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

        async def disconnect(self, close_code):
            group = getattr(self, 'group_name', None)
            if group:
                await self.channel_layer.group_discard(group, self.channel_name)

        async def chat_message(self, event):
            await self.send_json({'type': 'chat_message', 'message': event['message']})
