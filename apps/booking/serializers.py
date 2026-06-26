from rest_framework import serializers
from apps.booking.models import Booking
from apps.property.serializers import PropertyListSerializer
from apps.auth.serializers import UserDataSerializer

class CreateBookingSerializer(serializers.ModelSerializer):
    price_type = serializers.ChoiceField(choices=['daily', 'monthly'], default='daily', write_only=True)
    selected_addon_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )
    document_file = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True
    )
    document_type = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Booking
        fields = [
            'property', 'name', 'phone', 'email', 'check_in', 'check_out', 
            'guest_count', 'price_type', 'selected_addon_ids',
            'document_file', 'document_type'
        ]

    def validate(self, data):
        # Could add validation for check_in < check_out, property availability, etc.
        return data

    def create(self, validated_data):
        validated_data.pop('price_type', None)
        validated_data.pop('selected_addon_ids', None)
        validated_data.pop('document_file', None)
        validated_data.pop('document_type', None)
        return super().create(validated_data)

class BookingListSerializer(serializers.ModelSerializer):
    property = PropertyListSerializer()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'property', 'name', 'phone', 'email', 'guest_count', 
            'check_in', 'check_out', 'price', 'status'
        ]

class BookingDetailsSerializer(serializers.ModelSerializer):
    property = PropertyListSerializer()
    owner = UserDataSerializer(source='property.owner')

    class Meta:
        model = Booking
        fields = [
            'id', 'property', 'owner', 'name', 'phone', 'email', 'guest_count', 
            'check_in', 'check_out', 'price', 'status', 'created_at', 'updated_at'
        ]

class MyBookingListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='property.name')
    address = serializers.CharField(source='property.address')
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['id', 'status', 'name', 'address', 'cover']
        
    def get_cover(self, obj):
        from django.conf import settings
        if obj.property and obj.property.cover_image:
            return f"{settings.BACKEND_URI}{obj.property.cover_image.url}"
        return ""
