from django.urls import path
from .views import AddDeviceTokenView, NotificationViewSet, NotifySettingsView

urlpatterns = [
    # Settings Endpoints
    path('settings/', NotifySettingsView.as_view(), name='notify-settings'),

    # Guest Endpoints
    path('guest/notify/add-device/', AddDeviceTokenView.as_view(), name='add-device-guest'),
    path('guest/notify/', NotificationViewSet.as_view({'get': 'list'}), name='guest-notify-list'),
    
    # Owner Endpoints
    path('owner/notify/add-device/', AddDeviceTokenView.as_view(), name='add-device-owner'),
    path('owner/notify/', NotificationViewSet.as_view({'get': 'list'}), name='owner-notify-list'),
]
