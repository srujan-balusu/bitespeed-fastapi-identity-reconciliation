from typing import Optional
from pydantic import BaseModel

class ContactRequest(BaseModel):
    email: Optional[str]
    phoneNumber: Optional[str]

class ContactResponse(BaseModel):
    contact: dict