from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
import json
from apps.property.models import Property, Amenity, Gallery, AdvantgePrice, AddOnsPrice, SeasonalPrice

User = get_user_model()

class PropertyDRFTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.user.is_active = True
        self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_create_property_drf(self):
        # A valid 1x1 pixel transparent GIF image
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
            "amenities": json.dumps([
                {"name": "WiFi"},
                {"name": "Swimming Pool"}
            ]),
            "gallery": json.dumps([
                {"type": "IMAGE"}
            ]),
            "advantage_prices": json.dumps([
                {"service": "Airport Pickup", "price": 25}
            ]),
            "add_ons_prices": json.dumps([
                {"service": "Extra Bed", "price": 15}
            ]),
            "season_prices": json.dumps([
                {"start": "2026-06-01", "end": "2026-08-31", "price": 180}
            ])
        }

        # The view is routed at /api/v1/owner/property/create/ in config/api.py
        response = self.client.post("/api/v1/owner/property/create/", data, format="multipart")
        print("RESPONSE STATUS:", response.status_code)
        print("RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        # Verify database objects
        property_obj = Property.objects.filter(name="Luxury Oceanfront Condo").first()
        self.assertIsNotNone(property_obj)
        self.assertEqual(property_obj.owner, self.user)
        self.assertEqual(property_obj.amenities.count(), 2)
        self.assertEqual(property_obj.galleries.count(), 1)
        self.assertEqual(property_obj.advantge_prices.count(), 1)
        self.assertEqual(property_obj.add_ons_prices.count(), 1)
        self.assertEqual(property_obj.season_prices.count(), 1)

    def test_update_property_drf(self):
        # Create an initial property
        property_obj = Property.objects.create(
            owner=self.user,
            name="Initial Name",
            address="Initial Address",
            bedroom=1,
            bathroom=1,
            price_daily=100.00
        )
        Amenity.objects.create(property=property_obj, name="Initial Amenity")

        # Prepare update data (partial update: only name, price_daily, amenities, and advantage_prices)
        data = {
            "name": "Updated Name",
            "price_daily": 120.00,
            "amenities": json.dumps([
                {"name": "Updated Amenity 1"},
                {"name": "Updated Amenity 2"}
            ]),
            "advantage_prices": json.dumps([
                {"service": "Laundry", "price": 10}
            ])
        }

        url = f"/api/v1/owner/property/update/{property_obj.id}/"
        response = self.client.post(url, data, format="multipart")
        print("UPDATE RESPONSE STATUS:", response.status_code)
        print("UPDATE RESPONSE DATA:", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Refresh from database and verify updates
        property_obj.refresh_from_db()
        self.assertEqual(property_obj.name, "Updated Name")
        self.assertEqual(float(property_obj.price_daily), 120.00)
        # Verify amenities were replaced
        self.assertEqual(property_obj.amenities.count(), 2)
        self.assertTrue(property_obj.amenities.filter(name="Updated Amenity 1").exists())
        self.assertFalse(property_obj.amenities.filter(name="Initial Amenity").exists())
        # Verify advantage prices were created
        self.assertEqual(property_obj.advantge_prices.count(), 1)
        self.assertEqual(property_obj.advantge_prices.first().service, "Laundry")
