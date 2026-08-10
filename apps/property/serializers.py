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
            return obj.image.url
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
    price_daily = serializers.FloatField(required=False)
    price_monthly = serializers.FloatField(required=False)
    size = serializers.CharField(source='area')
    status = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'price', 'price_daily', 'price_monthly', 'bathroom', 'bedroom', 'size', 
            'type', 'status', 'sea_view', 'cover', 'average_rating', 'address', 
            'views', 'favourite', 'discount', 'distance', 'currency_code', 'currency_symbol'
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_currency_code(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        return code

    @extend_schema_field(OpenApiTypes.STR)
    def get_currency_symbol(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        return symbol

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        
        # Convert prices
        if ret.get('price') is not None:
            ret['price'] = round(float(ret['price']) * rate, 2)
        if ret.get('price_daily') is not None:
            ret['price_daily'] = round(float(ret['price_daily']) * rate, 2)
        if ret.get('price_monthly') is not None:
            ret['price_monthly'] = round(float(ret['price_monthly']) * rate, 2)
            
        return ret

    @extend_schema_field(OpenApiTypes.STR)
    def get_cover(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
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

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, obj):
        request = self.context.get('request')
        if request:
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            if start_date and end_date:
                from datetime import datetime
                try:
                    start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
                    from apps.booking.models import Booking
                    is_booked = Booking.objects.filter(
                        property=obj,
                        status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN'],
                        check_in__lt=end_d,
                        check_out__gt=start_d
                    ).exists()
                    if is_booked:
                        return "Booked"
                except Exception:
                    pass
        val = getattr(obj, 'status', 'AVAILABLE') or 'AVAILABLE'
        return val.capitalize()

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance(self, obj):
        view = self.context.get('view')
        if view and hasattr(view, 'distances'):
            return view.distances.get(obj.id)
        return getattr(obj, 'distance', None)



class GallerySerializer(serializers.ModelSerializer):
    file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Gallery
        fields = ["id", "type", "file"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.file:
            url = instance.file.url
            request = self.context.get('request')
            if request:
                ret['file'] = request.build_absolute_uri(url)
            elif hasattr(settings, 'BACKEND_URI') and settings.BACKEND_URI:
                ret['file'] = settings.BACKEND_URI + url
            else:
                ret['file'] = url
        else:
            ret['file'] = ""
        return ret



class AddOnsPriceSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=16, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = AddOnsPrice
        fields = ["id", "service", "price"]

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ["id", "name"]

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "name", "details"]

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
    gallery = GallerySerializer(source='galleries', many=True, read_only=True)
    add_ons_prices = AddOnsPriceSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    activities = ActivitySerializer(many=True, read_only=True)
    weekend_dates = WeekendSerializer(read_only=True)
    vacations = VacetionsSerializer(read_only=True)
    other_charges = OtherChargesSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    favourite = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    price_daily = serializers.FloatField(required=False)
    price_monthly = serializers.FloatField(required=False)
    size = serializers.CharField(source='area')
    distance = serializers.SerializerMethodField()
    rating_breakdown = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    booked_ranges = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'about', 'price_daily', 'price_monthly', 'owner', 'bathroom', 'bedroom', 'size','hosted_by','whatsapp',
            'type', 'status', 'verified', 'sea_view', 'review_count', 'cover',
            'average_rating', 'address', 'latitude', 'longitude', 'distance', 'rating_breakdown',
            'weekend_dates', 'vacations', 'other_charges',
            'gallery', 'add_ons_prices', 'amenities', 'activities', 'reviews', 'views', 'favourite', 'discount',
            'currency_code', 'currency_symbol', 'booked_ranges',
            'rating_threshold', 'rating_surcharge_percent'
        ]

    def get_booked_ranges(self, obj):
        from apps.booking.models import Booking
        from django.utils import timezone
        today = timezone.now().date()
        bookings = Booking.objects.filter(
            property=obj,
            status__in=['CONFIRMED', 'CHECKED_IN'],
            check_out__gte=today
        ).values('check_in', 'check_out')
        return [
            {
                "check_in": b['check_in'].strftime('%Y-%m-%d'),
                "check_out": b['check_out'].strftime('%Y-%m-%d')
            }
            for b in bookings
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_currency_code(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        return code

    @extend_schema_field(OpenApiTypes.STR)
    def get_currency_symbol(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        return symbol

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        
        # Convert base prices
        if ret.get('price_daily') is not None:
            ret['price_daily'] = round(float(ret['price_daily']) * rate, 2)
        if ret.get('price_monthly') is not None:
            ret['price_monthly'] = round(float(ret['price_monthly']) * rate, 2)
            
        # Convert weekend_dates price
        if ret.get('weekend_dates') and 'price' in ret['weekend_dates'] and ret['weekend_dates']['price'] is not None:
            ret['weekend_dates']['price'] = round(float(ret['weekend_dates']['price']), 2)
            
        # Convert vacations price
        if ret.get('vacations') and 'price' in ret['vacations'] and ret['vacations']['price'] is not None:
            ret['vacations']['price'] = round(float(ret['vacations']['price']), 2)
            
        # Convert other_charges prices
        if ret.get('other_charges'):
            for charge in ret['other_charges']:
                if charge.get('price') is not None:
                    charge['price'] = round(float(charge['price']), 2)

        # Convert add_ons_prices prices
        if ret.get('add_ons_prices'):
            for addon in ret['add_ons_prices']:
                if addon.get('price') is not None:
                    addon['price'] = round(float(addon['price']) * rate, 2)
                    
        return ret

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance(self, obj):
        view = self.context.get('view')
        if view and hasattr(view, 'distances'):
            return view.distances.get(obj.id)
        return getattr(obj, 'distance', None)

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_rating_breakdown(self, obj):
        breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        ratings = obj.reviews.values_list('rating', flat=True)
        for r in ratings:
            try:
                r_int = int(round(float(r)))
                if r_int in breakdown:
                    breakdown[r_int] += 1
            except (ValueError, TypeError):
                pass
        return {str(k): v for k, v in breakdown.items()}

    @extend_schema_field(OpenApiTypes.STR)
    def get_cover(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
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
    gallery = GallerySerializer(source='galleries', many=True, required=False)
    add_ons_prices = AddOnsPriceSerializer(many=True, required=False)
    amenities = AmenitySerializer(many=True, required=False)
    activities = ActivitySerializer(many=True, required=False)
    weekend_dates = WeekendSerializer(required=False)
    vacations = VacetionsSerializer(required=False)
    other_charges = OtherChargesSerializer(many=True, required=False)
    cover = serializers.ImageField(source='cover_image', required=False, allow_null=True)
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    currency_code = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    currency_symbol = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)

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
            "amenities",
            "activities",
            "currency_code",
            "currency_symbol",
            "rating_threshold",
            "rating_surcharge_percent",
        ]
        read_only_fields = ["owner","created_at","updated_at"]

    def validate(self, attrs):
        request = self.context.get('request')
        
        # Check if we are creating, or updating any price-related fields
        price_fields = ['price_daily', 'price_monthly', 'weekend_dates', 'vacations', 'other_charges', 'add_ons_prices']
        has_prices = any(field in attrs for field in price_fields)
        is_create = self.instance is None

        currency_code = attrs.get('currency_code')
        currency_symbol = attrs.get('currency_symbol')

        if is_create or has_prices:
            from apps.others.models import Currency, UserPreference
            
            if not currency_code and not currency_symbol:
                raise serializers.ValidationError({
                    "currency_code": "Currency code or currency symbol is mandatory when setting prices."
                })

            currency = None
            if currency_code:
                currency = Currency.objects.filter(code=currency_code.upper()).first()
            
            if not currency and currency_symbol:
                currencies = Currency.objects.filter(symbol=currency_symbol)
                if currencies.exists():
                    user_currency_code = None
                    if request and request.user and request.user.is_authenticated:
                        try:
                            pref = UserPreference.objects.select_related('currency').get(user=request.user)
                            if pref.currency:
                                user_currency_code = pref.currency.code
                        except Exception:
                            pass
                    
                    if user_currency_code:
                        currency = currencies.filter(code=user_currency_code).first()
                    if not currency:
                        currency = currencies.first()

            if not currency:
                raise serializers.ValidationError({
                    "currency_code": f"Unsupported or invalid currency: {currency_code or currency_symbol}"
                })

            rate = currency.exchange_rate
            
            def to_usd(val):
                if val is None:
                    return None
                from decimal import Decimal
                try:
                    # Store exact value without rounding to preserve precision
                    # Rounding will happen only when displaying to users
                    return Decimal(str(val)) / rate
                except Exception:
                    return val

            if 'price_daily' in attrs and attrs['price_daily'] is not None:
                attrs['price_daily'] = to_usd(attrs['price_daily'])
            
            if 'price_monthly' in attrs and attrs['price_monthly'] is not None:
                attrs['price_monthly'] = to_usd(attrs['price_monthly'])

            # NOTE: weekend_dates.price, vacations.price, other_charges.price are PERCENTAGES (e.g. 10 = 10%)
            # They must NOT go through to_usd() — percentages have no currency unit.
            # Only price_daily, price_monthly, add_ons_prices are actual amounts.


            if 'add_ons_prices' in attrs and attrs['add_ons_prices'] is not None:
                for addon in attrs['add_ons_prices']:
                    if 'price' in addon and addon['price'] is not None:
                        addon['price'] = to_usd(addon['price'])

        return super().validate(attrs)
    
    def create(self, validated_data):
        validated_data.pop("currency_code", None)
        validated_data.pop("currency_symbol", None)
        gallery = validated_data.pop("galleries", [])
        add_ons_prices = validated_data.pop("add_ons_prices", [])
        amenities = validated_data.pop("amenities", [])
        activities = validated_data.pop("activities", [])
        weekend_dates = validated_data.pop("weekend_dates", None)
        vacations = validated_data.pop("vacations", None)
        other_charges = validated_data.pop("other_charges", [])

        property = Property.objects.create(**validated_data)    
        
        for g in gallery:
            Gallery.objects.create(property=property, **g)

        for add_on in add_ons_prices:
            AddOnsPrice.objects.create(property=property, **add_on)

        for amenity in amenities:
            Amenity.objects.create(property=property, **amenity)

        for activity in activities:
            Activity.objects.create(property=property, **activity)

        if weekend_dates:
            Weekend.objects.create(property=property, **weekend_dates)

        if vacations:
            Vacetions.objects.create(property=property, **vacations)

        for charge in other_charges:
            OtherCharges.objects.create(property=property, **charge)
        
        return property

    def update(self, instance, validated_data):
        validated_data.pop("currency_code", None)
        validated_data.pop("currency_symbol", None)
        gallery = validated_data.pop("galleries", None)
        add_ons_prices = validated_data.pop("add_ons_prices", None)
        amenities = validated_data.pop("amenities", None)
        activities = validated_data.pop("activities", None)
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

        if amenities is not None:
            instance.amenities.all().delete()
            for amenity in amenities:
                Amenity.objects.create(property=instance, **amenity)

        if activities is not None:
            instance.activities.all().delete()
            for activity in activities:
                Activity.objects.create(property=instance, **activity)

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



class ReportsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reports
        fields = ["id", "property", "user", "reason", "description", "response", "is_resolved", "resolve_date", "created_at"]
        read_only_fields = ["id", "created_at", "is_resolved", "resolve_date", "response", "user"]
    
        

    
class VisitedPlacesSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    class Meta:
        model = VisitedPlaces
        fields = ["id", "name", "address", "latitude", "longitude", "images"]

    def get_images(self, obj):
        res = []
        for i in obj.images.all():
            if i.image:
                res.append({"image": settings.BACKEND_URI + i.image.url})
        return res
    