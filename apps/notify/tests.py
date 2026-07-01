from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from apps.property.models import Property
from apps.booking.models import Booking
from apps.notify.models import Notification
from apps.notify.utils import booking_reminder, send_checkin_reminder, send_checkout_reminder
import datetime

User = get_user_model()

class NotificationTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="password", name="Property Owner")
        self.guest = User.objects.create_user(email="guest@example.com", password="password", name="John Guest")
        self.client.force_authenticate(user=self.owner)

        self.property = Property.objects.create(
            owner=self.owner,
            name="Beach Side Villa",
            address="123 Ocean Drive",
            bedroom=2,
            bathroom=2,
            price_daily=100.00
        )

        self.booking = Booking.objects.create(
            property=self.property,
            user=self.guest,
            name="John Guest Booking",
            phone="1234567890",
            email="guest@example.com",
            guest_count=2,
            check_in=datetime.date.today(),
            check_out=datetime.date.today() + datetime.timedelta(days=3),
            price=300.00,
            status="PENDING"
        )

    def test_booking_notification_fields(self):
        # Trigger booking notification
        booking_reminder(self.owner, self.booking)

        # Check in DB
        notif = Notification.objects.filter(user=self.owner).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, "booking")
        self.assertEqual(notif.related_id, str(self.booking.id))

        # Check API list response
        response = self.client.get("/notify/api/v1/owner/notify/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif_data = response.data["data"][0]
        self.assertEqual(notif_data["type"], "booking")
        self.assertEqual(notif_data["related_id"], str(self.booking.id))

    def test_checkin_checkout_notification_fields(self):
        # Trigger check-in notification
        send_checkin_reminder(self.owner, self.booking)
        notif = Notification.objects.filter(user=self.owner, notification_type="about to check in").first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.related_id, str(self.booking.id))

        # Trigger check-out notification
        send_checkout_reminder(self.owner, self.booking)
        notif_out = Notification.objects.filter(user=self.owner, notification_type="about to check out").first()
        self.assertIsNotNone(notif_out)
        self.assertEqual(notif_out.related_id, str(self.booking.id))

    def test_notify_settings_get_and_toggle(self):
        self.client.force_authenticate(user=self.guest)
        
        # 1. GET settings (should auto-create with defaults = True)
        url = "/notify/api/v1/settings/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["data"]["booking"])
        self.assertTrue(response.data["data"]["checkin"])
        
        # 2. Toggle booking using PATCH (explicit field update)
        response_patch = self.client.patch(url, {"booking": False}, format="json")
        self.assertEqual(response_patch.status_code, status.HTTP_200_OK)
        self.assertFalse(response_patch.data["data"]["booking"])
        self.assertTrue(response_patch.data["data"]["checkin"])
        
        # 3. Toggle checkin using toggle parameter
        response_toggle = self.client.patch(url, {"toggle": "checkin"}, format="json")
        self.assertEqual(response_toggle.status_code, status.HTTP_200_OK)
        self.assertFalse(response_toggle.data["data"]["checkin"])
        
        # 4. Toggle checkin again using toggle parameter (should flip to True)
        response_toggle2 = self.client.patch(url, {"toggle": "checkin"}, format="json")
        self.assertEqual(response_toggle2.status_code, status.HTTP_200_OK)
        self.assertTrue(response_toggle2.data["data"]["checkin"])
