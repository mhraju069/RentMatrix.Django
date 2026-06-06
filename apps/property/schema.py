import msgspec, uuid
from typing import Optional,List

class UserSchema(msgspec.Struct):
    name: str
    image: Optional[str] = None


class PropertyGallerySchema(msgspec.Struct):
    type: str
    file: str


class PropertyAmenitySchema(msgspec.Struct):
    name: str


class ReviewSchema(msgspec.Struct):
    rating: float
    review: str
    user: UserSchema
    created_at: str


class GetPropertySchema(msgspec.Struct):
    id: uuid.UUID


class PropertyDetailSchema(msgspec.Struct):
    name: str
    about: str
    cover: str
    price: float
    owner: UserSchema
    bathroom: int
    bedroom: int
    size: str
    type : str
    status: str
    verified: bool
    review_count: str
    average_rating : str
    address : str
    latitude : float
    longitude : float
    amenities : Optional[List[PropertyAmenitySchema]] = None
    gallery: Optional[List[PropertyGallerySchema]] = None
    reviews : Optional[List[ReviewSchema]] = None


# class PropertyListSchema(msgspec.Struct):
    
