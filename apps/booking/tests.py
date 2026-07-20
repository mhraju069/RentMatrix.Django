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
            price_daily=100.00,
            verified=True
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

    def test_owner_cannot_confirm_overlapping_booking(self):
        # Create a second booking with overlapping dates
        second_booking = Booking.objects.create(
            property=self.property,
            user=self.guest,
            name="Conflicting Booking",
            phone="0987654321",
            email="guest2@example.com",
            guest_count=1,
            check_in=self.booking.check_in,
            check_out=self.booking.check_out,
            price=300.00,
            status="PENDING"
        )

        self.client.force_authenticate(user=self.owner)
        
        # Confirm the first booking
        url_confirm_first = f"/booking/api/v1/owner/booking/confirm/{self.booking.id}/"
        res_first = self.client.patch(url_confirm_first)
        self.assertEqual(res_first.status_code, status.HTTP_200_OK)

        # Attempting to confirm the second booking should fail
        url_confirm_second = f"/booking/api/v1/owner/booking/confirm/{second_booking.id}/"
        res_second = self.client.patch(url_confirm_second)
        self.assertEqual(res_second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date conflict", res_second.data["message"])

    def test_guest_cannot_create_overlapping_booking(self):
        # Confirm the first booking first
        self.booking.status = "CONFIRMED"
        self.booking.save()

        # Try to create an overlapping booking via API as guest
        self.client.force_authenticate(user=self.guest)
        
        payload = {
            "property": str(self.property.id),
            "name": "Another Guest",
            "phone": "1234567890",
            "email": "another@example.com",
            "check_in": str(self.booking.check_in),
            "check_out": str(self.booking.check_out),
            "guest_count": 2,
            "price_type": "daily"
        }
        url = "/booking/api/v1/guest/booking/"
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This property is already booked for the selected dates.", str(response.data))

    def test_property_detail_includes_booked_ranges(self):
        # Confirm the booking first
        self.booking.status = "CONFIRMED"
        self.booking.save()

        self.client.force_authenticate(user=self.guest)
        url = f"/property/api/v1/guest/property/{self.property.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify booked_ranges is present and populated
        self.assertIn("booked_ranges", response.data)
        self.assertEqual(len(response.data["booked_ranges"]), 1)
        self.assertEqual(response.data["booked_ranges"][0]["check_in"], str(self.booking.check_in))
        self.assertEqual(response.data["booked_ranges"][0]["check_out"], str(self.booking.check_out))

    def test_create_booking_with_security_document(self):
        self.client.force_authenticate(user=self.guest)
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a dummy file for the security document
        dummy_file = SimpleUploadedFile("security_doc.pdf", b"dummy content", content_type="application/pdf")
        
        payload = {
            "property": str(self.property.id),
            "name": "Guest With Doc",
            "phone": "1234567890",
            "email": "docguest@example.com",
            "check_in": str(datetime.date.today() + datetime.timedelta(days=10)),
            "check_out": str(datetime.date.today() + datetime.timedelta(days=13)),
            "guest_count": 2,
            "price_type": "daily",
            "security_document": dummy_file
        }
        url = "/booking/api/v1/guest/booking/"
        response = self.client.post(url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the security document is saved in the db and returned in list/detail serialization
        booking_id = response.data["data"]["id"]
        booking = Booking.objects.get(id=booking_id)
        self.assertTrue(booking.security_document.name.endswith("security_doc.pdf"))
        
        self.assertIn("security_document", response.data["data"])
        self.assertIsNotNone(response.data["data"]["security_document"])
        
        # Verify retrieve detail also includes security_document
        url_detail = f"/booking/api/v1/guest/booking/{booking_id}/"
        res_detail = self.client.get(url_detail)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertIn("security_document", res_detail.data["data"])
        self.assertIsNotNone(res_detail.data["data"]["security_document"])


