import base64,uuid
from django.db.models import F
from django.http import JsonResponse
from django.db.models import Avg
from django.core.files.base import ContentFile
from django_bolt import Router
from .models import *
from .schema import *
from .utils import *
from django_bolt.auth import JWTAuthentication, IsAuthenticated
from django.conf import settings


guest_api = Router(prefix='/api/v1/guest/property')
owner_api = Router(prefix='/api/v1/owner/property')


@guest_api.get('/{property_id:uuid}', response_model=PropertyDetailSchema,auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Get Property Details")
async def get_property_details(request,property_id: uuid.UUID):
    property = await Property.objects.select_related('owner').filter(id=property_id).afirst()
    
    if not property:
        return JsonResponse(data={"status": 404, "success": False, "message": "Property not found"})
    
    property.views = F('views') + 1

    await property.asave(update_fields=['views'])
    
    amenities = [
        PropertyAmenitySchema(name=a.name)
        async for a in property.amenities.all()
    ]
    
    gallery = [
        PropertyGallerySchema(type=g.type, file=f"{settings.BACKEND_URI}{g.file.url}" if g.file else "")
        async for g in property.galleries.all()
    ]
    
    reviews = []
    async for r in property.reviews.select_related('user').all():
        reviews.append(
            ReviewSchema(
                rating=float(r.rating),
                review=r.review or "",
                user=UserSchema(
                    name=r.user.name or r.user.email,
                    image=f"{settings.BACKEND_URI}{r.user.image.url}" if r.user.image else None
                ),
                created_at=r.created_at.isoformat()
            )
        )
    
    review_count = len(reviews)
    avg_rating = sum(r.rating for r in reviews) / review_count if review_count > 0 else 0.0

    fav = await Favourites.objects.filter(user=request.user, property=property).aexists()
    
    return PropertyDetailSchema(
        name=property.name,
        about=property.about or "",
        price=float(property.price or 0.0),
        owner=UserSchema(
            name=property.owner.name or property.owner.email,
            image=f"{settings.BACKEND_URI}{property.owner.image.url}" if property.owner.image else None
        ),
        bathroom=property.bathroom or 0,
        bedroom=property.bedroom or 0,
        size=property.area or "",
        type=property.type,
        status=property.status,
        verified=property.verified,
        sea_view=property.sea_view,
        review_count=str(review_count),
        cover=f"{settings.BACKEND_URI}{property.cover_image.url}" if property.cover_image else "",
        average_rating=f"{avg_rating:.1f}",
        address=property.address,
        latitude=property.latitude or 0.0,
        longitude=property.longitude or 0.0,
        amenities=amenities,
        gallery=gallery,
        reviews=reviews,
        views=property.views,
        favourite=fav
    )



@guest_api.get('/', response_model=PropertyListResponse,auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Get Property List")
async def get_property_list(
    request, 
    type: str = "ANY", 
    search: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    sea_view = False, 
    bed: int = None,
    bath: int = None
):
    properties = Property.objects.all()

    if search:
        from django.db.models import Q
        properties = properties.filter(Q(name__icontains=search) | Q(address__icontains=search))

    if bed:
        properties = properties.filter(bedroom=bed)
        
    if bath:
        properties = properties.filter(bathroom=bath)

    if type != 'ANY':
        properties = properties.filter(type=type)
    
    if sea_view:
        val = str(sea_view).lower() in ("true", "1")
        if val:
            properties = properties.filter(sea_view=True)

    from datetime import datetime
    start_d = None
    end_d = None
    if start_date and end_date:
        try:
            start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    if start_d and end_d:
        from apps.booking.models import Booking
        booked_property_ids = Booking.objects.filter(
            status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN'],
            check_in__lt=end_d,
            check_out__gt=start_d
        ).values_list('property_id', flat=True)

        properties = properties.exclude(id__in=booked_property_ids).exclude(status="CLOSED")
    else:
        properties = properties.filter(status__in=["AVAILABLE", "OPEN", "ACTIVE"])

    data = []
    # Fetch all properties with average rating annotated in a single database query
    async for p in properties.annotate(avg_rating=Avg('reviews__rating')).all():
        avg_rating = p.avg_rating or 0.0
        fav = await Favourites.objects.filter(user=request.user, property=p).aexists()
        data.append(
            PropertyListSchema(
                id=p.id,
                name=p.name,
                price=float(p.price or 0.0),
                bathroom=p.bathroom or 0,
                bedroom=p.bedroom or 0,
                size=p.area or "",
                type=p.type,
                sea_view=p.sea_view,
                cover=f"{settings.BACKEND_URI}{p.cover_image.url}" if p.cover_image else "",
                average_rating=f"{avg_rating:.1f}",
                address=p.address,
                views=p.views,
                favourite=fav
            )
        )

    return PropertyListResponse(
        status=200,
        message="Properties fetched successfully",
        success=True,
        data=data
    )



@owner_api.post('/create', response_model=PropertyListResponse, auth=[JWTAuthentication()], guards=[IsAuthenticated()], summary="Create New Property (Async)")
async def create_property(request):
    try:
        property_obj = await sync_to_async(_handle_multipart_property_creation, thread_sensitive=False)(request)
        
        return PropertyListResponse(
            status=200,
            message="Property created successfully asynchronously",
            success=True,
            data=[
                PropertyListSchema(
                    id=property_obj.id,
                    name=property_obj.name,
                    price=float(property_obj.price or 0.0),
                    bathroom=property_obj.bathroom or 0,
                    bedroom=property_obj.bedroom or 0,
                    size=property_obj.area or "",
                    type=property_obj.type,
                    sea_view=property_obj.sea_view,
                    cover=f"{settings.BACKEND_URI}{property_obj.cover_image.url}" if property_obj.cover_image else "",
                    average_rating="0.0",
                    address=property_obj.address,
                    views=0,
                )
            ]
        )
        
    except ValueError as val_err:
        return JsonResponse({"success": False, "message": str(val_err)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)



@guest_api.post('/favourite/{property_id:uuid}', auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Add / Remove Favourite Property")
async def update_favourite_property(request, property_id: uuid.UUID, data:AddFavouriteSchema):
    try:
        try:
            property_obj = await Property.objects.aget(id=property_id)
        except Property.DoesNotExist:
            return JsonResponse({"success": False, "message": "Property not found"}, status=404)

        obj, created = await Favourites.objects.aget_or_create(
            property=property_obj,
            user=request.user
        )

        if not created:
            await obj.adelete()
            message = "Property unfavourited successfully"
        else:
            message = "Property favourited successfully"

        return JsonResponse({"success": True, "message": message}, status=200)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    


@guest_api.get('/favourite', response_model=PropertyListResponse, auth=[JWTAuthentication()], guards=[IsAuthenticated()], summary="Get Favourite Properties List")
async def get_favourite_property(request):
    try:
        favourite_properties = Favourites.objects.filter(user=request.user).select_related('property')
        
        data = []
        async for favourite_property in favourite_properties:
            prop = favourite_property.property
            review_stats = await prop.reviews.aaggregate(Avg('rating'))
            avg_rating_val = review_stats['rating__avg'] or 0.0
            
            data.append(
                PropertyListSchema(
                    id=prop.id,
                    name=prop.name,
                    price=float(prop.price or 0.0),
                    bathroom=prop.bathroom or 0,
                    bedroom=prop.bedroom or 0,
                    size=prop.area or "",
                    type=prop.type,
                    sea_view=prop.sea_view,
                    cover=f"{settings.BACKEND_URI}{prop.cover_image.url}" if prop.cover_image else "",
                    average_rating=f"{avg_rating_val:.1f}",
                    address=prop.address,
                    views=prop.views,
                )
            )
            
        return PropertyListResponse(
            status=200,
            message="Favourite properties fetched successfully",
            success=True,
            data=data
        )
        
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)



@owner_api.get('/{property_id:uuid}', response_model=MyPropertyDetailResponseSchema,auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Get Owner's Property Details")
async def get_owner_property_details(request,property_id: uuid.UUID):
    property = await Property.objects.select_related('owner').filter(id=property_id,owner=request.user).afirst()
    
    if not property:
        return JsonResponse(data={"status": 404, "success": False, "message": "Property not found"})
    
    amenities = [
        PropertyAmenitySchema(name=a.name)
        async for a in property.amenities.all()
    ]
    
    gallery = [
        PropertyGallerySchema(type=g.type, file=g.file.url if g.file else "")
        async for g in property.galleries.all()
    ]
    
    reviews = []
    async for r in property.reviews.select_related('user').all():
        reviews.append(
            ReviewSchema(
                rating=float(r.rating),
                review=r.review or "",
                user=UserSchema(
                    name=r.user.name or r.user.email,
                    image=f"{settings.BACKEND_URI}{r.user.image.url}" if r.user.image else None
                ),
                created_at=r.created_at.isoformat()
            )
        )
    
    review_count = len(reviews)
    avg_rating = sum(r.rating for r in reviews) / review_count if review_count > 0 else 0.0
    
        
    obj= PropertyDetailSchema(
        name=property.name,
        about=property.about or "",
        price=float(property.price or 0.0),
        owner=UserSchema(
            name=property.owner.name or property.owner.email,
            image=f"{settings.BACKEND_URI}{property.owner.image.url}" if property.owner.image else None
        ),
        bathroom=property.bathroom or 0,
        bedroom=property.bedroom or 0,
        size=property.area or "",
        type=property.type,
        status=property.status,
        verified=property.verified,
        sea_view=property.sea_view,
        review_count=str(review_count),
        cover=f"{settings.BACKEND_URI}{property.cover_image.url}" if property.cover_image else "",
        average_rating=f"{avg_rating:.1f}",
        address=property.address,
        latitude=property.latitude or 0.0,
        longitude=property.longitude or 0.0,
        amenities=amenities,
        gallery=gallery,
        reviews=reviews,
        views=property.views
    )

    total_bookings = await Booking.objects.filter(property=property).acount()
    # occupancy = sum(await bookings.annotate(total_nights=ExpressionWrapper(F('checkout') - F('checkin'), output_field=DurationField())).values_list('total_nights', flat=True)) / (total_bookings * 30) * 100
    # avg_stay = sum(await bookings.annotate(total_nights=ExpressionWrapper(F('checkout') - F('checkin'), output_field=DurationField())).values_list('total_nights', flat=True)) / total_bookings

    return MyPropertyDetailResponseSchema(
        status=200,
        message="Property details fetched successfully",
        success=True,
        occupancy="Not Implemented Yet",
        total_bookings=total_bookings,
        avg_stay="Not Implemented Yet",
        property=obj
    )




@owner_api.get('', response_model=MyPropertyResponseSchema,auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Get Owner's Property List")
async def get_owner_properties(request, status: str = "ANY", type: str = "ANY", search: str = None, start_date: str = None, end_date: str = None , sea_view=False, bed: int = None, bath: int = None):

    STATUS = ["ANY","AVAILABLE","BOOKED","CLOSED"]
    TYPES = ['ANY','HOUSE','VILLA','APARTMENT','COMMERCIAL']


    if status not in STATUS or type not in TYPES:
        return JsonResponse({"status": 400,"success": False, "message": "Invalid status or type"}, status=400)
        
    properties = Property.objects.filter(owner=request.user)

    if search:
        from django.db.models import Q
        properties = properties.filter(Q(name__icontains=search) | Q(address__icontains=search))
    
    if bed:
        properties = properties.filter(bedroom=bed)

    if bath:
        properties = properties.filter(bathroom=bath)

    if type != 'ANY':
        properties = properties.filter(type=type)
    
    if sea_view:
        val = str(sea_view).lower() in ("true", "1")
        if val:
            properties = properties.filter(sea_view=True)

    from datetime import datetime
    start_d = None
    end_d = None
    if start_date and end_date:
        try:
            start_d = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_d = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    if start_d and end_d:
        from apps.booking.models import Booking
        booked_property_ids = Booking.objects.filter(
            status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN'],
            check_in__lt=end_d,
            check_out__gt=start_d
        ).values_list('property_id', flat=True)

        if status == "AVAILABLE":
            properties = properties.exclude(id__in=booked_property_ids).exclude(status="CLOSED")
        elif status == "BOOKED":
            properties = properties.filter(id__in=booked_property_ids)
        elif status == "CLOSED":
            properties = properties.filter(status="CLOSED")
    else:
        if status == "AVAILABLE":
            properties = properties.filter(status__in=["AVAILABLE", "OPEN", "ACTIVE"])
        elif status == "BOOKED":
            properties = properties.filter(status="BOOKED")
        elif status == "CLOSED":
            properties = properties.filter(status="CLOSED")

    data = []
    async for property in properties:
        review_stats = await property.reviews.aaggregate(Avg('rating'))
        avg_rating_val = review_stats['rating__avg'] or 0.0

        data.append(
            MyPropertyListSchema(
                id=property.id,
                name=property.name,
                cover=f"{settings.BACKEND_URI}{property.cover_image.url}" if property.cover_image else "",
                avg_rating=f"{avg_rating_val:.1f}",
                address=property.address,
            )
        )
    
    
    return MyPropertyResponseSchema(
        status=200,
        message="Properties fetched successfully",
        success=True,
        properties=data
    )




@owner_api.delete('/delete/{property_id:uuid}',auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Delete Property")
async def delete_property(request,property_id: uuid.UUID):
    try:
        property = await Property.objects.aget(id=property_id)
    except Property.DoesNotExist:
        return JsonResponse({"status": 404,"success": False, "message": "Property not found"}, status=404)
    await property.adelete()
    return JsonResponse({"status": 200,"success": True, "message": "Property deleted successfully"}, status=200)



@owner_api.post('/update/{property_id:uuid}', auth=[JWTAuthentication()], guards=[IsAuthenticated()], summary="Update Property")
async def update_property(request, property_id: uuid.UUID,data : UpdatePropertySchema= msgspec.convert):
    try:
        await sync_to_async(_handle_multipart_property_update, thread_sensitive=False)(request, property_id)
        
        return JsonResponse({"status": 200, "success": True, "message": "Property updated successfully"}, status=200)

    except KeyError as key_err:
        return JsonResponse({"status": 404, "success": False, "message": str(key_err)}, status=404)
    except Exception as e:
        return JsonResponse({"status": 500, "success": False, "error": str(e)}, status=500)