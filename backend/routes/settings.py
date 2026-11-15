from flask import Blueprint, request
from datetime import datetime
from database import get_db, reset_demo_data
from utils.helpers import json_response, serialize_doc, log_activity, auth_required

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

@settings_bp.route('', methods=['GET'])
@auth_required
def get_settings():
    db = get_db()
    settings = db.settings.find_one()
    if not settings:
        settings = {
            "company_name": "Apex Enterprise Solutions",
            "company_email": "contact@apexenterprise.io",
            "company_phone": "+1 (800) 555-0199",
            "company_address": "100 Tech Boulevard, Suite 500, San Francisco, CA 94107",
            "company_website": "https://apexenterprise.io",
            "currency": "USD",
            "currency_symbol": "$",
            "fiscal_year_start": "January",
            "casual_leaves_allowed": 12,
            "sick_leaves_allowed": 10,
            "earned_leaves_allowed": 15,
            "work_hours_per_day": 8,
            "updated_at": datetime.utcnow()
        }
        db.settings.insert_one(settings)

    return json_response(serialize_doc(settings), "Settings retrieved successfully")

@settings_bp.route('', methods=['PUT'])
@auth_required
def update_settings():
    db = get_db()
    data = request.get_json() or {}

    update_fields = {}
    allowed_fields = [
        'company_name', 'company_email', 'company_phone', 'company_address',
        'company_website', 'currency', 'currency_symbol', 'fiscal_year_start',
        'casual_leaves_allowed', 'sick_leaves_allowed', 'earned_leaves_allowed',
        'work_hours_per_day', 'company_logo'
    ]

    for field in allowed_fields:
        if field in data:
            if field in ['casual_leaves_allowed', 'sick_leaves_allowed', 'earned_leaves_allowed', 'work_hours_per_day']:
                try:
                    update_fields[field] = int(data[field])
                except (ValueError, TypeError):
                    pass
            else:
                update_fields[field] = str(data[field]).strip()

    update_fields['updated_at'] = datetime.utcnow()
    db.settings.update_one({}, {"$set": update_fields}, upsert=True)

    settings = db.settings.find_one()
    admin_name = request.current_admin.get("name", "Admin") if hasattr(request, "current_admin") else "Admin"
    log_activity(db, "Settings Updated", f"Company configuration updated by {admin_name}")

    return json_response(serialize_doc(settings), "Settings updated successfully")

@settings_bp.route('/reset-demo-data', methods=['POST'])
@auth_required
def reset_data():
    db = get_db()
    reset_demo_data(db)
    admin_name = request.current_admin.get("name", "Admin") if hasattr(request, "current_admin") else "Admin"
    log_activity(db, "Reset Demo Data", f"Entire system demo data reset to default by {admin_name}")
    return json_response(None, "System reset to default demo dataset successfully")
