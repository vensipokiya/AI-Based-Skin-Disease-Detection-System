# DermaCare AI - Intelligent Skin Disease Detection System

DermaCare AI is a full-stack health-tech application designed to analyze skin condition images using deep learning (EfficientNetV2) and provide preliminary diagnostic insights. It features a secure administrative dashboard for patient and system management.

## 🚀 Key Features

- **AI-Powered Analysis**: High-accuracy skin disease detection using Keras/TensorFlow.
- **Secure Authentication**: JWT-based login system for patients and administrators.
- **Admin Dashboard**: Real-time MySQL data visualization for user management.
- **Nearby Dermatologists**: Integration with mapping services to find local medical help.
- **Responsive Design**: Premium UI/UX built with Vanilla CSS and modern JavaScript.

## 🏗️ Technical Architecture

### Backend (Python/FastAPI)
- **FastAPI**: High-performance web framework for APIs.
- **MySQL**: Relational database for persistent storage (Users, Medical Profiles, Scans).
- **Deep Learning**: EfficientNetV2 model (.h5) for image classification.
- **Security**: JWT-based authorization and Bcrypt password hashing.

### Frontend (HTML/CSS/JS)
- **Vanilla CSS**: Premium, dark-mode inspired aesthetic with glassmorphism.
- **JavaScript**: Async/Await patterns for real-time backend communication.
- **Canvas API**: Integrated camera support for live disease scanning.

## 🔑 Administrative Access

The system includes a restricted **Admin Panel** accessible via:
- **URL**: `admin.html` (Requires Authentication)
- **Default Credentials**: `admin@gmail.com` / `Admin@1234`
- **Capabilities**:
    - Real-time user management (Live MySQL fetching).
    - View patient Age, Date of Birth, and Contact details.
    - **Live Session Tracking**: Monitor Online/Offline status of patients.
    - Secure account deletion and management.

## 📂 Project Structure

```text
├── backend/
│   ├── api/routes/      # FastAPI Routers (Admin, Auth, Predict)
│   ├── core/            # Security, Logging, and Configuration
│   ├── dao/             # Data Access Objects (MySQL queries)
│   ├── db/              # Database connection singleton
│   └── models/          # TensorFlow/Keras .h5 files
├── frontend/
│   ├── css/             # Modern styling system
│   ├── js/              # Application logic and API handlers
│   ├── admin.html       # Management Dashboard
│   ├── detection.html   # AI Scanner Interface
│   └── login.html       # Secure Login Page
└── README.md
```

## 🛠️ Installation & Setup

1. **Database**: Import the provided MySQL schema.
2. **Environment**: Install dependencies: `pip install fastapi uvicorn mysql-connector-python tensorflow authlib`.
3. **Run Backend**: `python -m uvicorn main:app --reload`.
4. **Access UI**: Open `frontend/login.html` in any modern browser.

---
*Disclaimer: This tool is for educational purposes and preliminary screening. Always consult a certified dermatologist for medical diagnosis.*
