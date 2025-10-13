import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Timezone configuration
TIMEZONE = os.getenv('TIMEZONE', 'America/New_York')

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Security
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')

# Flask configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Confirmation timeout (in seconds)
CONFIRMATION_TIMEOUT = int(os.getenv('CONFIRMATION_TIMEOUT', '300'))

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Validate required configuration
def validate_config():
    """Validate that all required configuration is present"""
    errors = []
    
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is not set in .env file")
    
    if errors:
        print("\n❌ Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your .env file and try again.\n")
        return False
    
    return True
