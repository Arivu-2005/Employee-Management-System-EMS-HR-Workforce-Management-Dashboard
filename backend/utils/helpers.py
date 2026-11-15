from functools import wraps
from flask import request, jsonify, session
from bson import ObjectId
from datetime import datetime
import secrets

def json_response(data=None, message="", status=200, success=True, errors=None):
    payload = {
        "success": success,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    if errors is not None:
        payload["errors"] = errors
    return jsonify(payload), status

def serialize_doc(doc):
    if not doc:
        return None
    res = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            res[k] = str(v)
        elif isinstance(v, datetime):
            res[k] = v.isoformat()
        elif isinstance(v, dict):
            res[k] = serialize_doc(v)
        elif isinstance(v, list):
            res[k] = [serialize_doc(item) if isinstance(item, dict) else (str(item) if isinstance(item, ObjectId) else item) for item in v]
        else:
            res[k] = v
    return res

def serialize_docs(docs):
    return [serialize_doc(d) for d in docs]

def generate_employee_id(db):
    """Generate next sequential employee id like EMP-1001"""
    last_emp = db.employees.find_one(sort=[("employee_id", -1)])
    if last_emp and "employee_id" in last_emp and last_emp["employee_id"].startswith("EMP-"):
        try:
            num = int(last_emp["employee_id"].replace("EMP-", "")) + 1
            return f"EMP-{num:04d}"
        except ValueError:
            pass
    count = db.employees.count_documents({}) + 1001
    return f"EMP-{count:04d}"

def log_activity(db, action, details, admin_email="admin@ems.com", admin_name="System Admin"):
    try:
        activity = {
            "action": action,
            "details": details,
            "admin_email": admin_email,
            "admin_name": admin_name,
            "ip_address": request.remote_addr if request else "127.0.0.1",
            "created_at": datetime.utcnow()
        }
        db.activities.insert_one(activity)
    except Exception as e:
        print(f"Error logging activity: {e}")

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Support session or Authorization Bearer header
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1].strip()

        is_authenticated = False
        user_info = None

        if token:
            from database import get_db
            db = get_db()
            admin = db.admins.find_one({"token": token})
            if admin:
                is_authenticated = True
                user_info = admin

        if not is_authenticated and session.get("admin_logged_in"):
            is_authenticated = True
            user_info = {
                "email": session.get("admin_email"),
                "name": session.get("admin_name"),
                "role": session.get("admin_role", "admin")
            }

        if not is_authenticated:
            return json_response(None, "Unauthorized: Authentication required", status=401, success=False)

        # Attach admin info to request
        request.current_admin = user_info
        return f(*args, **kwargs)
    return decorated
