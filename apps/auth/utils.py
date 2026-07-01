import random
import string

from django.conf import settings
from django.core.mail import send_mail

from .models import User, OTP


def send_otp(user, task="verification"):
    otp_code = str(random.randint(1000, 9999))

    OTP.objects.filter(user=user).delete()
    OTP.objects.create(user=user, otp=otp_code)

    try:
        subject = f"Your OTP for {task}"
        message = f"Your OTP code is {otp_code}. It will expire in 3 minutes."
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [user.email]
        send_mail(subject, message, email_from, recipient_list)
        return True
    except Exception:
        return False


def format_serializer_errors(errors):
    if not errors:
        return ""
    if isinstance(errors, dict):
        for field, error_list in errors.items():
            if isinstance(error_list, list) and error_list:
                first_error = error_list[0]
                if isinstance(first_error, dict):
                    return format_serializer_errors(first_error)
                return str(first_error)
            elif isinstance(error_list, dict):
                return format_serializer_errors(error_list)
            else:
                return str(error_list)
    elif isinstance(errors, list) and errors:
        first_error = errors[0]
        if isinstance(first_error, dict):
            return format_serializer_errors(first_error)
        return str(first_error)
    return str(errors)



