from rest_framework import serializers
from .models import DeviceToken, Notification, NotifySettings

class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ['token']

class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='notification_type', required=False, allow_null=True)

    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'type', 'related_id', 'is_read', 'created_at']

class NotifySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotifySettings
        fields = ['booking', 'checkin']
