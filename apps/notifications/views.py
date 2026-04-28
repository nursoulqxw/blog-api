# HTTP Polling trade-off:
# Polling is simple — standard HTTP, no persistent connections, works everywhere, easy to scale
# horizontally behind a load balancer with no sticky sessions.
# Downsides: latency is at best N seconds (your poll interval), and every client fires a request
# every N seconds even when nothing changed — wasted load at scale.
# Acceptable when: updates are not time-critical (e.g. notification badges, dashboard stats),
# user count is moderate, and infra is simple.
# Switch to WebSockets when: you need sub-second delivery (chat, live collaboration, games).
# Switch to SSE when: updates are server->client only and you want lower overhead than WebSockets.

#Django modules
from django.shortcuts import render

#Django REST modues
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

#Project modules
from .models import Notification
from .serializers import NotificationSerializer

# Create your views here.

class NotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user, is_read=False).order_by('-created_at')
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(notifications, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"marked_read":updated})
