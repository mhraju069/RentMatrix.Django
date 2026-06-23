from apps.property.models import Property,Amenity,Gallery
from .schema import CreatePropertySchema, UpdatePropertySchema
import msgspec
import json
from django_bolt import UploadFile

def _handle_multipart_property_creation(request):
    # মাল্টিপার্ট ডাটা সিঙ্ক থ্রেডে রিড করা হচ্ছে (সেফ এবং নন-ব্লকিং)
    try:
        # Clean keys from request.form by stripping whitespace/tabs to be robust
        form_data = {k.strip(): v for k, v in request.form.items()} if request.form else {}
        
        amenities_raw = form_data.get("amenities")
        gallery_raw = form_data.get("gallery")
        
        cover_info = request.files.get("cover")
        cover_filename = ""
        if cover_info:
            if isinstance(cover_info, dict):
                cover_filename = cover_info.get("filename", "")
            else:
                cover_filename = getattr(cover_info, "filename", "")
        if not cover_filename:
            cover_filename = form_data.get("cover", "") or ""
        
        parsed_dict = {
            "name": form_data.get("name"),
            "address": form_data.get("address"),
            "bedroom": int(form_data.get("bedroom", 0)),
            "bathroom": int(form_data.get("bathroom", 0)),
            "size": form_data.get("size"),
            "about": form_data.get("about"),
            "cover": cover_filename,
            "latitude": float(form_data.get("latitude", 0.0)),
            "longitude": float(form_data.get("longitude", 0.0)),
            "price": float(form_data.get("price", 0.0)),
            "sea_view": form_data.get("sea_view", "false").lower() in ("true", "1"),
            "type": form_data.get("type"),
            "amenities": json.loads(amenities_raw) if amenities_raw else None,
            "gallery": json.loads(gallery_raw) if gallery_raw else None,
        }
        
        # msgspec ভ্যালিডেশন
        data = msgspec.convert(parsed_dict, CreatePropertySchema)
    except Exception as parse_err:
        raise ValueError(f"Validation/Parsing error: {str(parse_err)}")

    # মেইন প্রোপার্টি অবজেক্ট তৈরি
    cover_info = request.files.get("cover")
    cover_file = UploadFile.from_file_info(cover_info).file if cover_info else None
    
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
    )

    # নেস্টেড অ্যামেনিটিজ তৈরি
    if data.amenities:
        for amenity in data.amenities:
            Amenity.objects.create(property=property_obj, name=amenity.name)

    # নেস্টেড গ্যালারি ফাইলস তৈরি
    if data.gallery:
        gallery_files_raw = request.files.get("gallery_files")
        if gallery_files_raw:
            if isinstance(gallery_files_raw, list):
                gallery_files = [UploadFile.from_file_info(f).file for f in gallery_files_raw]
            else:
                gallery_files = [UploadFile.from_file_info(gallery_files_raw).file]
        else:
            gallery_files = []

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

    # Clean keys from request.form by stripping whitespace/tabs to be robust
    form_data = {k.strip(): v for k, v in request.form.items()} if request.form else {}

    parsed_dict = {}
    field_keys = ["name", "about", "address", "type", "status", "size"]
    int_keys = ["bedroom", "bathroom"]
    float_keys = ["price", "latitude", "longitude"]

    for k in field_keys:
        if k in form_data: parsed_dict[k] = form_data.get(k)
    for k in int_keys:
        if k in form_data: parsed_dict[k] = int(form_data.get(k, 0))
    for k in float_keys:
        if k in form_data: parsed_dict[k] = float(form_data.get(k, 0.0))
    if "sea_view" in form_data:
        parsed_dict["sea_view"] = form_data.get("sea_view").lower() in ("true", "1")

    amenities_raw = form_data.get("amenities")
    gallery_raw = form_data.get("gallery")
    if amenities_raw: parsed_dict["amenities"] = json.loads(amenities_raw)
    if gallery_raw: parsed_dict["gallery"] = json.loads(gallery_raw)

    data = msgspec.convert(parsed_dict, UpdatePropertySchema)

    field_mapping = {
        "name": "name", "about": "about", "address": "address",
        "price": "price", "bathroom": "bathroom", "bedroom": "bedroom",
        "size": "area", "type": "type", "status": "status",
        "sea_view": "sea_view",
        "latitude": "latitude", "longitude": "longitude",
    }

    for schema_key, model_key in field_mapping.items():
        val = getattr(data, schema_key, None)
        if val is not None:
            setattr(property_obj, model_key, val)

    cover_info = request.files.get("cover")
    if cover_info:
        property_obj.cover_image = UploadFile.from_file_info(cover_info).file

    property_obj.save()

    if data.amenities is not None:
        Amenity.objects.filter(property=property_obj).delete()
        for amenity_data in data.amenities:
            Amenity.objects.create(property=property_obj, name=amenity_data.get("name"))

    if data.gallery is not None:
        Gallery.objects.filter(property=property_obj).delete()
        
        gallery_files_raw = request.files.get("gallery_files")
        if gallery_files_raw:
            if isinstance(gallery_files_raw, list):
                gallery_files = [UploadFile.from_file_info(f).file for f in gallery_files_raw]
            else:
                gallery_files = [UploadFile.from_file_info(gallery_files_raw).file]
        else:
            gallery_files = []
        
        for index, gallery_item in enumerate(data.gallery):
            if index < len(gallery_files):
                Gallery.objects.create(
                    property=property_obj,
                    type=gallery_item.get("type", "BEDROOM"),
                    file=gallery_files[index]
                )

    return property_obj