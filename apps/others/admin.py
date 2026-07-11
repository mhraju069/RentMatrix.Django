from django.contrib import admin
from .models import Language, Currency, UserPreference
from unfold.admin import ModelAdmin

@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)

@admin.register(Currency)
class CurrencyAdmin(ModelAdmin):
    list_display = ('name', 'code', 'symbol', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)

@admin.register(UserPreference)
class UserPreferenceAdmin(ModelAdmin):
    list_display = ('user', 'language', 'currency')
    search_fields = ('user__email',)
