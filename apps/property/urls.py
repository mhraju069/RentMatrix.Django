from django.urls import path
from .views import *

urlpatterns = [
    # Guest Endpoints
    path('guest/property/', PropertyGuestViewSet.as_view({'get': 'list'}), name='guest-property-list'),
    path('guest/property/<uuid:pk>/', PropertyGuestViewSet.as_view({'get': 'retrieve'}), name='guest-property-detail'),
    path('guest/favourite/', FavouritePropertyView.as_view(), name='favourite-list'),
    path('guest/favourite/<uuid:property_id>/', FavouritePropertyView.as_view(), name='favourite-action'),
    path('guest/report/', ReportPropertyView.as_view(), name='report-property'),
    
    # Owner Endpoints
    path('owner/property/', PropertyOwnerViewSet.as_view({'get': 'list'}), name='owner-property-list'),
    path('owner/property/<uuid:pk>/', PropertyOwnerViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}), name='owner-property-detail'),
    path('owner/create-property/', CreatePropertyDRF.as_view(), name='owner-property-create'),
    path('owner/update-property/<uuid:property_id>/', UpdatePropertyDRF.as_view(), name='owner-property-update'),
    path('owner/update-gallery/<int:media_id>/', UpdateGallery.as_view(), name='owner-gallery-update'),
]
