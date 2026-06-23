from apps.property.models import *
from rest_framework import serializers


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ["id", "name"]


class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ["id","type", "file"]


class AdvantagePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvantgePrice
        fields = ["id","service", "price"]


class AddOnsPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOnsPrice
        fields = ["id","service", "price"]


class SeasonalPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeasonalPrice
        fields = ["id","start", "end", "price"]


class PropertySerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, required=False)
    gallery = GallerySerializer(many=True, required=False)
    advantage_prices = AdvantagePriceSerializer(many=True, required=False)
    add_ons_prices = AddOnsPriceSerializer(many=True, required=False)
    season_prices = SeasonalPriceSerializer(many=True, required=False)
    cover = serializers.ImageField(source='cover_image', required=False, allow_null=True)

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
            "hosted_by",
            "whatsapp",
            "views",
            "sea_view",
            "type",
            "amenities",
            "gallery",
            "advantage_prices",
            "add_ons_prices",
            "season_prices",
        ]
    
    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        gallery = validated_data.pop("gallery", [])
        advantage_prices = validated_data.pop("advantage_prices", [])
        add_ons_prices = validated_data.pop("add_ons_prices", [])
        season_prices = validated_data.pop("season_prices", [])

        property = Property.objects.create(**validated_data)    

        for amenity in amenities:
            Amenity.objects.create(property=property, **amenity)
        
        for g in gallery:
            Gallery.objects.create(property=property, **g)

        for adv in advantage_prices:
            AdvantgePrice.objects.create(property=property, **adv)

        for add_on in add_ons_prices:
            AddOnsPrice.objects.create(property=property, **add_on)

        for season in season_prices:
            SeasonalPrice.objects.create(property=property, **season)
        
        return property

    def update(self, instance, validated_data):
        amenities = validated_data.pop("amenities", None)
        gallery = validated_data.pop("gallery", None)
        advantage_prices = validated_data.pop("advantage_prices", None)
        add_ons_prices = validated_data.pop("add_ons_prices", None)
        season_prices = validated_data.pop("season_prices", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if amenities is not None:
            instance.amenities.all().delete()
            for amenity in amenities:
                Amenity.objects.create(property=instance, **amenity)

        if gallery is not None:
            instance.galleries.all().delete()
            for g in gallery:
                Gallery.objects.create(property=instance, **g)

        if advantage_prices is not None:
            instance.advantge_prices.all().delete()
            for adv in advantage_prices:
                AdvantgePrice.objects.create(property=instance, **adv)

        if add_ons_prices is not None:
            instance.add_ons_prices.all().delete()
            for add_on in add_ons_prices:
                AddOnsPrice.objects.create(property=instance, **add_on)

        if season_prices is not None:
            instance.season_prices.all().delete()
            for season in season_prices:
                SeasonalPrice.objects.create(property=instance, **season)

        return instance
        
        

    