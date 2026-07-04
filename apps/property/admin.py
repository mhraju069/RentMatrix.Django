from .models import *
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline


@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    list_display = ('name', 'address', 'bedroom', 'bathroom', 'area', 'price_daily', 'price_monthly', 'type', 'status', 'verified')
    list_filter = ('type', 'status', 'verified')
    search_fields = ('name', 'address', 'about')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Gallery)
class GalleryAdmin(ModelAdmin):
    list_display = ('type', 'property', 'file')
    list_filter = ('type', 'property')
    search_fields = ('property',)


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('user', 'property', 'rating', 'review')
    list_filter = ('user', 'property')
    search_fields = ('user', 'property', 'review')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')



admin.site.register(AddOnsPrice,ModelAdmin)
admin.site.register(Weekend,ModelAdmin)
admin.site.register(Vacetions,ModelAdmin)
admin.site.register(OtherCharges,ModelAdmin)
admin.site.register(Activity,ModelAdmin)
admin.site.register(Amenity,ModelAdmin)

@admin.register(Reports)
class ReportsAdmin(ModelAdmin):
    list_display = ('user', 'property', 'reason', 'description', 'response', 'is_resolved', 'resolve_date', 'created_at')
    list_filter = ('user', 'property', 'is_resolved', 'resolve_date')
    search_fields = ('user', 'property', 'reason', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')



class PlaceImageInline(TabularInline):
    model = PlaceImage
    extra = 1


@admin.register(VisitedPlaces)
class VisitedPlacesAdmin(ModelAdmin):
    list_display = ('name', 'address', 'latitude', 'longitude')
    search_fields = ('name', 'address')
    inlines = [PlaceImageInline]


@admin.register(PlaceImage)
class PlaceImageAdmin(ModelAdmin):
    list_display = ('place', 'image')
    list_filter = ('place',)
    search_fields = ('place__name',)