from typing import List
import msgspec
from datetime import datetime

class DeviceTokenSchema(msgspec.Struct):
    token: str


class NotificationSchema(msgspec.Struct):
    id: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


class NotificationListSchema(msgspec.Struct):
    data: List[NotificationSchema]
    status: int = 200
    message: str = "Notifications fetched successfully"
    success: bool = True
