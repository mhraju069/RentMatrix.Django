import msgspec
from typing import List, Optional
from datetime import date
from uuid import UUID
from apps.property.schema import PropertyListSchema, PropertyDetailSchema
from apps.auth.schema import UserDataSchema


class CreateBookingSchema(msgspec.Struct):
    property_id: UUID
    name: str
    phone: str
    email: str
    start_date: date
    end_date: date
    num_guests: int



class ConfirmBookingSchema(msgspec.Struct):
    payment_method_id: str



class BookingListSchema(msgspec.Struct):
    id: UUID
    property: PropertyListSchema
    name: str
    phone: str
    email: str
    guest_count: int
    check_in: str
    check_out: str
    price: float
    status: str



class BookingListResponseSchema(msgspec.Struct):
    status : int
    message : str
    success : bool
    data : List[BookingListSchema]



class BookingDetailsSchema(msgspec.Struct):
    id: UUID
    property: PropertyListSchema
    owner: UserDataSchema
    name: str
    phone: str
    email: str
    guest_count: int
    check_in: str
    check_out: str
    price: float
    status: str
    created_at: str
    updated_at: str



class BookingDetailsResponseSchema(msgspec.Struct):
    status : int
    message : str
    success : bool
    data : BookingDetailsSchema
    docs: Optional[List]


class MyBookingListResponseSchema(msgspec.Struct):
    status : int
    message : str
    success : bool
    count : int
    data : List