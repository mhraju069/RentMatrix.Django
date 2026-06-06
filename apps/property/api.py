import uuid
from django.http import JsonResponse
from django.db.models import Avg
from django_bolt import Router
from .models import Property
from .schema import *
api = Router(prefix='/api/v1/property')


@api.get('/{id:uuid}', response_model=PropertyDetailSchema)
async def get_property_details(id: uuid.UUID):
    property = await Property.objects.select_related('owner').filter(id=id).afirst()
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
        reviews=reviews
    )


@api.get('/', response_model=PropertyListResponse)
async def get_property_list():
    data = []
    # Fetch all properties with average rating annotated in a single database query
    async for p in Property.objects.annotate(avg_rating=Avg('reviews__rating')).all():
        avg_rating = p.avg_rating or 0.0
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
                address=p.address
            )
        )

    return PropertyListResponse(
        status=200,
        message="Properties fetched successfully",
        success=True,
        data=data
    )
