from flask import Blueprint, request
from bson import ObjectId
from datetime import datetime, timedelta
from database import get_db
from utils.helpers import json_response, serialize_doc, serialize_docs, log_activity, auth_required
from utils.validators import validate_required_fields, validate_date

leaves_bp = Blueprint('leaves', __name__, url_prefix='/api/leaves')

@leaves_bp.route('', methods=['GET'])
@auth_required
def list_leaves():
    db = get_db()
    query = {}

    status = request.args.get('status', '').strip()
    emp_id = request.args.get('employee_id', '').strip()
    leave_type = request.args.get('type', '').strip()

    if status and status != 'All':
        query["status"] = status
    if emp_id:
        query["employee_id"] = emp_id
    if leave_type and leave_type != 'All':
        query["leave_type"] = leave_type

    leaves = serialize_docs(db.leaves.find(query).sort([("applied_at", -1)]))
    return json_response(leaves, "Leaves retrieved successfully")

@leaves_bp.route('', methods=['POST'])
@auth_required
def apply_leave():
    db = get_db()
    data = request.get_json() or {}

    required = ['employee_id', 'leave_type', 'start_date', 'end_date', 'reason']
    missing = validate_required_fields(data, required)
    if missing:
        return json_response(None, f"Missing required fields: {', '.join(missing)}", status=400, success=False)

    emp_id = data['employee_id'].strip()
    emp = db.employees.find_one({"employee_id": emp_id})
    if not emp:
        return json_response(None, f"Employee '{emp_id}' not found", status=404, success=False)

    start_date_str = data['start_date'].strip()
    end_date_str = data['end_date'].strip()
    try:
        d1 = datetime.strptime(start_date_str, "%Y-%m-%d")
        d2 = datetime.strptime(end_date_str, "%Y-%m-%d")
        if d2 < d1:
            return json_response(None, "End date cannot be prior to start date", status=400, success=False)
        days_count = (d2 - d1).days + 1
    except ValueError:
        return json_response(None, "Invalid date format. Use YYYY-MM-DD", status=400, success=False)

    leave_type = data['leave_type'].strip()
    type_key = "casual" if "casual" in leave_type.lower() else ("sick" if "sick" in leave_type.lower() else "earned")

    balances = emp.get("leave_balance", {"casual": 12, "sick": 10, "earned": 15})
    current_balance = balances.get(type_key, 0)
    if current_balance < days_count:
        return json_response(None, f"Insufficient leave balance: Employee has {current_balance} {leave_type} remaining, requested {days_count} days.", status=400, success=False)

    leave_doc = {
        "employee_id": emp_id,
        "employee_name": emp.get("name"),
        "department": emp.get("department"),
        "leave_type": leave_type,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "days_count": days_count,
        "reason": data['reason'].strip(),
        "status": "Pending",
        "applied_at": datetime.utcnow(),
        "reviewed_by": None,
        "review_comment": None
    }
    result = db.leaves.insert_one(leave_doc)
    leave_doc["_id"] = result.inserted_id

    log_activity(db, "Leave Applied", f"Leave application submitted for {emp.get('name')} ({days_count} days {leave_type})")
    return json_response(serialize_doc(leave_doc), "Leave request submitted successfully", status=201)

@leaves_bp.route('/<leave_id>/approve', methods=['PUT'])
@auth_required
def approve_leave(leave_id):
    db = get_db()
    if not ObjectId.is_valid(leave_id):
        return json_response(None, "Invalid leave ID", status=400, success=False)

    leave = db.leaves.find_one({"_id": ObjectId(leave_id)})
    if not leave:
        return json_response(None, "Leave request not found", status=404, success=False)

    if leave.get("status") == "Approved":
        return json_response(None, "Leave is already approved", status=400, success=False)

    emp_id = leave.get("employee_id")
    emp = db.employees.find_one({"employee_id": emp_id})
    if not emp:
        return json_response(None, "Associated employee not found", status=404, success=False)

    data = request.get_json() or {}
    admin_name = request.current_admin.get("name", "Admin") if hasattr(request, "current_admin") else "Admin"
    comment = data.get("review_comment", "Approved by administrator")

    # Deduct balance
    leave_type = leave.get("leave_type", "Casual Leave")
    type_key = "casual" if "casual" in leave_type.lower() else ("sick" if "sick" in leave_type.lower() else "earned")
    balances = emp.get("leave_balance", {"casual": 12, "sick": 10, "earned": 15})
    new_bal = max(0, balances.get(type_key, 0) - leave.get("days_count", 1))
    balances[type_key] = new_bal
    db.employees.update_one({"employee_id": emp_id}, {"$set": {"leave_balance": balances}})

    # Update leave record
    db.leaves.update_one({"_id": ObjectId(leave_id)}, {"$set": {
        "status": "Approved",
        "reviewed_by": admin_name,
        "review_comment": comment,
        "reviewed_at": datetime.utcnow()
    }})

    # Synchronize attendance records for all dates in leave period without duplicate records
    try:
        d1 = datetime.strptime(leave["start_date"], "%Y-%m-%d")
        d2 = datetime.strptime(leave["end_date"], "%Y-%m-%d")
        cur_day = d1
        while cur_day <= d2:
            day_str = cur_day.strftime("%Y-%m-%d")
            # Upsert attendance to prevent duplicates
            db.attendance.update_one(
                {"employee_id": emp_id, "date": day_str},
                {"$set": {
                    "employee_name": emp.get("name"),
                    "department": emp.get("department"),
                    "status": "Leave",
                    "check_in": "-",
                    "check_out": "-",
                    "working_hours": 0.0,
                    "notes": f"Approved {leave_type}: {leave.get('reason')}",
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
            cur_day += timedelta(days=1)
    except Exception as e:
        print(f"Error syncing attendance for approved leave: {e}")

    updated_leave = db.leaves.find_one({"_id": ObjectId(leave_id)})
    log_activity(db, "Leave Approved", f"Approved {leave.get('days_count')} day(s) {leave_type} for {emp.get('name')}")
    return json_response(serialize_doc(updated_leave), "Leave request approved successfully")

@leaves_bp.route('/<leave_id>/reject', methods=['PUT'])
@auth_required
def reject_leave(leave_id):
    db = get_db()
    if not ObjectId.is_valid(leave_id):
        return json_response(None, "Invalid leave ID", status=400, success=False)

    leave = db.leaves.find_one({"_id": ObjectId(leave_id)})
    if not leave:
        return json_response(None, "Leave request not found", status=404, success=False)

    data = request.get_json() or {}
    admin_name = request.current_admin.get("name", "Admin") if hasattr(request, "current_admin") else "Admin"
    comment = data.get("review_comment", "Request rejected by management")

    db.leaves.update_one({"_id": ObjectId(leave_id)}, {"$set": {
        "status": "Rejected",
        "reviewed_by": admin_name,
        "review_comment": comment,
        "reviewed_at": datetime.utcnow()
    }})

    updated_leave = db.leaves.find_one({"_id": ObjectId(leave_id)})
    log_activity(db, "Leave Rejected", f"Rejected leave request for {leave.get('employee_name')}")
    return json_response(serialize_doc(updated_leave), "Leave request rejected")

@leaves_bp.route('/<leave_id>', methods=['DELETE'])
@auth_required
def delete_leave(leave_id):
    db = get_db()
    if not ObjectId.is_valid(leave_id):
        return json_response(None, "Invalid leave ID", status=400, success=False)

    res = db.leaves.delete_one({"_id": ObjectId(leave_id)})
    if res.deleted_count == 0:
        return json_response(None, "Leave record not found", status=404, success=False)

    log_activity(db, "Leave Deleted", f"Deleted leave record {leave_id}")
    return json_response(None, "Leave record deleted successfully")
