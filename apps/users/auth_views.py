import logging
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from .throttles import TokenIPThrottle



logger = logging.getLogger("users")



class LoggingTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [TokenIPThrottle]
    def post(self, request, *args, **kwargs):
        email = request.data.get("email") or request.data.get("username")
        logger.info("Login attempt for: %s", email)

        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            logger.exception("Login failed for: %s", email)
            raise

        if response.status_code == 200:
            logger.info("Login success for: %s", email)
        else:
            logger.warning("Login failed for: %s, status=%s", email, response.status_code)

        return response
