from django_bolt import Router
from django.http import JsonResponse
from .models import *
from .schema import *
from django_bolt.auth import JWTAuthentication, IsAuthenticated


owner_api = Router(prefix="/api/v1/owner/notify")
guest_api = Router(prefix="/api/v1/guest/notify")



@owner_api.post('/add-device',auth=[JWTAuthentication()], guards=[IsAuthenticated()])
async def add_device(request, data: DeviceTokenSchema):
    try:
        try:
            device_token = await DeviceToken.objects.aget(user=request.user, token=data.token)
            return JsonResponse({
                "status": 200,
                "message": "Device token already saved",
                "success": True
            })
        except DeviceToken.DoesNotExist:
            await DeviceToken.objects.acreate(user=request.user, token=data.token)
            return JsonResponse({
                "status": 200,
                "message": "Device token saved successfully",
                "success": True
            })
    except Exception as e:
        return JsonResponse({
            "status": 500,
            "message": str(e),
            "success":False
        })



@owner_api.get('', response_model=NotificationListSchema,auth=[JWTAuthentication()], guards=[IsAuthenticated()])
async def get_notifications(request):
    try:
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        notification_data = []
        async for item in notifications:
            notification_data.append(NotificationSchema(
                id=item.id,
                title=item.title,
                body=item.body,
                is_read=item.is_read,
                created_at=item.created_at.isoformat() if item.created_at else "",
            ))
        return NotificationListSchema(
            status=200,
            message="Notifications fetched successfully",
            success=True,
            data=notification_data
        )
    except Exception as e:
        return JsonResponse({
            "status": 500,
            "message": str(e),
            "success":False
        })

