from flask import Blueprint, request
from bson import ObjectId
from datetime import datetime
from database import get_db
from utils.helpers import json_response, serialize_doc, serialize_docs, log_activity, auth_required
from utils.validators import validate_required_fields

departments_bp = Blueprint('departments', __name__, url_prefix='/api/departments')

@departments_bp.route('', methods=['GET'])
@auth_required
def list_departments():
    db = get_db()
    departments = serialize_docs(db.departments.find().sort([("name", 1)]))

    # Enrich each department with current employee count and status breakdown
    for dept in departments:
        name = dept.get("name")
        emp_count = db.employees.count_documents({"department": name})
        active_count = db.employees.count_documents({"department": name, "status": "Active"})
        on_leave_count = db.employees.count_documents({"department": name, "status": "On Leave"})
        dept["employee_count"] = emp_count
        dept["active_count"] = active_count
        dept["on_leave_count"] = on_leave_count

    return json_response(departments, "Departments retrieved successfully")

@departments_bp.route('/<dept_id>', methods=['GET'])
@auth_required
def get_department(dept_id):
    db = get_db()
    query = {"$or": [{"name": dept_id}]}
    if ObjectId.is_valid(dept_id):
        query["$or"].append({"_id": ObjectId(dept_id)})

    dept = db.departments.find_one(query)
    if not dept:
        return json_response(None, "Department not found", status=404, success=False)

    data = serialize_doc(dept)
    name = data.get("name")
    data["employees"] = serialize_docs(db.employees.find({"department": name}))
    data["employee_count"] = len(data["employees"])
    return json_response(data, "Department retrieved successfully")

@departments_bp.route('', methods=['POST'])
@auth_required
def create_department():
    db = get_db()
    data = request.get_json() or {}

    missing = validate_required_fields(data, ['name'])
    if missing:
        return json_response(None, "Department name is required", status=400, success=False)

    name = data['name'].strip()
    if db.departments.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}}):
        return json_response(None, f"Department '{name}' already exists", status=409, success=False)

    dept = {
        "name": name,
        "description": data.get('description', '').strip(),
        "manager_name": data.get('manager_name', '').strip(),
        "created_at": datetime.utcnow()
    }
    result = db.departments.insert_one(dept)
    dept["_id"] = result.inserted_id
    dept["employee_count"] = 0

    log_activity(db, "Department Created", f"Created department '{name}'")
    return json_response(serialize_doc(dept), "Department created successfully", status=201)

@departments_bp.route('/<dept_id>', methods=['PUT'])
@auth_required
def update_department(dept_id):
    db = get_db()
    query = {}
    if ObjectId.is_valid(dept_id):
        query["_id"] = ObjectId(dept_id)
    else:
        query["name"] = dept_id

    existing = db.departments.find_one(query)
    if not existing:
        return json_response(None, "Department not found", status=404, success=False)

    data = request.get_json() or {}
    update_data = {}

    old_name = existing.get("name")
    new_name = data.get('name', '').strip()

    if new_name and new_name.lower() != old_name.lower():
        duplicate = db.departments.find_one({"name": {"$regex": f"^{new_name}$", "$options": "i"}, "_id": {"$ne": existing["_id"]}})
        if duplicate:
            return json_response(None, f"Department '{new_name}' already exists", status=409, success=False)
        update_data['name'] = new_name
        # Update department name across employees, attendance, payroll
        db.employees.update_many({"department": old_name}, {"$set": {"department": new_name}})
        db.attendance.update_many({"department": old_name}, {"$set": {"department": new_name}})
        db.payroll.update_many({"department": old_name}, {"$set": {"department": new_name}})

    if 'description' in data:
        update_data['description'] = data['description'].strip()
    if 'manager_name' in data:
        update_data['manager_name'] = data['manager_name'].strip()

    update_data['updated_at'] = datetime.utcnow()
    db.departments.update_one({"_id": existing["_id"]}, {"$set": update_data})

    updated = db.departments.find_one({"_id": existing["_id"]})
    log_activity(db, "Department Updated", f"Updated department '{old_name}'")
    return json_response(serialize_doc(updated), "Department updated successfully")

@departments_bp.route('/<dept_id>', methods=['DELETE'])
@auth_required
def delete_department(dept_id):
    db = get_db()
    query = {}
    if ObjectId.is_valid(dept_id):
        query["_id"] = ObjectId(dept_id)
    else:
        query["name"] = dept_id

    existing = db.departments.find_one(query)
    if not existing:
        return json_response(None, "Department not found", status=404, success=False)

    dept_name = existing.get("name")
    emp_count = db.employees.count_documents({"department": dept_name})
    if emp_count > 0:
        return json_response(None, f"Cannot delete department '{dept_name}' because it currently has {emp_count} assigned employee(s). Please reassign them first.", status=400, success=False)

    db.departments.delete_one({"_id": existing["_id"]})
    log_activity(db, "Department Deleted", f"Deleted department '{dept_name}'")
    return json_response(None, f"Department '{dept_name}' deleted successfully")
