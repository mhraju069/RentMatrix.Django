from rest_framework import serializers
from .models import User, OTP, Document
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

class UserDataSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['email', 'role', 'name', 'phone', 'image']

    @extend_schema_field(OpenApiTypes.STR)
    def get_image(self, obj):
        if obj.image:
            return f"{settings.BACKEND_URI}{obj.image.url}"
        return None

class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'phone', 'name', 'role']
        extra_kwargs = {
            'password': {'write_only': True}
        }

class LoginUserSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_null=True)

class GetOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=10)

class UpdateUserSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    old_password = serializers.CharField(required=False, write_only=True)
    new_password = serializers.CharField(required=False, write_only=True)
    image = serializers.ImageField(required=False)

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)

class UploadDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['document_type', 'document_file']
