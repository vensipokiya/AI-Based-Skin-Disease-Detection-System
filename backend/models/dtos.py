from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any

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
    email: EmailStr
    contact_number: Optional[str] = None

class ForgotPasswordVerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class ForgotPasswordResetRequest(BaseModel):
    email: EmailStr
    new_password: str

class ScanSaveRequest(BaseModel):
    disease: str
    confidence: float
    remedies: Dict[str, Any]

class AppointmentRequest(BaseModel):
    doctor_name: str
    doctor_specialty: str
    doctor_area: str
    doctor_city: str
    appointment_date: str
    appointment_time: str
