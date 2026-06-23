from django.urls import path
from django_bolt import BoltAPI
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from apps.property.api import CreatePropertyDRF, UpdatePropertyDRF
from apps.auth.api import api as auth_router
from apps.booking.api import api_guest as guest_booking_router
from apps.booking.api import api_owner as owner_booking_router
from apps.property.api import guest_api as guest_property_router
from apps.property.api import owner_api as owner_property_router
from apps.notify.api import owner_api as owner_notify_router
from apps.notify.api import guest_api as guest_notify_router

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/owner/property/create/', CreatePropertyDRF.as_view(), name="create-property"),
    path('api/v1/owner/property/update/<uuid:property_id>/', UpdatePropertyDRF.as_view(), name="update-property"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

api = BoltAPI()
api.include_router(auth_router)
api.include_router(guest_booking_router)
api.include_router(owner_booking_router)
api.include_router(guest_property_router)
api.include_router(owner_property_router)
api.include_router(owner_notify_router)
api.include_router(guest_notify_router)
api.mount_django("/")

