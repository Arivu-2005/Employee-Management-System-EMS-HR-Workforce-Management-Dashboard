import re
from datetime import datetime

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
PHONE_REGEX = r'^\+?[0-9\s\-()]{7,20}$'

def validate_email(email):
    if not email or not isinstance(email, str):
        return False
    return bool(re.match(EMAIL_REGEX, email.strip()))

def validate_phone(phone):
    if not phone or not isinstance(phone, str):
        return False
    return bool(re.match(PHONE_REGEX, phone.strip()))

def validate_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str.strip(), '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_required_fields(data, required_fields):
    missing = []
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing.append(field)
    return missing
