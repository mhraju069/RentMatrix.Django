import os,msgspec,base64,random,string
from dotenv import load_dotenv
load_dotenv()
from .utils import *
from .schema import *
from .models import *
from django_bolt import BoltAPI
from django.http import JsonResponse
from django.db.models import Q
from django_bolt.auth import create_jwt_for_user, JWTAuthentication, IsAuthenticated, Token
from django.conf import settings
from django.core.files.base import ContentFile


api = BoltAPI(prefix="/api/v1/auth")

# Expiration constants (in seconds)
ACCESS_TOKEN_LIFETIME = int(os.getenv("ACCESS_TOKEN_LIFETIME") or 604800)
REFRESH_TOKEN_LIFETIME = int(os.getenv("REFRESH_TOKEN_LIFETIME") or 2592000)


@api.post("/signup", response_model=UserDataResponseSchema)
async def signup(request, data: CreateUserSchema):
    
    if await User.objects.filter(email=data.email).aexists():
        return JsonResponse(data={"status":400,"success":False,"message":"User with this email already exists"})
    
    if await User.objects.filter(phone=data.phone).aexists():
        return JsonResponse(data={"status":400,"success":False,"message":"User with this phone already exists"})

    user = await User.objects.acreate(
        email=data.email,
        password=data.password,
        name=data.name,
        phone=data.phone
    )

    user_data = UserDataSchema(
        email=user.email,
        role=user.role,
        name=user.name,
        phone=user.phone,
        image=user.image.url if user.image else None
    )

    access_token = create_jwt_for_user(user, expires_in=ACCESS_TOKEN_LIFETIME)
    refresh_token = create_jwt_for_user(user, expires_in=REFRESH_TOKEN_LIFETIME, extra_claims={"type": "refresh"})

    return UserDataResponseSchema(
        message="User created successfully",
        status=201,
        success=True,
        user=user_data,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    


@api.post("/login",response_model=UserDataResponseSchema)
async def login(request,data: LoginUserSchema):
    user = await User.objects.filter(Q(email=data.email) | Q(phone=data.phone)).afirst()
    
    if not user:
        return JsonResponse(data={"status":404,"success":False,"message":"User not found"})

    if not user.check_password(data.password):
        return JsonResponse(data={"status":401,"success":False,"message":"Invalid credentials"})

    user_data = UserDataSchema(
        email=user.email,
        role=user.role,
        name=user.name,
        phone=user.phone,
        image=user.image.url if user.image else None
    )

    access_token = create_jwt_for_user(user, expires_in=ACCESS_TOKEN_LIFETIME)
    refresh_token = create_jwt_for_user(user, expires_in=REFRESH_TOKEN_LIFETIME, extra_claims={"type": "refresh"})

    return UserDataResponseSchema(
        message="User logged in successfully",
        status=200,
        success=True,
        user=user_data,
        access_token=access_token,
        refresh_token=refresh_token,
    )



@api.post("/refresh", response_model=TokenResponseSchema)
async def refresh(request, data: RefreshRequestSchema):
    try:
        # Decode and validate refresh token
        token_obj = Token.decode(data.refresh_token, secret=settings.SECRET_KEY)
    except ValueError:
        return JsonResponse(data={"status": 401, "success": False, "message": "Invalid or expired refresh token"})

    # Verify that this is actually a refresh token
    if token_obj.extras.get("type") != "refresh":
        return JsonResponse(data={"status": 400, "success": False, "message": "Invalid token type"})

    try:
        user = await User.objects.aget(pk=token_obj.sub)
    except User.DoesNotExist:
        return JsonResponse(data={"status": 404, "success": False, "message": "User not found"})

    # Issue new access and refresh tokens
    new_access_token = create_jwt_for_user(user, expires_in=ACCESS_TOKEN_LIFETIME)
    new_refresh_token = create_jwt_for_user(user, expires_in=REFRESH_TOKEN_LIFETIME, extra_claims={"type": "refresh"})

    return TokenResponseSchema(
        message="Token refreshed successfully",
        status=200,
        success=True,
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )



@api.get("/me", response_model=UserDataResponseSchema, auth=[JWTAuthentication()], guards=[IsAuthenticated()])
async def me(request):
    user = request.user
    user_data = UserDataSchema(
        email=user.email,
        role=user.role,
        name=user.name,
        phone=user.phone,
        image=user.image.url if user.image else None
    )
    return UserDataResponseSchema(
        message="User fetched successfully",
        status=200,
        success=True,
        user=user_data,
    )



@api.post("/get-otp")
async def get_otp(request, data: GetOtpSchema):

    user = await User.objects.filter(email=data.email).afirst()
    if not user:
        return JsonResponse(data={"status":404,"success":False,"message":"User not found"})
    
    await OTP.objects.filter(user=user).adelete()
        
    otp_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    await OTP.objects.acreate(
        user=user,
        otp=otp_code
    )
        
    status, res, msg = await send_otp(user.email, otp_code, "Login")
    
    return JsonResponse(data={"status":status,"success":res,"message":msg})



@api.post("/verify-otp")
async def verify_otp(request, data: VerifyOtpSchema):

    user = await User.objects.filter(email=data.email).afirst()
    if not user:
        return JsonResponse(data={"status":404,"success":False,"message":"User not found"})
    
    otp_code = await OTP.objects.filter(user=user).afirst()
    if not otp_code:
        return JsonResponse(data={"status":404,"success":False,"message":"OTP not found"})
    
    print(otp_code.otp)
    print(data.otp)
    print(otp_code.otp == data.otp)

    if otp_code.otp != data.otp:
        return JsonResponse(data={"status":400,"success":False,"message":"Invalid OTP"})
    
    if otp_code.is_expired():
        await otp_code.adelete()
        return JsonResponse(data={"status":400,"success":False,"message":"OTP expired"})

    await otp_code.adelete()


    access_token = create_jwt_for_user(user, expires_in=ACCESS_TOKEN_LIFETIME)
    refresh_token = create_jwt_for_user(user, expires_in=REFRESH_TOKEN_LIFETIME, extra_claims={"type": "refresh"})

    user_data = UserDataSchema(
        email=user.email,
        role=user.role,
        name=user.name,
        phone=user.phone,
        image=user.image.url if user.image else None
    )

    return UserDataResponseSchema(
        message="Otp verified successfully",
        status=200,
        success=True,
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_data,
    )



@api.patch("/me/update", auth=[JWTAuthentication()], guards=[IsAuthenticated()],response_model=UserDataResponseSchema)
async def me_update(request, data: UpdateUserSchema):
    user = request.user
    for key, value in msgspec.structs.asdict(data).items():
        if value is not None:
            if key == "new_password":
                if not data.old_password or not data.new_password:
                    return JsonResponse(data={"status":400,"success":False,"message":"Old and new password are required"})
                
                if not user.check_password(data.old_password):
                    return JsonResponse(data={"status":400,"success":False,"message":"Invalid old password"})
                
                user.set_password(data.new_password)
                continue
            
            if key == "image":
                
                try:
                    format, imgstr = value.split(';base64,')
                    ext = format.split('/')[-1]
                    file_data = ContentFile(base64.b64decode(imgstr), name=f"profile_{user.id}.{ext}")
                    user.image = file_data
                except Exception as e:
                    print("Error processing image while updating user data: ", str(e))
                
                continue

            if key in ("name", "phone"):
                setattr(user, key, value)
                continue
    await user.asave()
    
    user_data = UserDataSchema(
        email=user.email,
        role=user.role,
        name=user.name,
        phone=user.phone,
        image=user.image.url if user.image else None
    )
    return UserDataResponseSchema(
        message="User updated successfully",
        status=200,
        success=True,
        user=user_data,
    )



@api.post("/reset-password",auth=[JWTAuthentication()], guards=[IsAuthenticated()],response_model=UserDataResponseSchema)
async def reset_password(request, data: ResetPasswordSchema):
    user = request.user

    user.set_password(data.new_password)
    await user.asave()

    access_token = create_jwt_for_user(user, expires_in=ACCESS_TOKEN_LIFETIME)
    refresh_token = create_jwt_for_user(user, expires_in=REFRESH_TOKEN_LIFETIME, extra_claims={"type": "refresh"})

    user_data = UserDataSchema(
        email=user.email,
        role=user.role,
        name=user.name,
        phone=user.phone,
        image=user.image.url if user.image else None
    )
    return UserDataResponseSchema(
        message="Password reset successfully",
        status=200,
        success=True,
        user=user_data,
        access_token=access_token,
        refresh_token=refresh_token,
    )

    



    
