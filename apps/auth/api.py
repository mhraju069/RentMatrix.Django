from .schema import *
from .models import *
from django_bolt import BoltAPI
from django_bolt.exceptions import Conflict
from django.http import JsonResponse
from django.db.models import Q

api = BoltAPI(prefix="/api/v1/auth")


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

    return UserDataResponseSchema(
        message="User created successfully",
        status=201,
        success=True,
        user=user_data,
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

    return UserDataResponseSchema(
        message="User logged in successfully",
        status=200,
        success=True,
        user=user_data,
    )