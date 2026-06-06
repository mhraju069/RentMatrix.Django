from unfold.admin import ModelAdmin
from django.contrib import admin
from unfold.widgets import UnfoldAdminSelectWidget
from .models import *


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = ("email", "name", "role", "is_active", "is_superuser", "created_at")
    list_filter = ("role", "is_active", "is_superuser")
    search_fields = ("name", "email", "phone")
    ordering = ("-created_at",)
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Identity", {
            "fields": ("name", "email", "phone", "image", "role")
        }),
        ("Access", {
            "fields": ("password", "is_active", "is_staff", "is_superuser")
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",), "fields": ("name", "email", "password", "phone")
        }),
    )