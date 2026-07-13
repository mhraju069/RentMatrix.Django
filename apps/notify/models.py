import uuid
from django.db import models
from django.conf import settings


class NotifySettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notify_settings')
    booking = models.BooleanField(default=True)
    checkin = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Notify Settings'
        verbose_name_plural = 'Notify Settings'

    def __str__(self):
        return f"{self.user.email} - {self.booking} - {self.checkin}"
    


class DeviceToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Device Token'
        verbose_name_plural = 'Device Tokens'

    def __str__(self):
        return f"{self.user.email} - {self.token}"



class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(max_length=50, blank=True, null=True)
    related_id = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class Announcement(models.Model):
    USER_GROUPS = [
        ('ALL', 'All Users'),
        ('GUESTS', 'Guests Only'),
        ('OWNERS', 'Owners Only'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    body = models.TextField()
    user_group = models.CharField(max_length=20, choices=USER_GROUPS, default='ALL')
    sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'

    def __str__(self):
        return f"{self.title} ({self.get_user_group_display()})"

    def save(self, *args, **kwargs):
        should_send = not self.sent
        super().save(*args, **kwargs)
        
        if should_send:
            from django.contrib.auth import get_user_model
            from .models import DeviceToken, Notification
            from .utils import send_notification
            
            User = get_user_model()
            users = User.objects.filter(is_active=True)
            if self.user_group == 'GUESTS':
                users = users.filter(role='guest')
            elif self.user_group == 'OWNERS':
                users = users.filter(role='owner')
            elif self.user_group == 'ALL':
                users = users.filter(role__in=['guest', 'owner'])
                
            for user in users:
                notification = Notification.objects.create(
                    user=user,
                    title=self.title,
                    body=self.body,
                    notification_type='announcement',
                    related_id=str(self.id)
                )
                
                tokens = DeviceToken.objects.filter(user=user)
                extra_data = {
                    "id": str(notification.id),
                    "type": "announcement",
                    "related_id": str(self.id),
                }
                for token_obj in tokens:
                    try:
                        send_notification(token_obj.token, self.title, self.body, data=extra_data)
                    except Exception as e:
                        print(f"Error sending announcement to {user.email}: {e}")
            
            self.sent = True
            super().save(update_fields=['sent'])