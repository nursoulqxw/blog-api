from rest_framework.throttling import SimpleRateThrottle


class PostCreateUserThrottle(SimpleRateThrottle):
    scope = "post_create"

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return f"user:{request.user.id}"