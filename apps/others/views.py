from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema

from apps.others.models import Language, Currency, UserPreference
from apps.others.serializers import LanguageSerializer, CurrencySerializer, UserPreferenceSerializer
from apps.auth.utils import format_serializer_errors

class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = LanguageSerializer
    queryset = Language.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": 200,
            "success": True,
            "message": "Languages fetched successfully",
            "data": serializer.data
        })

class CurrencyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CurrencySerializer
    queryset = Currency.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": 200,
            "success": True,
            "message": "Currencies fetched successfully",
            "data": serializer.data
        })

class UserPreferenceView(views.APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserPreferenceSerializer

    def get_object(self, user):
        preference, created = UserPreference.objects.get_or_create(user=user)
        # If created and language/currency are null, try to seed default
        if created:
            if not preference.language:
                preference.language = Language.objects.filter(code='en').first()
            if not preference.currency:
                preference.currency = Currency.objects.filter(code='USD').first()
            preference.save()
        return preference

    @extend_schema(responses={200: UserPreferenceSerializer})
    def get(self, request):
        pref = self.get_object(request.user)
        serializer = UserPreferenceSerializer(pref)
        return Response({
            "status": 200,
            "success": True,
            "message": "User preferences fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(request=UserPreferenceSerializer, responses={200: UserPreferenceSerializer})
    def patch(self, request):
        pref = self.get_object(request.user)
        serializer = UserPreferenceSerializer(pref, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": 200,
                "success": True,
                "message": "Preferences updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "status": 400,
            "success": False,
            "errors": format_serializer_errors(serializer.errors)
        }, status=status.HTTP_400_BAD_REQUEST)
