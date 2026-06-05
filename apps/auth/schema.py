import msgspec
from typing import Optional,List


class CreateUserSchema(msgspec.Struct):
    email : str
    password : str
    phone : str
    name : str



class UserDataSchema(msgspec.Struct):
    email : str
    role : str
    name : str
    phone : str
    image : Optional[str] = None


class SignupResponseSchema(msgspec.Struct):
    message:str
    status: int
    success: bool
    user: UserDataSchema
    