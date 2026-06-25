from django.urls import path
from .views import (
    SignupView, LoginView, MeView, MeUpdateView, GetOtpView, VerifyOtpView,
    ResetPasswordView, UploadDocumentView
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='auth_signup'),
    path('login/', LoginView.as_view(), name='auth_login'),
    path('me/', MeView.as_view(), name='auth_me'),
    path('me/update/', MeUpdateView.as_view(), name='auth_me_update'),
    path('get-otp/', GetOtpView.as_view(), name='auth_get_otp'),
    path('verify-otp/', VerifyOtpView.as_view(), name='auth_verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='auth_reset_password'),
    path('upload-document/', UploadDocumentView.as_view(), name='auth_upload_document'),
]
