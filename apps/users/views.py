from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import logging 
logger = logging.getLogger("users")

from .serializers import RegisterSerializer, UserSerializer
from .throttles import RegisterIPThrottle




class RegisterViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        logger.info("Registration attempt for email: %s", request.data.get("email"))

        try:
            serializer = RegisterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
        except Exception:
            logger.exception("Registration failed for email: %s", request.data.get("email"))
            raise

        logger.info("User registered: %s", user.email)

        throttle_classes = [RegisterIPThrottle]

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )
