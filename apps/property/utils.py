from apps.property.models import Property,Amenity,Gallery
from .schema import CreatePropertySchema
import msgspec
import json

def _handle_multipart_property_creation(request):
    # মাল্টিপার্ট ডাটা সিঙ্ক থ্রেডে রিড করা হচ্ছে (সেফ এবং নন-ব্লকিং)
    try:
        amenities_raw = request.POST.get("amenities")
        gallery_raw = request.POST.get("gallery")
        
        parsed_dict = {
            "name": request.POST.get("name"),
            "address": request.POST.get("address"),
            "bedroom": int(request.POST.get("bedroom", 0)),
            "bathroom": int(request.POST.get("bathroom", 0)),
            "size": request.POST.get("size"),
            "about": request.POST.get("about"),
            "latitude": float(request.POST.get("latitude", 0.0)),
            "longitude": float(request.POST.get("longitude", 0.0)),
            "price": float(request.POST.get("price", 0.0)),
            "type": request.POST.get("type"),
            "amenities": json.loads(amenities_raw) if amenities_raw else None,
            "gallery": json.loads(gallery_raw) if gallery_raw else None,
        }
        
        # msgspec ভ্যালিডেশন
        data = msgspec.convert(parsed_dict, CreatePropertySchema)
    except Exception as parse_err:
        raise ValueError(f"Validation/Parsing error: {str(parse_err)}")

    # মেইন প্রোপার্টি অবজেক্ট তৈরি
    cover_file = request.FILES.get("cover")
    property_obj = Property.objects.create(
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

    # নেস্টেড অ্যামেনিটিজ তৈরি
    if data.amenities:
        for amenity in data.amenities:
            Amenity.objects.create(property=property_obj, name=amenity.name)

    # নেস্টেড গ্যালারি ফাইলস তৈরি
    if data.gallery:
        gallery_files = request.FILES.getlist("gallery_files")
        for index, gallery_item in enumerate(data.gallery):
            if index < len(gallery_files):
                Gallery.objects.create(
                    property=property_obj,
                    type=gallery_item.type,
                    file=gallery_files[index]
                )
                
    return property_obj