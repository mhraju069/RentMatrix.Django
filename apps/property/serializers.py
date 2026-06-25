from rest_framework import serializers
from apps.property.models import *
from apps.auth.models import User
from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

class PropertyOwnerSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['name', 'email', 'image']

    def get_image(self, obj):
        if obj.image:
            return f"{settings.BACKEND_URI}{obj.image.url}"
        return None

class ReviewSerializer(serializers.ModelSerializer):
    user = PropertyOwnerSerializer()
    
    class Meta:
        model = Review
        fields = ['rating', 'review', 'user', 'created_at']

class PropertyListSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    favourite = serializers.SerializerMethodField()
    price = serializers.FloatField(source='price_daily', required=False) # Maps to old price logic
    size = serializers.CharField(source='area')

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'price', 'bathroom', 'bedroom', 'size', 
            'type', 'sea_view', 'cover', 'average_rating', 'address', 
            'views', 'favourite', 'discount'
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_cover(self, obj):
        if obj.cover_image:
            return f"{settings.BACKEND_URI}{obj.cover_image.url}"
        return ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_average_rating(self, obj):
        return getattr(obj, 'avg_rating', "0.0")

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_favourite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favourites.objects.filter(user=request.user, property=obj).exists()
        return False



class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ["id","type", "file"]



class AddOnsPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOnsPrice
        fields = ["id","service", "price"]

class WeekendSerializer(serializers.ModelSerializer):
    weekend = serializers.JSONField(required=False)
    class Meta:
        model = Weekend
        fields = ["id", "weekend", "price"]

class VacetionsSerializer(serializers.ModelSerializer):
    month = serializers.JSONField(required=False)
    class Meta:
        model = Vacetions
        fields = ["id", "month", "price"]

class OtherChargesSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherCharges
        fields = ["id", "name", "price"]

class PropertyDetailSerializer(serializers.ModelSerializer):
    owner = PropertyOwnerSerializer()
    gallery = GallerySerializer(many=True, read_only=True)
    add_ons_prices = AddOnsPriceSerializer(many=True, read_only=True)
    weekend_dates = WeekendSerializer(read_only=True)
    vacations = VacetionsSerializer(read_only=True)
    other_charges = OtherChargesSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    favourite = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    price = serializers.FloatField(source='price_daily', required=False)
    size = serializers.CharField(source='area')

    class Meta:
        model = Property
        fields = [
            'name', 'about', 'price', 'owner', 'bathroom', 'bedroom', 'size',
            'type', 'status', 'verified', 'sea_view', 'review_count', 'cover',
            'average_rating', 'address', 'latitude', 'longitude',
            'weekend_dates', 'vacations', 'other_charges',
            'gallery', 'add_ons_prices', 'reviews', 'views', 'favourite', 'discount'
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_cover(self, obj):
        if obj.cover_image:
            return f"{settings.BACKEND_URI}{obj.cover_image.url}"
        return ""

    def get_reviews(self, obj):
        reviews = obj.reviews.select_related('user').all()
        return ReviewSerializer(reviews, many=True).data

    @extend_schema_field(OpenApiTypes.STR)
    def get_review_count(self, obj):
        return str(obj.reviews.count())

    @extend_schema_field(OpenApiTypes.STR)
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        count = reviews.count()
        if count > 0:
            avg = sum(r.rating for r in reviews) / count
            return f"{avg:.1f}"
        return "0.0"

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_favourite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favourites.objects.filter(user=request.user, property=obj).exists()
        return False


class PropertySerializer(serializers.ModelSerializer):
    gallery = GallerySerializer(many=True, required=False)
    add_ons_prices = AddOnsPriceSerializer(many=True, required=False)
    weekend_dates = WeekendSerializer(required=False)
    vacations = VacetionsSerializer(required=False)
    other_charges = OtherChargesSerializer(many=True, required=False)
    cover = serializers.ImageField(source='cover_image', required=False, allow_null=True)
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Property
        fields = [
            "id",
            "owner",
            "name",
            "about",
            "address",
            "bathroom",
            "bedroom",
            "area",
            "cover",
            "latitude",
            "longitude",
            "price_daily",
            "price_monthly",
            "discount",
            "hosted_by",
            "whatsapp",
            "views",
            "sea_view",
            "type",
            "weekend_dates",
            "vacations",
            "other_charges",
            "gallery",
            "add_ons_prices",
        ]
        read_only_fields = ["owner","created_at","updated_at"]
    
    def create(self, validated_data):
        gallery = validated_data.pop("gallery", [])
        add_ons_prices = validated_data.pop("add_ons_prices", [])
        weekend_dates = validated_data.pop("weekend_dates", None)
        vacations = validated_data.pop("vacations", None)
        other_charges = validated_data.pop("other_charges", [])

        property = Property.objects.create(**validated_data)    
        
        for g in gallery:
            Gallery.objects.create(property=property, **g)

        for add_on in add_ons_prices:
            AddOnsPrice.objects.create(property=property, **add_on)

        if weekend_dates:
            Weekend.objects.create(property=property, **weekend_dates)

        if vacations:
            Vacetions.objects.create(property=property, **vacations)

        for charge in other_charges:
            OtherCharges.objects.create(property=property, **charge)
        
        return property

    def update(self, instance, validated_data):
        gallery = validated_data.pop("gallery", None)
        add_ons_prices = validated_data.pop("add_ons_prices", None)
        weekend_dates = validated_data.pop("weekend_dates", None)
        vacations = validated_data.pop("vacations", None)
        other_charges = validated_data.pop("other_charges", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if gallery is not None:
            instance.galleries.all().delete()
            for g in gallery:
                Gallery.objects.create(property=instance, **g)

        if add_ons_prices is not None:
            instance.add_ons_prices.all().delete()
            for add_on in add_ons_prices:
                AddOnsPrice.objects.create(property=instance, **add_on)

        if weekend_dates is not None:
            if hasattr(instance, 'weekend_dates'):
                instance.weekend_dates.delete()
            if isinstance(weekend_dates, dict) and weekend_dates:
                Weekend.objects.create(property=instance, **weekend_dates)

        if vacations is not None:
            if hasattr(instance, 'vacations'):
                instance.vacations.delete()
            if isinstance(vacations, dict) and vacations:
                Vacetions.objects.create(property=instance, **vacations)

        if other_charges is not None:
            instance.other_charges.all().delete()
            for charge in other_charges:
                OtherCharges.objects.create(property=instance, **charge)

        return instance
        
        

    