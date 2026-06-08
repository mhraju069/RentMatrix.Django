from django_bolt import Router
from .schema import *
from .models import Booking
from .utils import *
from apps.property.schema import PropertyListSchema
from apps.property.models import Property
from django.http import JsonResponse
from django_bolt.auth import JWTAuthentication, IsAuthenticated
from django.db.models import Avg

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
async def confirm_booking(request, booking_id, data: ConfirmBookingSchema):
    booking = await Booking.objects.filter(id=booking_id).afirst()
    if not booking:
        return JsonResponse(data={"status": 404, "success": False, "message": "Booking not found"}, status=404)

    if booking.status == "CONFIRMED":
        return JsonResponse(data={"status": 400, "success": False, "message": "Booking already confirmed"}, status=400)

    if booking.status == "CANCELLED":
        return JsonResponse(data={"status": 400, "success": False, "message": "Booking cannot be confirmed as it is cancelled"}, status=400)

    payment = await Create_payment_intent(request, booking.id, booking.price, data.payment_method_id)
    
    if not payment["success"]:
        return JsonResponse(data={"status": payment["status"], "success": payment["success"], "message": payment["message"]}, status=payment["status"])

    if payment["success"] and not payment.get("requires_action"):
        booking.status = "CONFIRMED"
        await booking.asave()
    
    return JsonResponse({
        "status": 200,
        "success": True,
        "message": "Booking confirmed successfully",
        "payment": payment
    })




@api.post('/payment/success')
async def payment_success(request):
    
    return JsonResponse({
        "status": 200,
        "success": True,
        "message": "Payment success",
    })




@api.get('/list', auth=[JWTAuthentication()], guards=[IsAuthenticated()], response_model=BookingListResponseSchema)
async def booking_list(request):
    bookings = Booking.objects.filter(user=request.user).select_related('property').annotate(
        property_avg_rating=Avg('property__reviews__rating')
    )
    booking_data = []
    async for booking in bookings:
        p = booking.property
        avg_rating = booking.property_avg_rating or 0.0
        booking_data.append(
            BookingListSchema(
                id=booking.id,
                property=PropertyListSchema(
                    id=p.id,
                    name=p.name,
                    address=p.address,
                    price=float(p.price or 0.0),
                    bathroom=p.bathroom or 0,
                    bedroom=p.bedroom or 0,
                    size=p.area or "",
                    type=p.type,
                    average_rating=f"{avg_rating:.1f}",
                    cover=p.cover_image.url if p.cover_image else "",
                ),
                name=booking.name,
                phone=booking.phone,
                email=booking.email,
                guest_count=booking.guest_count,
                check_in=booking.check_in.isoformat() if booking.check_in else "",
                check_out=booking.check_out.isoformat() if booking.check_out else "",
                price=float(booking.price),
                status=booking.status,
            )
        )
    return BookingListResponseSchema(
        status=200,
        success=True,
        message="Booking list fetched successfully",
        data=booking_data
    )