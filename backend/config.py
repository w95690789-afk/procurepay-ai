import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class Settings:
    PAYPAL_ENV = os.getenv('PAYPAL_ENV', 'sandbox')
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
    PAYPAL_API_BASE = os.getenv('PAYPAL_API_BASE', 'https://api-m.sandbox.paypal.com')
    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    
    PORT = int(os.getenv('PORT', 8000))
    AUTO_APPROVAL_THRESHOLD_USD = float(os.getenv('AUTO_APPROVAL_THRESHOLD_USD', 500.0))
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')

settings = Settings()
