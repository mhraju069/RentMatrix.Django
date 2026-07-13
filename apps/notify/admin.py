from django.contrib import admin
from .models import *
from unfold.admin import ModelAdmin

# Register your models here.


admin.site.register(DeviceToken, ModelAdmin)
admin.site.register(Notification, ModelAdmin)
@admin.register(Announcement)
class AnnouncementAdmin(ModelAdmin):
    list_display = ('title', 'user_group', 'sent', 'created_at')
    list_editable = ('sent',)
    list_filter = ('user_group', 'sent', 'created_at')
    search_fields = ('title', 'body')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    

