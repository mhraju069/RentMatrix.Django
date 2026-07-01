from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import DeviceToken, Notification, NotifySettings
from .serializers import DeviceTokenSerializer, NotificationSerializer, NotifySettingsSerializer
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

class NotifySettingsView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotifySettingsSerializer

    @extend_schema(responses={200: NotifySettingsSerializer})
    def get(self, request):
        settings_obj, created = NotifySettings.objects.get_or_create(user=request.user)
        serializer = NotifySettingsSerializer(settings_obj)
        return Response({
            "status": 200,
            "success": True,
            "message": "Notification settings fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        request=NotifySettingsSerializer,
        responses={200: NotifySettingsSerializer}
    )
    def patch(self, request):
        settings_obj, created = NotifySettings.objects.get_or_create(user=request.user)
        
        toggle_field = request.data.get('toggle')
        if toggle_field in ['booking', 'checkin']:
            current_val = getattr(settings_obj, toggle_field)
            setattr(settings_obj, toggle_field, not current_val)
            settings_obj.save()
            serializer = NotifySettingsSerializer(settings_obj)
            return Response({
                "status": 200,
                "success": True,
                "message": f"Successfully toggled {toggle_field}",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
        serializer = NotifySettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": 200,
                "success": True,
                "message": "Notification settings updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "status": 400,
            "success": False,
            "errors": format_serializer_errors(serializer.errors)
        }, status=status.HTTP_400_BAD_REQUEST)
