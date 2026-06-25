import msgspec
from .models import User
from django.core.mail import send_mail
from django.conf import settings


def send_otp(email, otp_code, task="verification"):

    try:
        subject = f"Your OTP for {task}"
        message = f"Your OTP code is {otp_code}. It will expire in 3 minutes."
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [email]
        send_mail(subject, message, email_from, recipient_list)
        
        return 200, True, "Otp Sent Successfully"

    except User.DoesNotExist:
        return 404, False, "User Not Found"

    except Exception as e:
        return 500, False, str(e)


