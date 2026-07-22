from django.urls import path
from .views import LanguageViewSet, CurrencyViewSet, UserPreferenceView, ReviewView, ReviewRetrieveUpdateDestroyView

urlpatterns = [
    path('languages/', LanguageViewSet.as_view({'get': 'list'}), name='languages-list'),
    path('currencies/', CurrencyViewSet.as_view({'get': 'list'}), name='currencies-list'),
    path('preferences/', UserPreferenceView.as_view(), name='user-preferences'),
    path('reviews/<uuid:property_id>/', ReviewView.as_view(), name='reviews-list-create'),
    path('reviews/<uuid:pk>/', ReviewRetrieveUpdateDestroyView.as_view(), name='reviews-detail'),
]
