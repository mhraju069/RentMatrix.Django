import msgspec
from typing import Optional,List
from django_bolt import UploadFile


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


class GetOtpSchema(msgspec.Struct):
    email: str


class VerifyOtpSchema(msgspec.Struct):
    email: str
    otp: str


class UpdateUserSchema(msgspec.Struct):
    name: Optional[str] = None
    phone: Optional[str] = None
    image: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None


class ResetPasswordSchema(msgspec.Struct):
    new_password: str



class UploadDocumentSchema(msgspec.Struct):
    type: str
    file: UploadFile
