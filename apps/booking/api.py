from apps.booking.schema import MyBookingListResponseSchema
from django_bolt import Router
from .schema import *
from .models import Booking
from apps.property.schema import PropertyListSchema
from apps.property.models import Property
from django.http import JsonResponse
from django_bolt.auth import JWTAuthentication, IsAuthenticated
from django.db.models import Avg
from django.utils import timezone

api_guest = Router(prefix='/api/v1/guest/booking')
api_owner = Router(prefix='/api/v1/owner/booking')


@api_guest.post('/create', auth=[JWTAuthentication()], guards=[IsAuthenticated()], summary='Create Booking')
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



@api_guest.get('', auth=[JWTAuthentication()], guards=[IsAuthenticated()], response_model=BookingListResponseSchema, summary='Booking List')
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
                    views=p.views,
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



@api_guest.get('/{booking_id:uuid}', auth=[JWTAuthentication()], guards=[IsAuthenticated()], response_model=BookingDetailsResponseSchema, summary='Booking Details')
async def booking_details(request, booking_id):
    booking = await Booking.objects.filter(id=booking_id, user=request.user).select_related('property', 'property__owner').annotate(
        property_avg_rating=Avg('property__reviews__rating')
    ).afirst()
    if not booking:
        return JsonResponse(data={"status": 404, "success": False, "message": "Booking not found"}, status=404)

    p = booking.property
    avg_rating = booking.property_avg_rating or 0.0
    
    details = BookingDetailsSchema(
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
        owner=UserDataSchema(
            name=p.owner.name or "",
            email=p.owner.email,
            phone=p.owner.phone or "",
            role=p.owner.role or "",
            image=p.owner.image.url if p.owner.image else None,
        ),
        name=booking.name,
        phone=booking.phone,
        email=booking.email,
        guest_count=booking.guest_count,
        check_in=booking.check_in.isoformat() if booking.check_in else "",
        check_out=booking.check_out.isoformat() if booking.check_out else "",
        price=float(booking.price),
        status=booking.status,
        created_at=booking.created_at.isoformat() if booking.created_at else "",
        updated_at=booking.updated_at.isoformat() if booking.updated_at else "",
    )

    return BookingDetailsResponseSchema(
        status=200,
        success=True,
        message="Booking details fetched successfully",
        data=details
    )



@api_guest.patch('/cancel/{booking_id:uuid}', auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary='Cancel Booking')
async def cancel_booking(request, booking_id):
    booking = await Booking.objects.filter(id=booking_id, user=request.user).afirst()
    if not booking:
        return JsonResponse(data={"status": 404, "success": False, "message": "Booking not found"}, status=404)

    if booking.status == "CANCELLED":
        return JsonResponse(data={"status": 400, "success": False, "message": "Booking already cancelled"}, status=400)

    booking.status = "CANCELLED"
    await booking.asave()

    return JsonResponse({
        "status": 200,
        "success": True,
        "message": "Booking cancelled successfully",
    })



@api_owner.get('', auth=[JWTAuthentication()], guards=[IsAuthenticated()], response_model=MyBookingListResponseSchema, summary="Owner's Booking List")
async def my_booking_list(request,status:str="ALL"):
    status_type = ['ALL','PENDING', 'CONFIRMED','CHECKED_IN','CHECKED_OUT','CANCELLED']

    if status not in status_type:
        return JsonResponse(data={"status": 400, "success": False, "message": "Invalid status"}, status=400)
    
    bookings = Booking.objects.filter(property__owner=request.user).select_related('property')

    if status != 'ALL':
        bookings = bookings.filter(status=status)

    booking_data = []
    async for p in bookings:
        booking_data.append({
            "id": p.id,
            "status": p.status,
            "name": p.property.name,
            "address": p.property.address,
            "cover": p.property.cover_image.url if p.property.cover_image else "",
        })
    return MyBookingListResponseSchema(
        status=200,
        success=True,
        message="Booking list fetched successfully",
        count = len(booking_data),
        data=booking_data
    )
