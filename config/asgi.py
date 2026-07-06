"""
ASGI config for config project — HTTP + WebSocket (Django Channels).
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.conf import settings

django_asgi_app = get_asgi_application()

from core.routing import websocket_urlpatterns  # noqa: E402

_ws_inner = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
_ws_app = (
    AllowedHostsOriginValidator(_ws_inner)
    if not settings.DEBUG
    else _ws_inner
)

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': _ws_app,
})
