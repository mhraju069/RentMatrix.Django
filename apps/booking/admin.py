from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = ('property', 'user', 'name', 'phone', 'guest_count', 'check_in', 'check_out', 'price', 'status')
    list_filter = ('status', 'check_in', 'check_out')
    search_fields = ('name', 'email', 'phone', 'property__name')
    readonly_fields = ('created_at', 'updated_at')
