from django.contrib import admin
from .models import Language, Currency, UserPreference

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'symbol', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'currency')
    search_fields = ('user__email',)
