from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthDRFTests(APITestCase):
    def test_duplicate_email_signup_error_format(self):
        # 1. Sign up the first user
        data = {
            "email": "testuser@example.com",
            "password": "password123",
            "phone": "01711111111",
            "name": "Test User",
            "role": "guest"
        }
        response = self.client.post("/auth/api/v1/signup/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])

        # 2. Try to sign up again with the same email
        response2 = self.client.post("/auth/api/v1/signup/", data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response2.data["success"])
        
        # Verify the errors field is formatted as a single string message
        self.assertEqual(response2.data["errors"], "User with this User Email already exists.")
