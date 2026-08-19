"""
ASGI config for CampNect_Backend project.

Serves both HTTP and WebSocket (real-time chat) traffic.
If Django Channels is not installed (or incompatible), the app
gracefully falls back to a plain HTTP-only ASGI application so the
site keeps working (clients fall back to polling).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CampNect_Backend.settings')

django_asgi_app = get_asgi_application()

application = django_asgi_app

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from core.routing import websocket_urlpatterns

    if websocket_urlpatterns:
        application = ProtocolTypeRouter({
            'http': django_asgi_app,
            'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
        })
except Exception:
    # channels/daphne not available or incompatible — HTTP-only ASGI app (chat falls back to polling).
    pass
