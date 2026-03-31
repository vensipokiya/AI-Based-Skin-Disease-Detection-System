const MessageEnum = Object.freeze({
    SUCCESS_LOGIN: "Login successful",
    SUCCESS_REGISTER: "Registration successful",
    SUCCESS_PASSWORD_UPDATE: "Password updated successfully",
    ERROR_UNAUTHORIZED: "Unauthorized access",
    ERROR_INVALID_CREDENTIALS: "Email or password incorrect",
    ERROR_USER_NOT_FOUND: "User not found",
    ERROR_EMAIL_EXISTS: "Email already registered",
    ERROR_INTERNAL: "Internal server error"
});

const ApiErrorCode = Object.freeze({
    UNAUTHORIZED: 401,
    NOT_FOUND: 404,
    BAD_REQUEST: 400,
    INTERNAL_SERVER_ERROR: 500
});

const AppConstants = Object.freeze({
    API_URL: "http://localhost:8000/api",
    TOKEN_KEY: "dermacare_token",
    REFRESH_TOKEN_KEY: "dermacare_refresh_token",
    USER_KEY: "dermacare_user"
});

const MLClassEnum = Object.freeze({
    ACNE: "Acne",
    BENIGN: "Benign",
    ECZEMA: "Eczema",
    MALIGNANT: "Malignant",
    NORMAL: "Normal",
    PSORIASIS: "Psoriasis",
    VITILIGO: "Vitiligo",
    NON_ACNE: "Non-Acne"
});
