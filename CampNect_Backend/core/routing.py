"""
WebSocket URL routing for all chat types.

Defined only when Django Channels is available; otherwise the list is empty
and asgi.py serves HTTP only (clients fall back to polling).
"""
from .consumers import CHANNELS_AVAILABLE

websocket_urlpatterns = []

if CHANNELS_AVAILABLE:
    from django.urls import re_path
    from . import consumers

    websocket_urlpatterns = [
        re_path(r'ws/chat/(?P<user_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
        re_path(r'ws/community/(?P<community_id>\d+)/$', consumers.CommunityChatConsumer.as_asgi()),
        re_path(r'ws/collaboration/(?P<post_id>\d+)/$', consumers.CollaborationChatConsumer.as_asgi()),
        re_path(r'ws/mentorship/(?P<mentorship_id>\d+)/$', consumers.MentorshipChatConsumer.as_asgi()),
    ]
