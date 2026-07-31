from rest_framework import serializers
from apps.booking.models import Booking
from apps.property.serializers import PropertyListSerializer
from apps.auth.serializers import UserDataSerializer

class AddonIdsField(serializers.Field):
    def to_internal_value(self, data):
        from apps.booking.utils import parse_addon_ids
        parsed = parse_addon_ids(data)
        res = []
        for x in parsed:
            try:
                res.append(int(x))
            except (ValueError, TypeError):
                pass
        return res

    def get_value(self, dictionary):
        from rest_framework.fields import empty
        if self.field_name not in dictionary:
            return empty
        if hasattr(dictionary, 'getlist'):
            val = dictionary.getlist(self.field_name)
            if len(val) == 1:
                return val[0]
            return val
        return dictionary.get(self.field_name)


class CreateBookingSerializer(serializers.ModelSerializer):
    price_type = serializers.ChoiceField(choices=['daily', 'monthly'], default='daily', write_only=True)
    selected_addon_ids = AddonIdsField(required=False, write_only=True)
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
            'document_file', 'document_type', 'security_document'
        ]

    def validate(self, data):
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        prop = data.get('property')
        
        if check_in and check_out:
            if check_in >= check_out:
                raise serializers.ValidationError({"check_in": "Check-in date must be before check-out date."})
            
            # Check if there is an overlapping confirmed/checked-in booking for this property
            overlapping_exists = Booking.objects.filter(
                property=prop,
                status__in=['CONFIRMED', 'CHECKED_IN'],
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exists()
            
            if overlapping_exists:
                raise serializers.ValidationError({
                    "non_field_errors": "This property is already booked for the selected dates."
                })
        return data

    def create(self, validated_data):
        validated_data.pop('price_type', None)
        validated_data.pop('selected_addon_ids', None)
        validated_data.pop('document_file', None)
        validated_data.pop('document_type', None)
        return super().create(validated_data)

class BookingListSerializer(serializers.ModelSerializer):
    property = PropertyListSerializer()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'property', 'name', 'phone', 'email', 'guest_count', 
            'check_in', 'check_out', 'price', 'status', 'currency_code', 'currency_symbol',
            'security_document'
        ]

    def get_currency_code(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        return code

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
        if ret.get('price') is not None:
            ret['price'] = round(float(ret['price']) * rate, 2)
        return ret

class BookingDetailsSerializer(serializers.ModelSerializer):
    property = PropertyListSerializer()
    owner = UserDataSerializer(source='property.owner')
    documents = serializers.SerializerMethodField()
    booking_status_tracker = serializers.SerializerMethodField()
    security_approval_tracker = serializers.SerializerMethodField()
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()
    price_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'property', 'owner', 'name', 'phone', 'email', 'guest_count', 
            'check_in', 'check_out', 'price', 'status', 'created_at', 'updated_at',
            'documents', 'booking_status_tracker', 'security_approval_tracker',
            'currency_code', 'currency_symbol', 'security_document', 'price_breakdown'
        ]

    def get_price_breakdown(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        from apps.booking.utils import get_final_discount_price_for_booking
        
        code, symbol, rate = get_user_currency_and_rate(request)
        
        total_duration = 1
        if obj.check_in and obj.check_out:
            try:
                s_d, e_d = min(obj.check_in, obj.check_out), max(obj.check_in, obj.check_out)
                delta = (e_d - s_d).days
                if delta > 0:
                    total_duration = delta
            except Exception:
                pass

        breakdown = get_final_discount_price_for_booking(
            property_obj_or_id=obj.property,
            price_type="daily",
            selected_addon_ids=None,
            start_date=str(obj.check_in) if obj.check_in else None,
            end_date=str(obj.check_out) if obj.check_out else None
        )

        return {
            "total_duration": total_duration,
            "base_price_total": round(breakdown["base_price"] * total_duration * rate, 2),
            "other_charges": [
                {
                    "name": c["name"],
                    "amount": round(c["amount"] * rate, 2),
                    "total_amount": round(c["amount"] * total_duration * rate, 2)
                }
                for c in breakdown["other_charges"]
            ],
            "other_charges_total": round(breakdown["other_charges_total"] * total_duration * rate, 2),
            "add_ons": [
                {
                    "name": a["name"],
                    "amount": round(a["amount"] * rate, 2),
                    "total_amount": round(a["amount"] * total_duration * rate, 2)
                }
                for a in breakdown["add_ons"]
            ],
            "add_ons_total": round(breakdown["add_ons_total"] * total_duration * rate, 2),
            "vacation_surcharge_total": round(breakdown["vacation_surcharge"] * total_duration * rate, 2),
            "weekend_surcharge_total": round(breakdown["weekend_surcharge"] * total_duration * rate, 2),
            "rating_surcharge_total": round(breakdown.get("rating_surcharge", 0) * total_duration * rate, 2),
            "discount_total": round(breakdown["discount_amount"] * total_duration * rate, 2),
            "total_amount_before_discount": round(breakdown["total_before_discount"] * total_duration * rate, 2)
        }

    def get_currency_code(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        return code

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
        if ret.get('price') is not None:
            ret['price'] = round(float(ret['price']) * rate, 2)
        return ret

    def get_booking_status_tracker(self, obj):
        return {
            "request_submitted": True,
            "host_review": obj.status in ['PENDING', 'CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT'],
            "approved": obj.status in ['CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT']
        }

    def get_security_approval_tracker(self, obj):
        from apps.auth.models import Document
        has_docs = Document.objects.filter(user=obj.user).exists()
        has_verified_docs = Document.objects.filter(user=obj.user, is_verified=True).exists()
        return {
            "document_uploaded": has_docs,
            "security_review": has_docs,
            "clearance_granted": has_verified_docs
        }

    def get_documents(self, obj):
        from apps.auth.models import Document
        from apps.auth.serializers import UploadDocumentSerializer
        docs = Document.objects.filter(user=obj.user)
        return UploadDocumentSerializer(docs, many=True).data

class MyBookingListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    name = serializers.CharField(source='property.name', read_only=True)
    address = serializers.CharField(source='property.address', read_only=True)
    cover = serializers.SerializerMethodField()
    guest_name = serializers.CharField(source='name', read_only=True)
    guest_phone = serializers.CharField(source='phone', read_only=True)
    guest_email = serializers.CharField(source='email', read_only=True)
    user = UserDataSerializer(read_only=True)
    currency_code = serializers.SerializerMethodField()
    currency_symbol = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'status', 'name', 'property_name', 'address', 'cover',
            'guest_name', 'guest_phone', 'guest_email', 'check_in', 'check_out',
            'guest_count', 'price', 'user', 'currency_code', 'currency_symbol',
            'security_document'
        ]

    def get_currency_code(self, obj):
        request = self.context.get('request')
        from apps.others.utils import get_user_currency_and_rate
        code, symbol, rate = get_user_currency_and_rate(request)
        return code

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
        if ret.get('price') is not None:
            ret['price'] = round(float(ret['price']) * rate, 2)
        return ret
        
    def get_cover(self, obj):
        if obj.property and obj.property.cover_image:
            return obj.property.cover_image.url
        return ""
