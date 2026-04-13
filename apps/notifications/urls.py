from django.urls import path
from .views import NotificationCountView, NotificationListView, MarkAllReadView

urlpatterns = [
    path('', NotificationListView.as_view(), name = 'notification-list'),
    path('count/', NotificationCountView.as_view(), name = 'notification-count'),
    path('read/', MarkAllReadView.as_view(), name = 'notification-mark-read'),
]