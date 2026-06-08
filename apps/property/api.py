from apps.property.models import Favourites
import base64
import uuid
from django.http import JsonResponse
from django.db.models import Avg
from django.core.files.base import ContentFile
from django_bolt import Router
from .models import *
from .schema import *
from django_bolt.auth import JWTAuthentication, IsAuthenticated


def decode_base64_file(data_str: str, prefix: str = "file") -> ContentFile | None:
    if not data_str or ";base64," not in data_str:
        return None
    try:
        format, imgstr = data_str.split(';base64,')
        ext = format.split('/')[-1]
        if '+' in ext:
            ext = ext.split('+')[0]
        file_name = f"{prefix}_{uuid.uuid4().hex}.{ext}"
        return ContentFile(base64.b64decode(imgstr), name=file_name)
    except Exception as e:
        print(f"Error decoding base64 file: {e}")
        return None


api = Router(prefix='/api/v1/guest/property')


@api.get('/{property_id:uuid}', response_model=PropertyDetailSchema,auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Get Property Details")
async def get_property_details(request,property_id: uuid.UUID):
    property = await Property.objects.select_related('owner').filter(id=property_id).afirst()
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
                    image=r.user.image.url if r.user.image else None
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
            image=property.owner.image.url if property.owner.image else None
        ),
        bathroom=property.bathroom or 0,
        bedroom=property.bedroom or 0,
        size=property.area or "",
        type=property.type,
        status=property.status,
        verified=property.verified,
        review_count=str(review_count),
        cover=property.cover_image.url if property.cover_image else "",
        average_rating=f"{avg_rating:.1f}",
        address=property.address,
        latitude=property.latitude or 0.0,
        longitude=property.longitude or 0.0,
        amenities=amenities,
        gallery=gallery,
        reviews=reviews,
        favourite=fav
    )



@api.get('/', response_model=PropertyListResponse,auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Get Property List")
async def get_property_list(request):
    data = []
    # Fetch all properties with average rating annotated in a single database query
    async for p in Property.objects.annotate(avg_rating=Avg('reviews__rating')).all():
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
                cover=p.cover_image.url if p.cover_image else "",
                average_rating=f"{avg_rating:.1f}",
                address=p.address,
                favourite=fav
            )
        )

    return PropertyListResponse(
        status=200,
        message="Properties fetched successfully",
        success=True,
        data=data
    )



@api.post('/create', response_model=PropertyListResponse, auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Create New Property")
async def create_property(request, data: CreatePropertySchema):
    cover_file = decode_base64_file(data.cover, prefix="cover") if data.cover else None

    property = await Property.objects.acreate(
        owner=request.user,
        name=data.name,
        address=data.address,
        bedroom=data.bedroom,
        bathroom=data.bathroom,
        area=data.size,
        about=data.about,
        cover_image=cover_file,
        latitude=data.latitude,
        longitude=data.longitude,
        price=data.price,
        type=data.type,
    )

    if data.amenities:
        for amenity in data.amenities:
            await Amenity.objects.acreate(
                property=property,
                name=amenity.name
            )

    if data.gallery:
        for gallery_item in data.gallery:
            gallery_file = decode_base64_file(gallery_item.file, prefix="gallery")
            if gallery_file:
                await Gallery.objects.acreate(
                    property=property,
                    type=gallery_item.type,
                    file=gallery_file
                )
            
    return PropertyListResponse(
        status=200,
        message="Property created successfully",
        success=True,
        data=[
            PropertyListSchema(
                id=property.id,
                name=property.name,
                price=float(property.price or 0.0),
                bathroom=property.bathroom or 0,
                bedroom=property.bedroom or 0,
                size=property.area or "",
                type=property.type,
                cover=property.cover_image.url if property.cover_image else "",
                average_rating="0.0",
                address=property.address,
            )
        ]
    )



@api.post('/favourite/{property_id:uuid}', auth=[JWTAuthentication()], guards=[IsAuthenticated()],summary="Add / Remove Favourite Property")
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
    


@api.get('/favourite', response_model=PropertyListResponse, auth=[JWTAuthentication()], guards=[IsAuthenticated()], summary="Get Favourite Properties List")
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
                    cover=prop.cover_image.url if prop.cover_image else "",
                    average_rating=f"{avg_rating_val:.1f}",
                    address=prop.address,
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