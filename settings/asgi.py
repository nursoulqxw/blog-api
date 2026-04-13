# ASGI (Asynchronous Server Gateway Interface)
import os
import django
from decouple import config

_env_id = config("BLOG_ENV_ID", default="local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{_env_id}")

# Must call setup() before importing any app modules (e.g. routing, consumers)
# to ensure the app registry is ready.
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from apps.notifications import routing

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': URLRouter(
        routing.websocket_urlpatterns
    )
})
