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
    views : int
    favourite : Optional[bool] = None
    amenities : Optional[List[PropertyAmenitySchema]] = None
    gallery: Optional[List[PropertyGallerySchema]] = None
    reviews : Optional[List[ReviewSchema]] = None


class PropertyListSchema(msgspec.Struct):
    id : uuid.UUID
    cover : str
    name : str
    price : float
    address : str
    bathroom : int
    bedroom : int
    size : str
    views : int
    type : str
    average_rating : str
    favourite : Optional[bool] = None


class PropertyListResponse(msgspec.Struct):
    status : int
    message : str
    success : bool
    data : List[PropertyListSchema]

    
class CreatePropertySchema(msgspec.Struct):
    name: str
    address: str
    bedroom: int
    bathroom: int
    size: str
    about: str
    cover: str
    latitude: float
    longitude: float
    price: float
    type: str
    amenities: Optional[List[PropertyAmenitySchema]] = None
    gallery: Optional[List[PropertyGallerySchema]] = None



class AddFavouriteSchema(msgspec.Struct):
    property: uuid.UUID



class FavouriteListResponseSchema(msgspec.Struct):
    status : int
    message : str
    success : bool
    properties : List[PropertyListSchema]



class MyPropertyDetailResponseSchema(msgspec.Struct):
    status : int
    message : str
    success : bool
    occupancy : str
    total_bookings : int
    avg_stay : str
    property : PropertyDetailSchema




class MyPropertyListSchema(msgspec.Struct):
    id : uuid.UUID
    cover : str
    name : str
    address : str
    avg_rating : str


class MyPropertyResponseSchema(msgspec.Struct):
    status : int
    message : str
    success : bool
    properties : List[MyPropertyListSchema]



class UpdatePropertySchema(msgspec.Struct):
    name: Optional[str] = None
    about: Optional[str] = None
    address: Optional[str] = None
    price: Optional[float] = None
    bathroom: Optional[int] = None
    bedroom: Optional[int] = None
    size: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: Optional[List[dict]] = None 
    gallery: Optional[List[dict]] = None