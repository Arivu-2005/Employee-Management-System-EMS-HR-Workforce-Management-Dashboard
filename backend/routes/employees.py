import os
import uuid
from flask import Blueprint, request
from bson import ObjectId
from datetime import datetime
from config import Config
from database import get_db
from utils.helpers import json_response, serialize_doc, serialize_docs, generate_employee_id, log_activity, auth_required
from utils.validators import validate_email, validate_required_fields

employees_bp = Blueprint('employees', __name__, url_prefix='/api/employees')

@employees_bp.route('/upload-photo', methods=['POST'])
@auth_required
def upload_photo():
    if 'photo' not in request.files:
        return json_response(None, "No photo file provided", status=400, success=False)

    file = request.files['photo']
    if file.filename == '':
        return json_response(None, "No selected file", status=400, success=False)

    allowed_exts = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_exts:
        return json_response(None, f"Invalid image format. Allowed: {', '.join(allowed_exts)}", status=400, success=False)

    filename = f"avatar_{uuid.uuid4().hex[:12]}.{ext}"
    upload_dir = Config.UPLOAD_FOLDER
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, filename)
    file.save(save_path)

    photo_url = f"/uploads/{filename}"
    return json_response({"url": photo_url}, "Photo uploaded successfully", status=200)

@employees_bp.route('', methods=['GET'])
@auth_required
def list_employees():
    db = get_db()
    query = {}

    search = request.args.get('search', '').strip()
    department = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()
    emp_type = request.args.get('type', '').strip()

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"employee_id": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"designation": {"$regex": search, "$options": "i"}}
        ]
    if department and department != 'All':
        query["department"] = department
    if status and status != 'All':
        query["status"] = status
    if emp_type and emp_type != 'All':
        query["employment_type"] = emp_type

    page = max(1, int(request.args.get('page', 1)))
    limit = max(1, min(100, int(request.args.get('limit', 10))))
    skip = (page - 1) * limit

    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = -1 if request.args.get('sort_dir', 'desc').lower() == 'desc' else 1

    total = db.employees.count_documents(query)
    cursor = db.employees.find(query).sort([(sort_by, sort_dir)]).skip(skip).limit(limit)
    employees = serialize_docs(cursor)

    return json_response({
        "employees": employees,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 1
        }
    }, "Employees retrieved successfully")

@employees_bp.route('/<emp_id>', methods=['GET'])
@auth_required
def get_employee(emp_id):
    db = get_db()
    query = {"$or": [{"employee_id": emp_id}]}
    if ObjectId.is_valid(emp_id):
        query["$or"].append({"_id": ObjectId(emp_id)})

    employee = db.employees.find_one(query)
    if not employee:
        return json_response(None, "Employee not found", status=404, success=False)

    e_id = employee.get("employee_id")
    recent_attendance = serialize_docs(db.attendance.find({"employee_id": e_id}).sort([("date", -1)]).limit(5))
    recent_leaves = serialize_docs(db.leaves.find({"employee_id": e_id}).sort([("applied_at", -1)]).limit(5))
    recent_reviews = serialize_docs(db.performance_reviews.find({"employee_id": e_id}).sort([("review_date", -1)]).limit(5))
    recent_payroll = serialize_docs(db.payroll.find({"employee_id": e_id}).sort([("year", -1), ("created_at", -1)]).limit(6))

    emp_data = serialize_doc(employee)
    emp_data["attendance_history"] = recent_attendance
    emp_data["leave_history"] = recent_leaves
    emp_data["performance_history"] = recent_reviews
    emp_data["payroll_history"] = recent_payroll

    return json_response(emp_data, "Employee details retrieved")

@employees_bp.route('', methods=['POST'])
@auth_required
def create_employee():
    db = get_db()
    data = request.get_json() or {}

    required = ['first_name', 'last_name', 'email', 'department', 'designation']
    missing = validate_required_fields(data, required)
    if missing:
        return json_response(None, f"Missing required fields: {', '.join(missing)}", status=400, success=False)

    email = data['email'].strip().lower()
    if not validate_email(email):
        return json_response(None, "Invalid email address format", status=400, success=False)

    if db.employees.find_one({"email": email}):
        return json_response(None, f"An employee with email '{email}' already exists", status=409, success=False)

    emp_id = data.get('employee_id')
    if emp_id:
        emp_id = emp_id.strip().upper()
        if db.employees.find_one({"employee_id": emp_id}):
            return json_response(None, f"Employee ID '{emp_id}' is already taken", status=409, success=False)
    else:
        emp_id = generate_employee_id(db)

    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    full_name = f"{first_name} {last_name}".strip()

    # Salary calculation
    basic = float(data.get('basic_salary', 0) or 0)
    hra = float(data.get('hra', 0) or 0)
    allowances = float(data.get('allowances', 0) or 0)
    deductions = float(data.get('deductions', 0) or 0)
    gross = basic + hra + allowances
    net = max(0, gross - deductions)

    new_emp = {
        "employee_id": emp_id,
        "first_name": first_name,
        "last_name": last_name,
        "name": full_name,
        "email": email,
        "phone": data.get('phone', '').strip(),
        "gender": data.get('gender', 'Male'),
        "dob": data.get('dob', ''),
        "address": data.get('address', '').strip(),
        "department": data.get('department', '').strip(),
        "designation": data.get('designation', '').strip(),
        "employment_type": data.get('employment_type', 'Full-Time'),
        "joining_date": data.get('joining_date', datetime.utcnow().strftime("%Y-%m-%d")),
        "status": data.get('status', 'Active'),
        "avatar": data.get('avatar') or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=300&q=80",
        "salary": {
            "basic": basic,
            "hra": hra,
            "allowances": allowances,
            "deductions": deductions,
            "gross": gross,
            "net": net
        },
        "leave_balance": {
            "casual": int(data.get('casual_leaves', 12)),
            "sick": int(data.get('sick_leaves', 10)),
            "earned": int(data.get('earned_leaves', 15))
        },
        "created_at": datetime.utcnow()
    }

    result = db.employees.insert_one(new_emp)
    new_emp["_id"] = result.inserted_id

    log_activity(db, "Employee Created", f"Added new employee {full_name} ({emp_id})")

    return json_response(serialize_doc(new_emp), "Employee created successfully", status=201)

@employees_bp.route('/<emp_id>', methods=['PUT'])
@auth_required
def update_employee(emp_id):
    db = get_db()
    query = {"$or": [{"employee_id": emp_id}]}
    if ObjectId.is_valid(emp_id):
        query["$or"].append({"_id": ObjectId(emp_id)})

    existing = db.employees.find_one(query)
    if not existing:
        return json_response(None, "Employee not found", status=404, success=False)

    data = request.get_json() or {}
    update_data = {}

    if 'first_name' in data or 'last_name' in data:
        fn = data.get('first_name', existing.get('first_name', '')).strip()
        ln = data.get('last_name', existing.get('last_name', '')).strip()
        update_data['first_name'] = fn
        update_data['last_name'] = ln
        update_data['name'] = f"{fn} {ln}".strip()

    if 'email' in data:
        email = data['email'].strip().lower()
        if not validate_email(email):
            return json_response(None, "Invalid email address format", status=400, success=False)
        duplicate = db.employees.find_one({"email": email, "employee_id": {"$ne": existing["employee_id"]}})
        if duplicate:
            return json_response(None, "Email already in use by another employee", status=409, success=False)
        update_data['email'] = email

    for field in ['phone', 'gender', 'dob', 'address', 'department', 'designation', 'employment_type', 'joining_date', 'status', 'avatar']:
        if field in data:
            update_data[field] = data[field]

    # Salary update
    if any(k in data for k in ['basic_salary', 'hra', 'allowances', 'deductions', 'salary']):
        cur_sal = existing.get('salary', {})
        sal_in = data.get('salary', {})
        basic = float(data.get('basic_salary', sal_in.get('basic', cur_sal.get('basic', 0))) or 0)
        hra = float(data.get('hra', sal_in.get('hra', cur_sal.get('hra', 0))) or 0)
        allowances = float(data.get('allowances', sal_in.get('allowances', cur_sal.get('allowances', 0))) or 0)
        deductions = float(data.get('deductions', sal_in.get('deductions', cur_sal.get('deductions', 0))) or 0)
        gross = basic + hra + allowances
        net = max(0, gross - deductions)
        update_data['salary'] = {
            "basic": basic,
            "hra": hra,
            "allowances": allowances,
            "deductions": deductions,
            "gross": gross,
            "net": net
        }

    # Leave balance update if provided
    if 'leave_balance' in data:
        update_data['leave_balance'] = data['leave_balance']

    update_data['updated_at'] = datetime.utcnow()
    db.employees.update_one({"_id": existing["_id"]}, {"$set": update_data})

    updated = db.employees.find_one({"_id": existing["_id"]})
    log_activity(db, "Employee Updated", f"Updated details for {existing.get('name')} ({existing.get('employee_id')})")

    return json_response(serialize_doc(updated), "Employee updated successfully")

@employees_bp.route('/<emp_id>', methods=['DELETE'])
@auth_required
def delete_employee(emp_id):
    db = get_db()
    query = {"$or": [{"employee_id": emp_id}]}
    if ObjectId.is_valid(emp_id):
        query["$or"].append({"_id": ObjectId(emp_id)})

    employee = db.employees.find_one(query)
    if not employee:
        return json_response(None, "Employee not found", status=404, success=False)

    actual_id = employee.get("employee_id")
    # Delete employee
    db.employees.delete_one({"_id": employee["_id"]})
    # Clean up or keep related records safe
    db.attendance.delete_many({"employee_id": actual_id})
    db.leaves.delete_many({"employee_id": actual_id})
    db.payroll.delete_many({"employee_id": actual_id})
    db.performance_reviews.delete_many({"employee_id": actual_id})

    log_activity(db, "Employee Deleted", f"Removed employee {employee.get('name')} ({actual_id}) and associated records")

    return json_response(None, f"Employee {actual_id} deleted successfully")
