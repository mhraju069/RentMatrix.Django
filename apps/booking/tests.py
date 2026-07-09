from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from apps.property.models import Property
from apps.booking.models import Booking
import datetime

User = get_user_model()

class OwnerBookingTests(APITestCase):
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

    def test_owner_booking_list_contains_guest_data(self):
        response = self.client.get("/booking/api/v1/owner/booking/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        booking_data = response.data["data"][0]
        self.assertEqual(booking_data["guest_name"], "John Guest Booking")
        self.assertEqual(booking_data["guest_phone"], "1234567890")
        self.assertEqual(booking_data["guest_email"], "guest@example.com")
        self.assertEqual(booking_data["check_in"], str(datetime.date.today()))
        self.assertEqual(booking_data["check_out"], str(datetime.date.today() + datetime.timedelta(days=3)))
        self.assertEqual(int(float(booking_data["price"])), 300)
        self.assertEqual(booking_data["guest_count"], 2)
        self.assertEqual(booking_data["user"]["name"], "John Guest")

    def test_booking_details_contains_documents(self):
        from apps.auth.models import Document
        # Create a document for the guest
        doc = Document.objects.create(
            user=self.guest,
            document_type="NID",
            document_file="documents/nid.png",
            is_verified=True
        )

        # 1. Retrieve as owner
        url_owner = f"/booking/api/v1/owner/booking/{self.booking.id}/"
        response_owner = self.client.get(url_owner)
        self.assertEqual(response_owner.status_code, status.HTTP_200_OK)
        self.assertIn("docs", response_owner.data)
        self.assertEqual(len(response_owner.data["docs"]), 1)
        self.assertEqual(response_owner.data["docs"][0]["document_type"], "NID")
        self.assertEqual(response_owner.data["docs"][0]["is_verified"], True)

        # 2. Retrieve as guest
        self.client.force_authenticate(user=self.guest)
        url_guest = f"/booking/api/v1/guest/booking/{self.booking.id}/"
        response_guest = self.client.get(url_guest)
        self.assertEqual(response_guest.status_code, status.HTTP_200_OK)
        self.assertIn("docs", response_guest.data)
        self.assertEqual(len(response_guest.data["docs"]), 1)
        self.assertEqual(response_guest.data["docs"][0]["document_type"], "NID")
        self.assertEqual(response_guest.data["docs"][0]["is_verified"], True)
        # Check inside data -> documents
        self.assertIn("documents", response_guest.data["data"])
        self.assertEqual(len(response_guest.data["data"]["documents"]), 1)
        self.assertEqual(response_guest.data["data"]["documents"][0]["is_verified"], True)

    def test_booking_figma_layout_fields_and_status_filtering(self):
        self.client.force_authenticate(user=self.guest)

        url_pending = "/booking/api/v1/guest/booking/?status=PENDING"
        response_pending = self.client.get(url_pending)
        self.assertEqual(response_pending.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_pending.data["data"]), 1)

        url_active = "/booking/api/v1/guest/booking/?status=ACTIVE"
        response_active = self.client.get(url_active)
        self.assertEqual(response_active.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_active.data["data"]), 0)

        url_detail = f"/booking/api/v1/guest/booking/{self.booking.id}/"
        response_detail = self.client.get(url_detail)
        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)
        data = response_detail.data["data"]
        
        self.assertIn("booking_status_tracker", data)
        self.assertIn("security_approval_tracker", data)
        
        self.assertTrue(data["booking_status_tracker"]["request_submitted"])
        self.assertTrue(data["booking_status_tracker"]["host_review"])
        self.assertFalse(data["booking_status_tracker"]["approved"])

    def test_owner_confirm_booking_auto_approves_documents(self):
        from apps.auth.models import Document
        
        doc = Document.objects.create(
            user=self.guest,
            document_type="Passport",
            document_file="documents/passport.png",
            is_verified=False
        )

        self.client.force_authenticate(user=self.owner)

        url_confirm = f"/booking/api/v1/owner/booking/confirm/{self.booking.id}/"
        response = self.client.patch(url_confirm)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "CONFIRMED")

        doc.refresh_from_db()
        self.assertTrue(doc.is_verified)

    def test_owner_decline_booking(self):
        self.client.force_authenticate(user=self.owner)

        url_decline = f"/booking/api/v1/owner/booking/decline/{self.booking.id}/"
        response = self.client.patch(url_decline)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "DECLINED")
