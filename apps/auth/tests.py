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

    def test_multiple_document_upload(self):
        user = User.objects.create_user(
            email="uploader@example.com",
            password="password123",
            phone="01722222222",
            name="Uploader User",
            role="guest"
        )
        self.client.force_authenticate(user=user)

        from django.core.files.uploadedfile import SimpleUploadedFile
        file1 = SimpleUploadedFile("passport.png", b"file_content_1", content_type="image/png")
        file2 = SimpleUploadedFile("nid.png", b"file_content_2", content_type="image/png")

        data = {
            "document_type": ["Passport", "NID"],
            "document_file": [file1, file2]
        }

        url = "/auth/api/v1/upload-document/"
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Successfully uploaded 2 document(s).")

        from apps.auth.models import Document
        docs = Document.objects.filter(user=user)
        self.assertEqual(docs.count(), 2)
        types = [doc.document_type for doc in docs]
        self.assertIn("Passport", types)
        self.assertIn("NID", types)
