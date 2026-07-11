from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.others.models import Language, Currency, UserPreference

User = get_user_model()

class CurrencyAndLanguageTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="prefuser@example.com",
            password="password123",
            phone="01733333333",
            name="Preference User"
        )
        self.client.force_authenticate(user=self.user)

    def test_languages_list(self):
        url = "/others/api/v1/languages/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        codes = [item["code"] for item in response.data["data"]]
        self.assertIn("en", codes)
        self.assertIn("ar", codes)

    def test_currencies_list(self):
        url = "/others/api/v1/currencies/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        codes = [item["code"] for item in response.data["data"]]
        self.assertIn("USD", codes)
        self.assertIn("AED", codes)
        self.assertIn("EGP", codes)

    def test_get_and_update_preferences(self):
        url = "/others/api/v1/preferences/"
        
        # 1. GET preferences (should auto-create with default English and USD)
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        self.assertTrue(response_get.data["success"])
        self.assertEqual(response_get.data["data"]["language"]["code"], "en")
        self.assertEqual(response_get.data["data"]["currency"]["code"], "USD")

        # 2. Update preference using codes (e.g. Arabic & AED)
        data = {
            "language_code": "ar",
            "currency_code": "AED"
        }
        response_patch = self.client.patch(url, data, format="json")
        self.assertEqual(response_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(response_patch.data["data"]["language"]["code"], "ar")
        self.assertEqual(response_patch.data["data"]["currency"]["code"], "AED")

        # 3. Update using invalid code
        data_invalid = {
            "language_code": "invalid_code"
        }
        response_invalid = self.client.patch(url, data_invalid, format="json")
        self.assertEqual(response_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_response_translation_based_on_user_preference(self):
        # 1. User preferences originally set to English (default)
        url_lang = "/others/api/v1/languages/"
        response_en = self.client.get(url_lang)
        self.assertEqual(response_en.status_code, status.HTTP_200_OK)
        self.assertEqual(response_en.data["message"], "Languages fetched successfully")

        # 2. Update language preference to Arabic
        url_pref = "/others/api/v1/preferences/"
        lang_ar = Language.objects.get(code="ar")
        pref, _ = UserPreference.objects.get_or_create(user=self.user)
        pref.language = lang_ar
        pref.save()

        # 3. Call same endpoint again - message should be translated to Arabic
        response_ar = self.client.get(url_lang)
        self.assertEqual(response_ar.status_code, status.HTTP_200_OK)
        self.assertEqual(response_ar.data["message"], "تم جلب اللغات بنجاح")

    def test_response_translation_based_on_accept_language_header(self):
        self.client.logout()  # Unauthenticated request
        url_lang = "/others/api/v1/languages/"
        
        # Request with Arabic Accept-Language header
        response = self.client.get(url_lang, HTTP_ACCEPT_LANGUAGE="ar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "تم جلب اللغات بنجاح")

        # Request with English Accept-Language header
        response_en = self.client.get(url_lang, HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response_en.status_code, status.HTTP_200_OK)
        self.assertEqual(response_en.data["message"], "Languages fetched successfully")

    def test_property_price_conversion_according_to_currency_preference(self):
        from apps.property.models import Property
        prop = Property.objects.create(
            owner=self.user, name="Currency Test Prop", address="123 Test St", 
            bedroom=2, bathroom=2, price_daily=100.00, price_monthly=2500.00, status="AVAILABLE"
        )
        
        aed_curr = Currency.objects.get(code="AED")
        aed_curr.exchange_rate = 3.67
        aed_curr.save()

        url = f"/property/api/v1/guest/property/{prop.id}/"
        response_usd = self.client.get(url)
        self.assertEqual(response_usd.status_code, status.HTTP_200_OK)
        self.assertEqual(response_usd.data["price_daily"], 100.00)
        self.assertEqual(response_usd.data["price_monthly"], 2500.00)
        self.assertEqual(response_usd.data["currency_code"], "USD")
        self.assertEqual(response_usd.data["currency_symbol"], "$")

        pref, _ = UserPreference.objects.get_or_create(user=self.user)
        pref.currency = aed_curr
        pref.save()

        response_aed = self.client.get(url)
        self.assertEqual(response_aed.status_code, status.HTTP_200_OK)
        self.assertEqual(response_aed.data["price_daily"], 367.00)
        self.assertEqual(response_aed.data["price_monthly"], 9175.00)
        self.assertEqual(response_aed.data["currency_code"], "AED")
        self.assertEqual(response_aed.data["currency_symbol"], "د.إ")
