from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.currency_and_language.models import Language, Currency, UserPreference

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
        url = "/currency-and-language/api/v1/languages/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        codes = [item["code"] for item in response.data["data"]]
        self.assertIn("en", codes)
        self.assertIn("ar", codes)

    def test_currencies_list(self):
        url = "/currency-and-language/api/v1/currencies/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        codes = [item["code"] for item in response.data["data"]]
        self.assertIn("USD", codes)
        self.assertIn("AED", codes)
        self.assertIn("EGP", codes)

    def test_get_and_update_preferences(self):
        url = "/currency-and-language/api/v1/preferences/"
        
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
