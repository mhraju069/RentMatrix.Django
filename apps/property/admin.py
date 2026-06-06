from .models import *
from django.contrib import admin
from unfold.admin import ModelAdmin


@admin.register(Property)
class PropertyAdmin(ModelAdmin):
    list_display = ('name', 'address', 'bedroom', 'bathroom', 'area', 'price', 'type', 'status', 'verified')
    list_filter = ('type', 'status', 'verified')
    search_fields = ('name', 'address', 'about')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Amenity)
class AmenityAdmin(ModelAdmin):
    list_display = ('name', 'property')
    list_filter = ('property',)
    search_fields = ('name',)

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