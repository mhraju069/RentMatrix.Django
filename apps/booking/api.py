from django_bolt import Router
from .schema import *
from .models import Booking
from apps.property.models import Property
from django.http import JsonResponse
from django_bolt.auth import JWTAuthentication, IsAuthenticated

api = Router(prefix='/api/v1/booking')


@api.post('/create', auth=[JWTAuthentication()], guards=[IsAuthenticated()])
async def create_booking(request, data: CreateBookingSchema):
    property = await Property.objects.filter(id=data.property_id).afirst()

    if not property:
        return JsonResponse(data={"status": 404, "success": False, "message": "Property not found"}, status=404)
    
    price = property.price or 0.0
    
    booking = await Booking.objects.acreate(
        property=property,
        user=request.user,
        price=price,
        name=data.name,
        phone=data.phone,
        email=data.email,
        guest_count=data.num_guests,
        check_in=data.start_date,
        check_out=data.end_date,
    )
    
    return JsonResponse({
        "status": 200,
        "success": True,
        "message": "Booking created successfully",
        "data": {
            "id": booking.id,
            "property_id": str(property.id),
            "name": booking.name,
            "phone": booking.phone,
            "email": booking.email,
            "guest_count": booking.guest_count,
            "check_in": booking.check_in.isoformat() if booking.check_in else "",
            "check_out": booking.check_out.isoformat() if booking.check_out else "",
            "price": float(booking.price),
            "status": booking.status,
        }
    })



@api.post('/confirm/{booking_id:uuid}', auth=[JWTAuthentication()], guards=[IsAuthenticated()])
async def confirm_booking(request, booking_id):
    booking = await Booking.objects.filter(id=booking_id).afirst()
    if not booking:
        return JsonResponse(data={"status": 404, "success": False, "message": "Booking not found"}, status=404)

    if booking.status == "CONFIRMED":
        return JsonResponse(data={"status": 400, "success": False, "message": "Booking already confirmed"}, status=400)

    if booking.status == "CANCELLED":
        return JsonResponse(data={"status": 400, "success": False, "message": "Booking cannot be confirmed as it is cancelled"}, status=400)

    booking.status = "CONFIRMED"
    await booking.asave()
    return JsonResponse({
        "status": 200,
        "success": True,
        "message": "Booking confirmed successfully",
        "data": {
            "id": booking.id,
            "property_id": str(booking.property_id),
            "name": booking.name,
            "phone": booking.phone,
            "email": booking.email,
            "guest_count": booking.guest_count,
            "check_in": booking.check_in.isoformat() if booking.check_in else "",
            "check_out": booking.check_out.isoformat() if booking.check_out else "",
            "price": float(booking.price),
            "status": booking.status,
        }
    })
    