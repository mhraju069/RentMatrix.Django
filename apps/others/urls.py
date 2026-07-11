from django.urls import path
from .views import LanguageViewSet, CurrencyViewSet, UserPreferenceView

urlpatterns = [
    path('languages/', LanguageViewSet.as_view({'get': 'list'}), name='languages-list'),
    path('currencies/', CurrencyViewSet.as_view({'get': 'list'}), name='currencies-list'),
    path('preferences/', UserPreferenceView.as_view(), name='user-preferences'),
]
