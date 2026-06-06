from django_bolt import BoltAPI
from apps.auth.api import api as auth_router
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]

api = BoltAPI()
api.include_router(auth_router)


