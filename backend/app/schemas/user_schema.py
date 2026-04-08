from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    contact_number: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    symptoms: str
    symptom_duration: str
    previous_conditions: str
    previous_condition_details: Optional[str] = ""

class ForgotPasswordSendOtpRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class ForgotPasswordVerifyOtpRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    otp: str

class ForgotPasswordResetRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str

class UserProfileResponse(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    contact_number: Optional[str]
    gender: Optional[str]
    age: Optional[int]
    user_location: Optional[str]
