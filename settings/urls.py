from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.users.views import RegisterViewSet
from apps.blog.views import PostViewSet
from apps.users.auth_views import LoggingTokenObtainPairView


router = DefaultRouter()
router.register(r"auth/register", RegisterViewSet, basename="register")
router.register(r"posts", PostViewSet, basename="posts")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    

    # JWT
    
    path(
        "api/auth/token/",
        LoggingTokenObtainPairView.as_view(),
        name="token",
    ),
    path(
        "api/auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # API router
    path("api/", include(router.urls)),
]
