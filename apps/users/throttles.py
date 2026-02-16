from rest_framework.throttling import SimpleRateThrottle


class RegisterIPThrottle(SimpleRateThrottle):
    scope = "register"

    def get_cache_key(self, request, view):
        return self.get_ident(request)


class TokenIPThrottle(SimpleRateThrottle):
    scope = "token"

    def get_cache_key(self, request, view):
        return self.get_ident(request)
