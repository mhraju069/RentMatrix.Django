from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
import json
from apps.property.models import Property, Gallery, AddOnsPrice, Reports, Review
from apps.booking.models import Booking

User = get_user_model()

class PropertyDRFTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.user.is_active = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
        # Get or create currencies
        from apps.others.models import Currency
        self.usd, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$", "exchange_rate": 1.0})
        self.bdt, _ = Currency.objects.get_or_create(code="BDT", defaults={"name": "Bangladeshi Taka", "symbol": "৳", "exchange_rate": 117.0})

    def test_create_property_drf(self):
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        cover_file = SimpleUploadedFile("cover.gif", gif_bytes, content_type="image/gif")
        gallery_file = SimpleUploadedFile("gallery1.gif", gif_bytes, content_type="image/gif")

        data = {
            "name": "Luxury Oceanfront Condo",
            "about": "A beautiful condo with a direct view of the sea.",
            "price_daily": 150.00,
            "price_monthly": 4000.00,
            "currency_code": "USD",
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
            "amenities": json.dumps([
                {"name": "WiFi"},
                {"name": "Pool"}
            ]),
            "activities": json.dumps([
                {"name": "Beach Music Fest", "details": "Annual music event"},
                {"name": "Surfing Competition", "details": "Pro surfers meet"}
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
        self.assertEqual(property_obj.amenities.count(), 2)
        self.assertEqual(property_obj.activities.count(), 2)
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
            price_daily=100.00,
            verified=True
        )

        data = {
            "name": "Updated Name",
            "price_daily": 120.00,
            "currency_code": "USD",
            "add_ons_prices": json.dumps([
                {"service": "Laundry", "price": 10}
            ]),
            "amenities": json.dumps([
                {"name": "AC"}
            ]),
            "activities": json.dumps([
                {"name": "Beach Music Fest", "details": "Updated details"}
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
        self.assertEqual(property_obj.amenities.count(), 1)
        self.assertEqual(property_obj.amenities.first().name, "AC")
        self.assertEqual(property_obj.activities.count(), 1)
        self.assertEqual(property_obj.activities.first().name, "Beach Music Fest")
        self.assertEqual(property_obj.activities.first().details, "Updated details")

    def test_report_property(self):
        # Create a property to report
        property_obj = Property.objects.create(
            owner=self.user,
            name="Test Property to Report",
            address="Some Address",
            bedroom=1,
            bathroom=1,
            price_daily=100.00,
            verified=True
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

    def test_owner_property_performance_and_metrics(self):
        from datetime import date, timedelta
        # Create multiple properties
        p1 = Property.objects.create(
            owner=self.user,
            name="Top Performer Condo",
            address="Dhaka",
            bedroom=2,
            bathroom=2,
            price_daily=150.00,
            verified=True
        )
        p2 = Property.objects.create(
            owner=self.user,
            name="Medium Performer Villa",
            address="Chittagong",
            bedroom=3,
            bathroom=3,
            price_daily=250.00,
            verified=True
        )
        
        # Create bookings for p1 (top performer: 2 bookings)
        Booking.objects.create(
            property=p1,
            user=self.user,
            name="Guest 1",
            phone="12345",
            email="g1@example.com",
            guest_count=2,
            check_in=date.today() - timedelta(days=5),
            check_out=date.today() - timedelta(days=2),
            price=450.00,
            status="CONFIRMED"
        )
        Booking.objects.create(
            property=p1,
            user=self.user,
            name="Guest 2",
            phone="12345",
            email="g2@example.com",
            guest_count=1,
            check_in=date.today() - timedelta(days=1),
            check_out=date.today() + timedelta(days=2),
            price=450.00,
            status="CONFIRMED"
        )
        # Pending booking for p1
        Booking.objects.create(
            property=p1,
            user=self.user,
            name="Guest 3",
            phone="12345",
            email="g3@example.com",
            guest_count=1,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=7),
            price=300.00,
            status="PENDING"
        )

        # Create bookings for p2 (medium performer: 1 booking)
        Booking.objects.create(
            property=p2,
            user=self.user,
            name="Guest 4",
            phone="12345",
            email="g4@example.com",
            guest_count=2,
            check_in=date.today() - timedelta(days=10),
            check_out=date.today() - timedelta(days=7),
            price=750.00,
            status="CONFIRMED"
        )

        # Create reviews
        Review.objects.create(
            property=p1,
            user=self.user,
            rating=4.5,
            review="Excellent stay!"
        )
        Review.objects.create(
            property=p2,
            user=self.user,
            rating=4.0,
            review="Good stay!"
        )

        # Call owner property list
        response = self.client.get("/property/api/v1/owner/property/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify metrics
        self.assertIn("occupancy_rate", response.data)
        self.assertIn("total_bookings", response.data)
        self.assertIn("pending_requests", response.data)
        self.assertIn("avg_rating", response.data)
        
        # Occupancy rate calculation check:
        # Total properties = 2.
        # Capacity days = 2 * 30 = 60.
        # Booked days overlapping last 30 days:
        # Booking 1: check_in (today-5), check_out (today-2) -> 3 days
        # Booking 2: check_in (today-1), check_out (today+2) -> overlap start today-1, overlap end today -> 1 day
        # Booking 4: check_in (today-10), check_out (today-7) -> 3 days
        # Total overlapping booked days = 3 + 1 + 3 = 7 days.
        # Occupancy rate = (7 / 60) * 100 = 11.66% -> 12%
        self.assertEqual(response.data["occupancy_rate"], "12%")
        self.assertEqual(response.data["total_bookings"], 4) # 4 non-cancelled bookings
        self.assertEqual(response.data["pending_requests"], 1)
        self.assertEqual(response.data["avg_rating"], "4.2") # (4.5 + 4.0) / 2 = 4.25 -> 4.2 (round to even)

        # Verify sorted list: p1 (2 bookings) should be first, p2 (1 booking) should be second
        properties_list = response.data["properties"]
        self.assertEqual(len(properties_list), 2)
        self.assertEqual(properties_list[0]["name"], "Top Performer Condo")
        self.assertEqual(properties_list[1]["name"], "Medium Performer Villa")

        # Call retrieve endpoint for p1
        detail_url = f"/property/api/v1/owner/property/{p1.id}/"
        retrieve_response = self.client.get(detail_url)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve_response.data["occupancy"], "13%") # 4 booked days out of 30 for p1 = 13.33% -> 13%
        self.assertEqual(retrieve_response.data["occupancy_rate"], "13%")
        self.assertEqual(retrieve_response.data["total_bookings"], 3) # includes pending/confirmed (non-cancelled)
        self.assertEqual(retrieve_response.data["avg_stay"], "2.7 days") # (3 + 3 + 2) / 3 = 2.666 -> 2.7
        self.assertEqual(retrieve_response.data["avg_stay_duration"], "2.7 days")
        self.assertEqual(retrieve_response.data["avg_rating"], "4.5") # p1 has one review rated 4.5
        self.assertEqual(retrieve_response.data["total_views"], p1.views)
        self.assertIn("amenities", retrieve_response.data["property"])
        self.assertIn("activities", retrieve_response.data["property"])

    def test_guest_property_availability_filtering(self):
        from datetime import date, timedelta
        # Setup properties
        p1 = Property.objects.create(
            owner=self.user, name="Booked Property", address="Addr 1", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE", verified=True
        )
        p2 = Property.objects.create(
            owner=self.user, name="Available Property", address="Addr 2", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE", verified=True
        )

        # Book p1 from today to today + 3 days
        Booking.objects.create(
            property=p1,
            user=self.user,
            name="Booking for P1",
            phone="12345",
            email="p1@example.com",
            guest_count=2,
            check_in=date.today(),
            check_out=date.today() + timedelta(days=3),
            price=300.00,
            status="CONFIRMED"
        )

        # 1. Query for BOOKED properties in the date range
        url = f"/property/api/v1/guest/property/?start_date={date.today()}&end_date={date.today() + timedelta(days=3)}&status=BOOKED"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["data"]]
        self.assertIn("Booked Property", names)
        self.assertNotIn("Available Property", names)
        self.assertEqual(response.data["data"][0]["status"], "Booked")

        # 2. Query for AVAILABLE properties in the date range
        url = f"/property/api/v1/guest/property/?start_date={date.today()}&end_date={date.today() + timedelta(days=3)}&status=AVAILABLE"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data["data"]]
        self.assertNotIn("Booked Property", names)
        self.assertIn("Available Property", names)
        self.assertEqual(response.data["data"][0]["status"], "Available")
        self.assertIn("price_daily", response.data["data"][0])
        self.assertIn("price_monthly", response.data["data"][0])

    def test_guest_property_proximity_location_filtering(self):
        p_far = Property.objects.create(
            owner=self.user, name="Far Property", address="NYC", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE",
            latitude=45.0000, longitude=-75.0000, verified=True
        )
        p_close = Property.objects.create(
            owner=self.user, name="Close Property", address="Hoboken", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE",
            latitude=40.7200, longitude=-74.0100, verified=True
        )

        url = "/property/api/v1/guest/property/?latitude=40.7201&longitude=-74.0101"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data["data"]
        names = [item["name"] for item in results]
        idx_close = names.index("Close Property")
        idx_far = names.index("Far Property")
        self.assertTrue(idx_close < idx_far)
        self.assertIsNotNone(results[idx_close]["distance"])
        self.assertIsNotNone(results[idx_far]["distance"])
        
        url_radius = "/property/api/v1/guest/property/?latitude=40.7201&longitude=-74.0101&radius=5.0"
        response_radius = self.client.get(url_radius)
        self.assertEqual(response_radius.status_code, status.HTTP_200_OK)
        names_radius = [item["name"] for item in response_radius.data["data"]]
        self.assertIn("Close Property", names_radius)
        self.assertNotIn("Far Property", names_radius)

    def test_guest_property_home_dashboard_and_detail_fields(self):
        p_far = Property.objects.create(
            owner=self.user, name="NYC far Property", address="NYC", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE",
            latitude=45.0000, longitude=-75.0000, views=10, verified=True
        )
        p_close = Property.objects.create(
            owner=self.user, name="Hoboken close Property", address="Hoboken", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE",
            latitude=40.7200, longitude=-74.0100, views=2, verified=True
        )

        url = "/property/api/v1/guest/home/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("recommended", response.data["data"])
        self.assertIn("popular_nearby", response.data["data"])

        # Test filtering Home dashboard collectively with search
        url_search = "/property/api/v1/guest/home/?search=NYC"
        response_search = self.client.get(url_search)
        self.assertEqual(response_search.status_code, status.HTTP_200_OK)
        rec_search = response_search.data["data"]["recommended"]
        near_search = response_search.data["data"]["popular_nearby"]
        self.assertTrue(all("NYC" in item["name"] for item in rec_search))
        self.assertTrue(all("NYC" in item["name"] for item in near_search))

        url = "/property/api/v1/guest/home/?latitude=40.7201&longitude=-74.0101"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        nearby = response.data["data"]["popular_nearby"]
        self.assertEqual(nearby[0]["name"], "Hoboken close Property")
        self.assertEqual(nearby[1]["name"], "NYC far Property")
        self.assertIsNotNone(nearby[0]["distance"])

        # Create a mock review
        from apps.property.models import Review
        Review.objects.create(property=p_close, user=self.user, rating=5.0, review="Excellent stay!")

        detail_url = f"/property/api/v1/guest/property/{p_close.id}/?latitude=40.7201&longitude=-74.0101"
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(detail_response.data["id"]), str(p_close.id))
        self.assertIsNotNone(detail_response.data["distance"])
        # Check rating breakdown
        breakdown = detail_response.data["rating_breakdown"]
        self.assertEqual(breakdown["5"], 1)
        self.assertEqual(breakdown["4"], 0)

    def test_guest_property_see_all_listings(self):
        p_far = Property.objects.create(
            owner=self.user, name="NYC far Property", address="NYC", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE",
            latitude=45.0000, longitude=-75.0000, views=10, type="HOUSE", verified=True
        )
        p_close = Property.objects.create(
            owner=self.user, name="Hoboken close Property", address="Hoboken", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE",
            latitude=40.7200, longitude=-74.0100, views=2, type="VILLA", verified=True
        )

        url_rec = "/property/api/v1/guest/recommended/"
        response_rec = self.client.get(url_rec)
        self.assertEqual(response_rec.status_code, status.HTTP_200_OK)
        self.assertEqual(response_rec.data["data"][0]["name"], "NYC far Property")

        url_rec_filter = "/property/api/v1/guest/recommended/?type=VILLA"
        response_rec_filter = self.client.get(url_rec_filter)
        self.assertEqual(response_rec_filter.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_rec_filter.data["data"]), 1)
        self.assertEqual(response_rec_filter.data["data"][0]["name"], "Hoboken close Property")

        url_near = "/property/api/v1/guest/popular-nearby/?latitude=40.7201&longitude=-74.0101"
        response_near = self.client.get(url_near)
        self.assertEqual(response_near.status_code, status.HTTP_200_OK)
        self.assertEqual(response_near.data["data"][0]["name"], "Hoboken close Property")
        self.assertIsNotNone(response_near.data["data"][0]["distance"])

    def test_property_detail_view_gallery_and_reviews(self):
        prop = Property.objects.create(
            owner=self.user, name="Detail Test Property", address="Test Addr", bedroom=2, bathroom=2, price_daily=150.00, status="AVAILABLE", verified=True
        )
        
        from apps.property.models import Gallery, Review
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_file = SimpleUploadedFile("image.jpg", b"file_content", content_type="image/jpeg")
        Gallery.objects.create(property=prop, type="IMAGE", file=mock_file)

        r1 = Review.objects.create(property=prop, user=self.user, rating=5.0, review="Latest best review")
        r2 = Review.objects.create(property=prop, user=self.user, rating=4.0, review="Older good review")
        
        from datetime import timedelta
        from django.utils import timezone
        r2.created_at = timezone.now() - timedelta(days=5)
        r2.save()

        url = f"/property/api/v1/guest/property/{prop.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        gallery_data = response.data["gallery"]
        self.assertEqual(len(gallery_data), 1)
        self.assertEqual(gallery_data[0]["type"], "IMAGE")
        self.assertTrue("image" in gallery_data[0]["file"])

        reviews_data = response.data["reviews"]
        self.assertEqual(len(reviews_data), 2)
        self.assertEqual(reviews_data[0]["review"], "Latest best review")
        self.assertEqual(reviews_data[1]["review"], "Older good review")

    def test_get_favourite_status_by_property_id(self):
        prop = Property.objects.create(
            owner=self.user, name="Fav Check Property", address="Test Addr", bedroom=2, bathroom=2, price_daily=150.00, status="AVAILABLE", verified=True
        )
        url = f"/property/api/v1/guest/favourite/{prop.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["favourite"])

        from apps.property.models import Favourites
        Favourites.objects.create(user=self.user, property=prop)

        response_fav = self.client.get(url)
        self.assertEqual(response_fav.status_code, status.HTTP_200_OK)
        self.assertTrue(response_fav.data["favourite"])

    def test_top_performing_properties(self):
        p1 = Property.objects.create(
            owner=self.user, name="Low Performing", address="Addr", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE", views=5, verified=True
        )
        p2 = Property.objects.create(
            owner=self.user, name="High Performing", address="Addr", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE", views=100, verified=True
        )
        p3 = Property.objects.create(
            owner=self.user, name="Medium Performing", address="Addr", bedroom=1, bathroom=1, price_daily=100.00, status="AVAILABLE", views=50, verified=True
        )

        url = "/property/api/v1/guest/top-performing/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["count"], 3)
        self.assertIsNone(response.data["previous"])
        self.assertIsNone(response.data["next"])
        
        names = [item["name"] for item in response.data["data"]]
        self.assertEqual(names[0], "High Performing")
        self.assertEqual(names[1], "Medium Performing")
        self.assertEqual(names[2], "Low Performing")

        # Test page size pagination
        response_paged = self.client.get(f"{url}?page_size=2")
        self.assertEqual(response_paged.status_code, status.HTTP_200_OK)
        self.assertEqual(response_paged.data["count"], 3)
        self.assertIsNotNone(response_paged.data["next"])
        self.assertEqual(len(response_paged.data["data"]), 2)
        self.assertEqual(response_paged.data["data"][0]["name"], "High Performing")
        self.assertEqual(response_paged.data["data"][1]["name"], "Medium Performing")

    def test_visited_places_list(self):
        from apps.property.models import VisitedPlaces, PlaceImage
        place = VisitedPlaces.objects.create(
            name="Paris", address="France", latitude=48.8566, longitude=2.3522
        )
        PlaceImage.objects.create(place=place, image="place_images/paris.jpg")

        url = "/property/api/v1/guest/visited-places/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["name"], "Paris")
        self.assertEqual(len(response.data["data"][0]["images"]), 1)
        self.assertIn("/media/place_images/paris.jpg", response.data["data"][0]["images"][0]["image"])

    def test_property_currency_conversion_flow(self):
        from apps.others.models import UserPreference
        UserPreference.objects.create(user=self.user, currency=self.bdt)
        
        # 1. Create property in BDT
        # Price daily: 1170.00 BDT. Exchange rate of BDT is 117.0.
        # This should convert to 10.00 USD in the database.
        data = {
            "name": "BDT Property",
            "about": "BDT property description",
            "price_daily": 1170.00,
            "price_monthly": 117000.00,
            "currency_code": "BDT",
            "bathroom": 1,
            "bedroom": 1,
            "area": "500 sqft",
            "type": "HOUSE",
            "status": "AVAILABLE",
            "address": "Dhaka",
            "add_ons_prices": json.dumps([
                {"service": "Breakfast", "price": 117}
            ]),
            "weekend_dates": json.dumps({
                "weekend": ["FRI"],
                "price": 2340
            }),
            "other_charges": json.dumps([
                {"name": "VAT", "price": 58.50}
            ])
        }
        
        response = self.client.post("/property/api/v1/owner/create-property/", data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stored in database as USD:
        # price_daily: 1170 / 117 = 10 USD
        # price_monthly: 117000 / 117 = 1000 USD
        property_obj = Property.objects.get(name="BDT Property")
        self.assertEqual(float(property_obj.price_daily), 10.00)
        self.assertEqual(float(property_obj.price_monthly), 1000.00)
        
        # Check add_ons_prices service Breakfast: 117 / 117 = 1 USD
        addon = property_obj.add_ons_prices.first()
        self.assertEqual(float(addon.price), 1.00)
        
        # Check weekend_dates price: 2340 / 117 = 20 USD
        self.assertEqual(float(property_obj.weekend_dates.price), 20.00)
        
        # Check other_charges VAT: 58.5 / 117 = 0.5 USD
        charge = property_obj.other_charges.first()
        self.assertEqual(float(charge.price), 0.50)
        
        # 2. Retrieve property: since user's preferred currency is BDT,
        # it should convert back to BDT when returned!
        url = f"/property/api/v1/guest/property/{property_obj.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Returned prices should be:
        # price_daily: 10 * 117 = 1170.0
        # price_monthly: 1000 * 117 = 117000.0
        # weekend_dates.price: 20 * 117 = 2340.0
        # add_ons_prices[0].price: 1 * 117 = 117.0
        # other_charges[0].price: 0.5 * 117 = 58.5
        self.assertEqual(response.data["price_daily"], 1170.00)
        self.assertEqual(response.data["price_monthly"], 117000.00)
        self.assertEqual(response.data["weekend_dates"]["price"], 2340.00)
        self.assertEqual(response.data["add_ons_prices"][0]["price"], 117.00)
        self.assertEqual(response.data["other_charges"][0]["price"], 58.50)



