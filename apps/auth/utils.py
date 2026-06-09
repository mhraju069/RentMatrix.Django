import msgspec
from .models import User
from django.core.mail import send_mail
from django.conf import settings
from .schema import UpdateUserSchema

async def send_otp(email, otp_code, task="verification"):

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




def _handle_multipart_user_update(request):
    user = request.user

    try:
        parsed_dict = {
            "name": request.POST.get("name") if "name" in request.POST else None,
            "phone": request.POST.get("phone") if "phone" in request.POST else None,
            "old_password": request.POST.get("old_password") if "old_password" in request.POST else None,
            "new_password": request.POST.get("new_password") if "new_password" in request.POST else None,
        }
        
        data = msgspec.convert(parsed_dict, UpdateUserSchema)
    except Exception as parse_err:
        raise ValueError(f"Validation/Parsing error: {str(parse_err)}")

    if data.name is not None:
        user.name = data.name
    if data.phone is not None:
        user.phone = data.phone

    if data.new_password is not None:
        if not data.old_password or not data.new_password:
            raise ValueError("Old and new password are required")
        
        if not user.check_password(data.old_password):
            raise ValueError("Invalid old password")
            
        user.set_password(data.new_password)

    uploaded_image = request.FILES.get("image")
    if uploaded_image:
        if not uploaded_image.content_type.startswith("image/"):
            raise ValueError("Uploaded file is not a valid image")
            
        user.image = uploaded_image

    user.save()
    return user