import os

# Ensure settings are configured before importing any Django modules or app code
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Reuse Django's ASGI application for HTTP and lifespan so servers
# (uvicorn, daphne) see that the lifespan protocol is supported.
django_asgi_app = get_asgi_application()

# Import routing after Django is initialized so model imports in consumers
# (which depend on app registry) don't run too early.
import chat.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(chat.routing.websocket_urlpatterns)
    ),
    # Forward lifespan events to the Django ASGI application
    "lifespan": django_asgi_app,
})