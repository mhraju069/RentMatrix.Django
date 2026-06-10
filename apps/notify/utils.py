import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from django.conf import settings


def send_notification(token,title,body):
    try:
        cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT)
        firebase_admin.initialize_app(cred)

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )

        response = messaging.send(message)

        if response.status_code == 200:
            print("Notification sent successfully!")
        else:
            print(f"Failed to send notification: {response}")

    except Exception as e:
        print(f"Error sending notification: {e}")