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
            "sea_view": request.POST.get("sea_view", "false").lower() in ("true", "1"),
            "type": request.POST.get("type"),
            "check_in": request.POST.get("check_in") or None,
            "check_out": request.POST.get("check_out") or None,
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
        sea_view=data.sea_view,
        type=data.type,
        check_in=data.check_in,
        check_out=data.check_out,
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




def _handle_multipart_property_update(request, property_id):
    try:
        property_obj = Property.objects.get(id=property_id, owner=request.user)
    except Property.DoesNotExist:
        raise KeyError("Property not found or unauthorized")

    parsed_dict = {}
    field_keys = ["name", "about", "address", "type", "status", "size", "check_in", "check_out"]
    int_keys = ["bedroom", "bathroom"]
    float_keys = ["price", "latitude", "longitude"]

    for k in field_keys:
        if k in request.POST: parsed_dict[k] = request.POST.get(k) or None
    for k in int_keys:
        if k in request.POST: parsed_dict[k] = int(request.POST.get(k, 0))
    for k in float_keys:
        if k in request.POST: parsed_dict[k] = float(request.POST.get(k, 0.0))
    if "sea_view" in request.POST:
        parsed_dict["sea_view"] = request.POST.get("sea_view").lower() in ("true", "1")

    amenities_raw = request.POST.get("amenities")
    gallery_raw = request.POST.get("gallery")
    if amenities_raw: parsed_dict["amenities"] = json.loads(amenities_raw)
    if gallery_raw: parsed_dict["gallery"] = json.loads(gallery_raw)

    data = msgspec.convert(parsed_dict, UpdatePropertySchema)

    field_mapping = {
        "name": "name", "about": "about", "address": "address",
        "price": "price", "bathroom": "bathroom", "bedroom": "bedroom",
        "size": "area", "type": "type", "status": "status",
        "sea_view": "sea_view",
        "check_in": "check_in", "check_out": "check_out",
        "latitude": "latitude", "longitude": "longitude",
    }

    for schema_key, model_key in field_mapping.items():
        val = getattr(data, schema_key, None)
        if val is not None:
            setattr(property_obj, model_key, val)

    uploaded_cover = request.FILES.get("cover")
    if uploaded_cover:
        property_obj.cover_image = uploaded_cover

    property_obj.save()

    if data.amenities is not None:
        Amenity.objects.filter(property=property_obj).delete()
        for amenity_data in data.amenities:
            Amenity.objects.create(property=property_obj, name=amenity_data.get("name"))

    if data.gallery is not None:
        Gallery.objects.filter(property=property_obj).delete()
        gallery_files = request.FILES.getlist("gallery_files")
        
        for index, gallery_item in enumerate(data.gallery):
            if index < len(gallery_files):
                Gallery.objects.create(
                    property=property_obj,
                    type=gallery_item.get("type", "BEDROOM"),
                    file=gallery_files[index]
                )

    return property_obj