from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import DeviceToken, Notification
from .serializers import DeviceTokenSerializer, NotificationSerializer
from apps.auth.utils import format_serializer_errors

class AddDeviceTokenView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceTokenSerializer

    @extend_schema(request=DeviceTokenSerializer)
    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            obj, created = DeviceToken.objects.get_or_create(user=request.user, token=token)
            if not created:
                return Response({"status": 200, "success": True, "message": "Device token already saved"}, status=status.HTTP_200_OK)
            return Response({"status": 200, "success": True, "message": "Device token saved successfully"}, status=status.HTTP_200_OK)
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": 200, "success": True, "message": "Notifications fetched successfully",
            "data": serializer.data
        })
