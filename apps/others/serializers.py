from rest_framework import serializers
from apps.others.models import Language, Currency, UserPreference
from apps.property.models import Review

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name', 'code', 'is_active']

class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'name', 'code', 'symbol', 'is_active']

class UserPreferenceSerializer(serializers.ModelSerializer):
    language = LanguageSerializer(read_only=True)
    currency = CurrencySerializer(read_only=True)
    
    language_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    currency_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    language_code = serializers.CharField(write_only=True, required=False, allow_null=True)
    currency_code = serializers.CharField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = UserPreference
        fields = ['language', 'currency', 'language_id', 'currency_id', 'language_code', 'currency_code']

    def update(self, instance, validated_data):
        lang_id = validated_data.get('language_id')
        lang_code = validated_data.get('language_code')
        if lang_id is not None:
            if lang_id is None:
                instance.language = None
            else:
                try:
                    instance.language = Language.objects.get(id=lang_id)
                except Language.DoesNotExist:
                    raise serializers.ValidationError({"language_id": "Language not found."})
        elif lang_code is not None:
            if lang_code == "":
                instance.language = None
            else:
                try:
                    instance.language = Language.objects.get(code=lang_code)
                except Language.DoesNotExist:
                    raise serializers.ValidationError({"language_code": f"Language '{lang_code}' not found."})

        curr_id = validated_data.get('currency_id')
        curr_code = validated_data.get('currency_code')
        if curr_id is not None:
            if curr_id is None:
                instance.currency = None
            else:
                try:
                    instance.currency = Currency.objects.get(id=curr_id)
                except Currency.DoesNotExist:
                    raise serializers.ValidationError({"currency_id": "Currency not found."})
        elif curr_code is not None:
            if curr_code == "":
                instance.currency = None
            else:
                try:
                    instance.currency = Currency.objects.get(code=curr_code)
                except Currency.DoesNotExist:
                    raise serializers.ValidationError({"currency_code": f"Currency '{curr_code}' not found."})

        instance.save()
        return instance

class ReviewSerializer(serializers.ModelSerializer):    
    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ['id', 'created_at', 'updated_at', 'property', 'user']

    