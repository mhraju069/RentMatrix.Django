import msgspec
from typing import Optional,List


class CreateUserSchema(msgspec.Struct):
    email : str
    password : str
    phone : str
    name : str
    role : str


class UserDataSchema(msgspec.Struct):
    email : str
    role : str
    name : str
    phone : str
    image : Optional[str] = None


class UserDataResponseSchema(msgspec.Struct):
    message:str
    status: int
    success: bool
    user: UserDataSchema
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    

class LoginUserSchema(msgspec.Struct):
    password : str
    email : Optional[str] = None
    phone : Optional[str] = None


class RefreshRequestSchema(msgspec.Struct):
    refresh_token: str


class TokenResponseSchema(msgspec.Struct):
    message: str
    status: int
    success: bool
    access_token: str
    refresh_token: Optional[str] = None