import secrets
from flask import Blueprint, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from utils.helpers import json_response, serialize_doc, log_activity, auth_required
from utils.validators import validate_email, validate_required_fields

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember_me = bool(data.get('remember_me', False))

    if not email or not password:
        return json_response(None, "Email and password are required", status=400, success=False)

    db = get_db()
    admin = db.admins.find_one({"email": email})

    if not admin or not check_password_hash(admin.get('password', ''), password):
        return json_response(None, "Invalid email or password", status=401, success=False)

    token = secrets.token_hex(32)
    db.admins.update_one({"_id": admin["_id"]}, {"$set": {"token": token, "last_login": admin.get("current_login")}})
    
    session['admin_logged_in'] = True
    session['admin_email'] = admin['email']
    session['admin_name'] = admin['name']
    session['admin_role'] = admin.get('role', 'Super Admin')
    session.permanent = remember_me

    log_activity(db, "Admin Login", f"Successful login by {admin['name']} ({email})", email, admin['name'])

    user_data = serialize_doc(admin)
    if "password" in user_data:
        del user_data["password"]
    user_data["token"] = token

    return json_response(user_data, "Login successful", status=200)

@auth_bp.route('/logout', methods=['POST'])
def logout():
    db = get_db()
    admin_email = session.get('admin_email', 'admin@ems.com')
    admin_name = session.get('admin_name', 'Admin')

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
        db.admins.update_one({"token": token}, {"$unset": {"token": ""}})

    session.clear()
    log_activity(db, "Admin Logout", f"Admin {admin_name} logged out", admin_email, admin_name)

    return json_response(None, "Logged out successfully", status=200)

@auth_bp.route('/profile', methods=['GET'])
@auth_required
def get_profile():
    admin = request.current_admin
    user_data = serialize_doc(admin)
    if "password" in user_data:
        del user_data["password"]
    return json_response(user_data, "Profile retrieved", status=200)

@auth_bp.route('/profile', methods=['PUT'])
@auth_required
def update_profile():
    data = request.get_json() or {}
    db = get_db()
    current_admin = request.current_admin
    email = current_admin.get('email')

    update_fields = {}
    if 'name' in data and data['name'].strip():
        update_fields['name'] = data['name'].strip()
        session['admin_name'] = data['name'].strip()
    if 'phone' in data:
        update_fields['phone'] = data['phone'].strip()
    if 'avatar' in data:
        update_fields['avatar'] = data['avatar'].strip()

    if not update_fields:
        return json_response(None, "No valid fields provided for update", status=400, success=False)

    db.admins.update_one({"email": email}, {"$set": update_fields})
    updated_admin = db.admins.find_one({"email": email})
    log_activity(db, "Profile Updated", f"Admin profile details updated for {email}", email, session.get('admin_name', 'Admin'))

    res_data = serialize_doc(updated_admin)
    if "password" in res_data:
        del res_data["password"]
    return json_response(res_data, "Profile updated successfully", status=200)

@auth_bp.route('/change-password', methods=['PUT'])
@auth_required
def change_password():
    data = request.get_json() or {}
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')

    if not current_pw or not new_pw:
        return json_response(None, "Both current and new password are required", status=400, success=False)

    if len(new_pw) < 6:
        return json_response(None, "New password must be at least 6 characters", status=400, success=False)

    db = get_db()
    current_admin = request.current_admin
    email = current_admin.get('email')
    admin_doc = db.admins.find_one({"email": email})

    if not admin_doc or not check_password_hash(admin_doc.get('password', ''), current_pw):
        return json_response(None, "Current password is incorrect", status=400, success=False)

    new_hash = generate_password_hash(new_pw)
    db.admins.update_one({"email": email}, {"$set": {"password": new_hash}})
    log_activity(db, "Password Changed", f"Security credential updated for {email}", email, admin_doc.get('name', 'Admin'))

    return json_response(None, "Password changed successfully", status=200)
