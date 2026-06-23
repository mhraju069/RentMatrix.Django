import base64,uuid
from django.db.models import F
from django.http import JsonResponse
from django.db.models import Avg
from django.core.files.base import ContentFile
from django_bolt import Router, UploadFile
from django_bolt.params import File
from typing import Optional
from .models import *
from .schema import *
from .utils import _handle_multipart_property_creation, _handle_multipart_property_update
from django_bolt.auth import JWTAuthentication, IsAuthenticated
from django.conf import settings
from asgiref.sync import sync_to_async


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
        properties = properties.filter(status="AVAILABLE")

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



# @owner_api.post('/create', response_model=PropertyListResponse, auth=[JWTAuthentication()], guards=[IsAuthenticated()], summary="Create New Property (Async)")
# async def create_property(request, cover: Optional[UploadFile] = File(None)):
#     try:
#         property_obj = await sync_to_async(_handle_multipart_property_creation, thread_sensitive=False)(request)
        
#         return PropertyListResponse(
#             status=200,
#             message="Property created successfully asynchronously",
#             success=True,
#             data=[
#                 PropertyListSchema(
#                     id=property_obj.id,
#                     name=property_obj.name,
#                     price=float(property_obj.price or 0.0),
#                     bathroom=property_obj.bathroom or 0,
#                     bedroom=property_obj.bedroom or 0,
#                     size=property_obj.area or "",
#                     type=property_obj.type,
#                     sea_view=property_obj.sea_view,
#                     cover=f"{settings.BACKEND_URI}{property_obj.cover_image.url}" if property_obj.cover_image else "",
#                     average_rating="0.0",
#                     address=property_obj.address,
#                     views=0,
#                 )
#             ]
#         )
        
#     except ValueError as val_err:
#         return JsonResponse({"success": False, "message": str(val_err)}, status=400)
#     except Exception as e:
#         return JsonResponse({"success": False, "error": str(e)}, status=500)



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



# @owner_api.post('/update/{property_id:uuid}', auth=[JWTAuthentication()], guards=[IsAuthenticated()], summary="Update Property")
# async def update_property(request, property_id: uuid.UUID, cover: Optional[UploadFile] = File(None)):
#     try:
#         await sync_to_async(_handle_multipart_property_update, thread_sensitive=False)(request, property_id)
        
#         return JsonResponse({"status": 200, "success": True, "message": "Property updated successfully"}, status=200)

#     except KeyError as key_err:
#         return JsonResponse({"status": 404, "success": False, "message": str(key_err)}, status=404)
#     except Exception as e:
#         return JsonResponse({"status": 500, "success": False, "error": str(e)}, status=500)


from rest_framework import views
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django_bolt.auth import Token
from django.contrib.auth import get_user_model
from .serializers import PropertySerializer

class BoltDRFAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization") or request.META.get("HTTP_AUTHORIZATION")
        if not auth_header:
            return None
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
            
        token_str = parts[1]
        try:
            from django.conf import settings
            token_obj = Token.decode(token_str, secret=settings.SECRET_KEY)
        except Exception as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")
            
        User = get_user_model()
        try:
            user = User.objects.get(pk=token_obj.sub)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found")
            
        return (user, token_str)

class CreatePropertyDRF(views.APIView):
    authentication_classes = [BoltDRFAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({"status": 200,"success": True, "message": "Properties fetched successfully"}, status=200)
    
    def post(self, request):
        import json

        def safe_int(val, default=None):
            if val in (None, "", "null"):
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def safe_float(val, default=None):
            if val in (None, "", "null"):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def safe_getlist(key):
            if hasattr(request.data, "getlist"):
                return request.data.getlist(key)
            val = request.data.get(key)
            if val is None:
                return []
            return val if isinstance(val, list) else [val]

        # Helper to parse list/dict fields from JSON string or list
        def parse_json_field(val):
            if not val:
                return []
            if isinstance(val, str):
                try:
                    loaded = json.loads(val)
                    if isinstance(loaded, list):
                        return loaded
                    elif isinstance(loaded, dict):
                        return [loaded]
                except Exception:
                    return [val] if val else []
            if isinstance(val, list):
                res = []
                for item in val:
                    if isinstance(item, dict):
                        res.append(item)
                    elif isinstance(item, str):
                        try:
                            loaded = json.loads(item)
                            if isinstance(loaded, dict):
                                res.append(loaded)
                            elif isinstance(loaded, list):
                                res.extend(loaded)
                            else:
                                res.append(item)
                        except Exception:
                            res.append(item)
                    else:
                        res.append(item)
                return res
            return []

        # Parse amenities
        amenities_raw = request.data.get("amenities") or safe_getlist("amenities")
        amenities_parsed = parse_json_field(amenities_raw)
        amenities = []
        for item in amenities_parsed:
            if isinstance(item, dict):
                amenities.append(item)
            elif isinstance(item, str):
                amenities.append({"name": item})

        # Parse gallery
        gallery_raw = request.data.get("gallery") or safe_getlist("gallery")
        gallery_parsed = parse_json_field(gallery_raw)
        gallery_files = request.FILES.getlist("gallery_files") or request.FILES.getlist("gallery")
        
        gallery = []
        for index, item in enumerate(gallery_parsed):
            g_item = {}
            if isinstance(item, dict):
                g_item = item.copy()
            elif isinstance(item, str):
                g_item = {"type": item}
            
            if "file" not in g_item and index < len(gallery_files):
                g_item["file"] = gallery_files[index]
            gallery.append(g_item)

        # Parse advantage_prices, add_ons_prices, season_prices
        advantage_prices = parse_json_field(request.data.get("advantage_prices") or safe_getlist("advantage_prices"))
        add_ons_prices = parse_json_field(request.data.get("add_ons_prices") or safe_getlist("add_ons_prices"))
        season_prices = parse_json_field(request.data.get("season_prices") or safe_getlist("season_prices"))

        data = {
            "name": request.data.get("name"),
            "about": request.data.get("about"),
            "price_daily": request.data.get("price_daily") if request.data.get("price_daily") not in (None, "") else None,
            "price_monthly": request.data.get("price_monthly") if request.data.get("price_monthly") not in (None, "") else None,
            "bathroom": safe_int(request.data.get("bathroom")),
            "bedroom": safe_int(request.data.get("bedroom")),
            "area": request.data.get("area"),
            "type": request.data.get("type", "HOUSE"),
            "status": request.data.get("status", "AVAILABLE"),
            "verified": str(request.data.get("verified", "true")).lower() in ("true", "1"),
            "sea_view": str(request.data.get("sea_view", "false")).lower() in ("true", "1"),
            "address": request.data.get("address"),
            "latitude": safe_float(request.data.get("latitude")),
            "longitude": safe_float(request.data.get("longitude")),
            "owner": request.user.id if request.user and request.user.is_authenticated else None,
            "cover": request.FILES.get("cover") or request.data.get("cover"),
            "amenities": amenities,
            "gallery": gallery,
            "advantage_prices": advantage_prices,
            "add_ons_prices": add_ons_prices,
            "season_prices": season_prices,
            "hosted_by": request.data.get("hosted_by"),
            "whatsapp": request.data.get("whatsapp"),
            "views": safe_int(request.data.get("views"), 0),
        }
        
        serializer = PropertySerializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"status": 200,"success": True, "message": "Property created successfully"}, status=200)
        return Response({"status": 400,"success": False, "message": "Invalid data", "errors": serializer.errors}, status=400)


class UpdatePropertyDRF(views.APIView):
    authentication_classes = [BoltDRFAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, property_id):
        try:
            property_obj = Property.objects.get(id=property_id, owner=request.user)
        except Property.DoesNotExist:
            return Response({"status": 404, "success": False, "message": "Property not found or unauthorized"}, status=404)

        import json

        def safe_int(val, default=None):
            if val in (None, "", "null"):
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def safe_float(val, default=None):
            if val in (None, "", "null"):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def safe_getlist(key):
            if hasattr(request.data, "getlist"):
                return request.data.getlist(key)
            val = request.data.get(key)
            if val is None:
                return []
            return val if isinstance(val, list) else [val]

        # Helper to parse list/dict fields from JSON string or list
        def parse_json_field(val):
            if not val:
                return []
            if isinstance(val, str):
                try:
                    loaded = json.loads(val)
                    if isinstance(loaded, list):
                        return loaded
                    elif isinstance(loaded, dict):
                        return [loaded]
                except Exception:
                    return [val] if val else []
            if isinstance(val, list):
                res = []
                for item in val:
                    if isinstance(item, dict):
                        res.append(item)
                    elif isinstance(item, str):
                        try:
                            loaded = json.loads(item)
                            if isinstance(loaded, dict):
                                res.append(loaded)
                            elif isinstance(loaded, list):
                                res.extend(loaded)
                            else:
                                res.append(item)
                        except Exception:
                            res.append(item)
                    else:
                        res.append(item)
                return res
            return []

        data = {}
        
        def set_if_present(key, transform=None):
            if key in request.data:
                val = request.data.get(key)
                if transform:
                    data[key] = transform(val)
                else:
                    data[key] = val

        set_if_present("name")
        set_if_present("about")
        set_if_present("address")
        set_if_present("area")
        set_if_present("type")
        set_if_present("status")
        set_if_present("hosted_by")
        set_if_present("whatsapp")
        
        if "price_daily" in request.data:
            val = request.data.get("price_daily")
            data["price_daily"] = val if val not in (None, "") else None
            
        if "price_monthly" in request.data:
            val = request.data.get("price_monthly")
            data["price_monthly"] = val if val not in (None, "") else None

        set_if_present("bathroom", safe_int)
        set_if_present("bedroom", safe_int)
        set_if_present("latitude", safe_float)
        set_if_present("longitude", safe_float)
        set_if_present("views", safe_int)

        if "verified" in request.data:
            data["verified"] = str(request.data.get("verified")).lower() in ("true", "1")
        if "sea_view" in request.data:
            data["sea_view"] = str(request.data.get("sea_view")).lower() in ("true", "1")

        if "cover" in request.FILES:
            data["cover"] = request.FILES.get("cover")
        elif "cover" in request.data:
            data["cover"] = request.data.get("cover")

        if "amenities" in request.data:
            amenities_raw = request.data.get("amenities") or safe_getlist("amenities")
            amenities_parsed = parse_json_field(amenities_raw)
            amenities = []
            for item in amenities_parsed:
                if isinstance(item, dict):
                    amenities.append(item)
                elif isinstance(item, str):
                    amenities.append({"name": item})
            data["amenities"] = amenities

        if "gallery" in request.data or "gallery_files" in request.FILES:
            gallery_raw = request.data.get("gallery") or safe_getlist("gallery")
            gallery_parsed = parse_json_field(gallery_raw)
            gallery_files = request.FILES.getlist("gallery_files") or request.FILES.getlist("gallery")
            
            gallery = []
            for index, item in enumerate(gallery_parsed):
                g_item = {}
                if isinstance(item, dict):
                    g_item = item.copy()
                elif isinstance(item, str):
                    g_item = {"type": item}
                
                if "file" not in g_item and index < len(gallery_files):
                    g_item["file"] = gallery_files[index]
                gallery.append(g_item)
            data["gallery"] = gallery

        if "advantage_prices" in request.data:
            data["advantage_prices"] = parse_json_field(request.data.get("advantage_prices") or safe_getlist("advantage_prices"))
            
        if "add_ons_prices" in request.data:
            data["add_ons_prices"] = parse_json_field(request.data.get("add_ons_prices") or safe_getlist("add_ons_prices"))
            
        if "season_prices" in request.data:
            data["season_prices"] = parse_json_field(request.data.get("season_prices") or safe_getlist("season_prices"))

        serializer = PropertySerializer(instance=property_obj, data=data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"status": 200, "success": True, "message": "Property updated successfully"}, status=200)
        return Response({"status": 400, "success": False, "message": "Invalid data", "errors": serializer.errors}, status=400)
