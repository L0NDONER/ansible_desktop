import os

# Base Paths
BASE_DIR = os.path.expanduser('~/ansible')
INVENTORY_PATH = os.path.join(BASE_DIR, 'inventory')
VAULT_PASS_FILE = os.path.join(BASE_DIR, '.vault_pass')

# Import secrets from local file (gitignored) or fall back to environment variables
try:
    from .secrets import WEATHER_API_KEY, CITY_NAME, ALLOWED_NUMBERS
except ImportError:
    # Fallback to environment variables if secrets.py doesn't exist
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
    CITY_NAME = os.getenv('CITY_NAME', 'Dereham,GB')
    ALLOWED_NUMBERS = os.getenv('ALLOWED_WHATSAPP_NUMBERS', '').split(',')

# Twilio credentials (always from environment for security)
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')

