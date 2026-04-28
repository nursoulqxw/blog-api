#Python modules
from django.urls import path

#Django REST modules
from rest_framework_simplejwt.views import TokenRefreshView

#Project modules
from apps.users.auth_views import LoggingTokenObtainPairView
from apps.users.views import RegisterViewSet, UserPreferencesViewSet


urlpatterns = [
    path(
        "register/",
        RegisterViewSet.as_view({"post": "create"}),
        name="register",
    ),
    path(
        "token/",
        LoggingTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "preferences/language/",
        UserPreferencesViewSet.as_view({"patch": "update_language"}),
        name="update_language",
    ),
    path(
        "preferences/timezone/",
        UserPreferencesViewSet.as_view({"patch": "update_timezone"}),
        name="update_timezone",
    ),
]