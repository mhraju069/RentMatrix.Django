from django.urls import path
from .views import GuestBookingViewSet, CancelBookingView, OwnerBookingViewSet, CalculateBookingPriceView, ConfirmBookingView

urlpatterns = [
    # Guest Endpoints
    path('guest/booking/calculate-price/', CalculateBookingPriceView.as_view(), name='calculate-price'),
    path('guest/booking/', GuestBookingViewSet.as_view({'get': 'list', 'post': 'create'}), name='guest-booking-list'),
    path('guest/booking/<uuid:pk>/', GuestBookingViewSet.as_view({'get': 'retrieve'}), name='guest-booking-detail'),
    path('guest/booking/cancel/<uuid:booking_id>/', CancelBookingView.as_view(), name='cancel-booking'),
    
    # Owner Endpoints
    path('owner/booking/', OwnerBookingViewSet.as_view({'get': 'list'}), name='owner-booking-list'),
    path('owner/booking/<uuid:pk>/', OwnerBookingViewSet.as_view({'get': 'retrieve'}), name='owner-booking-detail'),
    path('owner/booking/confirm/<uuid:booking_id>/', ConfirmBookingView.as_view(), name='confirm-booking'),
]
