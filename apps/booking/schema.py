import msgspec
from typing import List, Optional
from datetime import date
from uuid import UUID


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
