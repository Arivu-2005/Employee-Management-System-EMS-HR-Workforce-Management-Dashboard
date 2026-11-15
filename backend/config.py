import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ems-super-secret-key-change-in-production-2026')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/ems_db')
    DB_NAME = os.environ.get('DB_NAME', 'ems_db')
    CORS_ORIGIN = os.environ.get('CORS_ORIGIN', '*')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    DEBUG = os.environ.get('FLASK_ENV', 'development') == 'development'
