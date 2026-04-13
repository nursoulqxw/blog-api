from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.blog.views import PostViewSet, post_stream, post_poll
from apps.blog.stats_views import stats_view


router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="posts")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),

    # Auth endpoints (register, token, token/refresh, preferences)
    path("api/auth/", include("apps.users.urls")),

    # SSE stream — must come before the router so "stream" isn't matched as a slug
    path("api/posts/stream/", post_stream, name="post-stream"),
    # HTTP Polling — must come before router for the same reason
    path("api/posts/poll/", post_poll, name="post-poll"),

    path("api/notifications/", include("apps.notifications.urls")),

    # Blog endpoints
    path("api/", include(router.urls)),

    # Stats (async, no auth required)
    path("api/stats/", stats_view, name="stats"),


    # OpenAPI docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]