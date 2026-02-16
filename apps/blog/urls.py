from rest_framework.routers import DefaultRouter
# from .views import PostViewSet, CommentViewSet
from apps.blog.views import PostViewSet


router = DefaultRouter()
# router.register(r"posts", PostViewSet, basename="posts")
# router.register(r"comments", CommentViewSet, basename="comments")

urlpatterns = router.urls

from apps.blog.views import PostViewSet

router.register(r"posts", PostViewSet, basename="posts")

