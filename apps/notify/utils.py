import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from django.conf import settings
from .models import NotifySettings, DeviceToken, Notification


def send_notification(token,title,body):
    try:
        if not firebase_admin._apps:
            import os
            cred_path = os.path.join(settings.BASE_DIR, "firebase-key.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )

        response = messaging.send(message)
        print(f"Notification sent successfully: {response}")

    except Exception as e:
        print(f"Error sending notification: {e}")
    


def checkin_reminder():
    try:
        pass
    except Exception as e:
        print(f"Error sending checkin reminder: {e}")




async def booking_reminder(user, booking):
    try:
        config, _ = await NotifySettings.objects.aget_or_create(user=user)
        
        if not config or not config.booking:
            return
        
        title = "New Booking Request"
        body = f"You have received a new booking for {booking.property.name} from {booking.name}."
        
        # Save notification to database
        await Notification.objects.acreate(
            user=user,
            title=title,
            body=body
        )
        
        # Fetch owner's device tokens
        tokens = [token.token async for token in DeviceToken.objects.filter(user=user)]
        
        from asgiref.sync import sync_to_async
        async_send = sync_to_async(send_notification)
        
        for token in tokens:
            await async_send(token, title, body)

    except Exception as e:
        print(f"Error sending booking reminder: {e}")