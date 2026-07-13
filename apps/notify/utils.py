import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from django.conf import settings
from .models import NotifySettings, DeviceToken, Notification


def send_notification(token,title,body,data=None):
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
            data=data,
            token=token,
        )

        response = messaging.send(message)
        print(f"Notification sent successfully: {response}")

    except Exception as e:
        print(f"Error sending notification: {e}")
    


def checkin_reminder():
    try:
        from django.utils import timezone
        import datetime
        from apps.booking.models import Booking
        
        today = timezone.now().date()
        tomorrow = today + datetime.timedelta(days=1)
        
        # 1. Reminders for check-ins tomorrow
        upcoming_checkins = Booking.objects.filter(check_in=tomorrow, status='CONFIRMED')
        for booking in upcoming_checkins:
            # Send to owner
            send_checkin_reminder(booking.property.owner, booking)
            # Send to guest
            send_guest_checkin_reminder(booking)
            
        # 2. Reminders for check-outs tomorrow
        upcoming_checkouts = Booking.objects.filter(check_out=tomorrow, status='CHECKED_IN')
        for booking in upcoming_checkouts:
            # Send to owner
            send_checkout_reminder(booking.property.owner, booking)
            # Send to guest
            send_guest_checkout_reminder(booking)
            
    except Exception as e:
        print(f"Error sending checkin reminder: {e}")


def send_user_notification(user, title, body, notification_type, related_id=None):
    try:
        config, _ = NotifySettings.objects.get_or_create(user=user)
        
        # Check settings based on notification_type
        if notification_type in ['booking', 'about to check in', 'about to check out']:
            if not config or not config.booking:
                return
        elif notification_type == 'checkin':
            if not config or not config.checkin:
                return
        
        # Save notification to database
        notification = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            related_id=str(related_id) if related_id else None
        )
        
        # Build extra data dict for FCM
        extra_data = {
            "id": str(notification.id),
            "type": str(notification_type),
        }
        if related_id:
            extra_data["related_id"] = str(related_id)
            
        # Fetch owner's device tokens
        tokens = [token.token for token in DeviceToken.objects.filter(user=user)]
        
        for token in tokens:
            send_notification(token, title, body, data=extra_data)
            
        return notification

    except Exception as e:
        print(f"Error sending user notification: {e}")


def booking_reminder(user, booking):
    title = "New Booking Request"
    body = f"You have received a new booking for {booking.property.name} from {booking.name}."
    send_user_notification(user, title, body, notification_type="booking", related_id=booking.id)


def send_checkin_reminder(user, booking):
    title = "Upcoming Check-In"
    body = f"Reminder: Guest {booking.name} is scheduled to check in for {booking.property.name}."
    send_user_notification(user, title, body, notification_type="about to check in", related_id=booking.id)


def send_checkout_reminder(user, booking):
    title = "Upcoming Check-Out"
    body = f"Reminder: Guest {booking.name} is scheduled to check out for {booking.property.name}."
    send_user_notification(user, title, body, notification_type="about to check out", related_id=booking.id)


def send_review_notification(user, review):
    title = "New Property Review"
    body = f"A new review was submitted for {review.property.name} by {review.user.name or review.user.username}."
    send_user_notification(user, title, body, notification_type="review", related_id=review.id)


def send_guest_checkin_reminder(booking):
    title = "Upcoming Check-In"
    body = f"Reminder: Your check-in for {booking.property.name} is scheduled for tomorrow."
    send_user_notification(booking.user, title, body, notification_type="about to check in", related_id=booking.id)


def send_guest_checkout_reminder(booking):
    title = "Upcoming Check-Out"
    body = f"Reminder: Your check-out for {booking.property.name} is scheduled for tomorrow."
    send_user_notification(booking.user, title, body, notification_type="about to check out", related_id=booking.id)


def send_booking_status_notification(booking):
    status = booking.status
    if status == "CONFIRMED":
        title = "Booking Approved"
        body = f"Your booking for {booking.property.name} has been approved by the host."
    elif status == "DECLINED":
        title = "Booking Declined"
        body = f"Your booking for {booking.property.name} has been declined by the host."
    else:
        title = "Booking Status Updated"
        body = f"Your booking for {booking.property.name} has been updated to {status}."
        
    send_user_notification(booking.user, title, body, notification_type="booking", related_id=booking.id)