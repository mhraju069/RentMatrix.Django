import uuid
from django.db import models
from apps.property.models import Property
from django.conf import settings

# Create your models here.

STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('CONFIRMED', 'Confirmed'),
    ('CHECKED_IN', 'Checked In'),
    ('CHECKED_OUT', 'Checked Out'),
    ('CANCELLED', 'Cancelled'),
]


class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    email = models.CharField(max_length=100)    
    guest_count = models.IntegerField()
    check_in = models.DateField()
    check_out = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    cancel_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking for {self.property.name} by {self.user.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == 'CONFIRMED':
            from apps.auth.models import Document
            Document.objects.filter(user=self.user).update(is_verified=True)

