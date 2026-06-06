from django.urls import path
from django_bolt import BoltAPI
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from apps.auth.api import api as auth_router
from apps.booking.api import api as booking_router
from apps.property.api import api as property_router

urlpatterns = [
    path('admin/', admin.site.urls),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

api = BoltAPI()
api.include_router(auth_router)
api.include_router(booking_router)
api.include_router(property_router)

