from enum import Enum

class MessageEnum(Enum):
    SUCCESS_LOGIN = "Login successful"
    SUCCESS_LOGOUT = "Logout successful"
    SUCCESS_PASSWORD_UPDATED = "Password updated successfully"
    SUCCESS_USER_CREATED = "User created successfully"
    
    ERROR_INVALID_CREDENTIALS = "Invalid email or password"
    ERROR_EMAIL_EXISTS = "Email already exists"
    ERROR_USER_NOT_FOUND = "User not found"
    ERROR_UNAUTHORIZED = "Unauthorized access"
    ERROR_DB_CONNECTION = "Database connection error"
    ERROR_INVALID_OTP = "Invalid or expired OTP"
    ERROR_INTERNAL_SERVER = "An internal server error occurred"
