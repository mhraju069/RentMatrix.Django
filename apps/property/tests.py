from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
import json
from apps.property.models import Property, Gallery, AddOnsPrice, Reports

User = get_user_model()

class PropertyDRFTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.user.is_active = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_create_property_drf(self):
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        cover_file = SimpleUploadedFile("cover.gif", gif_bytes, content_type="image/gif")
        gallery_file = SimpleUploadedFile("gallery1.gif", gif_bytes, content_type="image/gif")

        data = {
            "name": "Luxury Oceanfront Condo",
            "about": "A beautiful condo with a direct view of the sea.",
            "price_daily": 150.00,
            "price_monthly": 4000.00,
            "bathroom": 2,
            "bedroom": 3,
            "area": "1500 sqft",
            "type": "APARTMENT",
            "status": "AVAILABLE",
            "verified": "true",
            "sea_view": "true",
            "address": "123 Marine Drive",
            "latitude": 21.43,
            "longitude": 91.98,
            "cover": cover_file,
            "gallery_files": [gallery_file],
            "gallery": json.dumps([
                {"type": "IMAGE"}
            ]),
            "add_ons_prices": json.dumps([
                {"service": "Extra Bed", "price": 15}
            ]),
            "weekend_dates": json.dumps({
                "weekend": ["FRI", "SAT"],
                "price": 180
            }),
            "vacations": json.dumps({
                "month": ["JUN", "JUL"],
                "price": 200
            }),
            "other_charges": json.dumps([
                {"name": "Cleaning Fee", "price": 50}
            ])
        }

        response = self.client.post("/property/api/v1/owner/create-property/", data, format="multipart")
        print("RESPONSE STATUS:", response.status_code)
        print("RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        # Verify database objects
        property_obj = Property.objects.filter(name="Luxury Oceanfront Condo").first()
        self.assertIsNotNone(property_obj)
        self.assertEqual(property_obj.owner, self.user)
        self.assertEqual(property_obj.galleries.count(), 1)
        self.assertEqual(property_obj.add_ons_prices.count(), 1)
        self.assertIsNotNone(property_obj.weekend_dates)
        self.assertIsNotNone(property_obj.vacations)
        self.assertEqual(property_obj.other_charges.count(), 1)

    def test_update_property_drf(self):
        property_obj = Property.objects.create(
            owner=self.user,
            name="Initial Name",
            address="Initial Address",
            bedroom=1,
            bathroom=1,
            price_daily=100.00
        )

        data = {
            "name": "Updated Name",
            "price_daily": 120.00,
            "add_ons_prices": json.dumps([
                {"service": "Laundry", "price": 10}
            ])
        }

        url = f"/property/api/v1/owner/update-property/{property_obj.id}/"
        response = self.client.patch(url, data, format="multipart")
        print("UPDATE RESPONSE STATUS:", response.status_code)
        print("UPDATE RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Refresh from database and verify updates
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.name, "Updated Name")
        self.assertEqual(float(property_obj.price_daily), 120.00)
        self.assertEqual(property_obj.add_ons_prices.count(), 1)
        self.assertEqual(property_obj.add_ons_prices.first().service, "Laundry")

    def test_report_property(self):
        # Create a property to report
        property_obj = Property.objects.create(
            owner=self.user,
            name="Test Property to Report",
            address="Some Address",
            bedroom=1,
            bathroom=1,
            price_daily=100.00
        )

        # 1. Test POST report
        data = {
            "property": str(property_obj.id),
            "reason": "Spam listing",
            "description": "This listing is duplicate and fake."
        }
        response = self.client.post("/property/api/v1/guest/report/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Verify DB
        report = Reports.objects.filter(property=property_obj, user=self.user).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reason, "Spam listing")

        # 2. Test GET reports
        response = self.client.get("/property/api/v1/guest/report/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["reason"], "Spam listing")
