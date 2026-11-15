from flask import Blueprint, request
from bson import ObjectId
from datetime import datetime
from database import get_db
from utils.helpers import json_response, serialize_doc, serialize_docs, log_activity, auth_required
from utils.validators import validate_required_fields, validate_date

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

def calculate_hours(check_in, check_out):
    if not check_in or not check_out or check_in == '-' or check_out == '-':
        return 0.0
    try:
        t1 = datetime.strptime(check_in.strip(), "%H:%M")
        t2 = datetime.strptime(check_out.strip(), "%H:%M")
        diff = (t2 - t1).total_seconds() / 3600.0
        return max(0.0, round(diff, 1))
    except Exception:
        return 0.0

@attendance_bp.route('', methods=['GET'])
@auth_required
def get_attendance():
    db = get_db()
    query = {}

    date_param = request.args.get('date', '').strip()
    emp_id = request.args.get('employee_id', '').strip()
    department = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()
    month = request.args.get('month', '').strip()
    year = request.args.get('year', '').strip()

    if date_param:
        query["date"] = date_param
    elif month and year:
        # Regex for YYYY-MM
        prefix = f"{year}-{month.zfill(2)}"
        query["date"] = {"$regex": f"^{prefix}"}
    elif year:
        query["date"] = {"$regex": f"^{year}"}

    if emp_id:
        query["employee_id"] = emp_id
    if department and department != 'All':
        query["department"] = department
    if status and status != 'All':
        query["status"] = status

    records = serialize_docs(db.attendance.find(query).sort([("date", -1), ("employee_id", 1)]))
    return json_response(records, "Attendance records retrieved successfully")

@attendance_bp.route('/summary', methods=['GET'])
@auth_required
def get_summary():
    db = get_db()
    date_str = request.args.get('date', datetime.utcnow().strftime("%Y-%m-%d")).strip()

    total_employees = db.employees.count_documents({"status": {"$ne": "Terminated"}})
    records = list(db.attendance.find({"date": date_str}))

    present = sum(1 for r in records if r.get("status") == "Present")
    late = sum(1 for r in records if r.get("status") == "Late")
    half_day = sum(1 for r in records if r.get("status") == "Half-Day")
    absent = sum(1 for r in records if r.get("status") == "Absent")
    on_leave = sum(1 for r in records if r.get("status") == "Leave")

    marked_count = len(records)
    unmarked = max(0, total_employees - marked_count)

    rate = round(((present + late + 0.5 * half_day) / total_employees * 100), 1) if total_employees > 0 else 0

    return json_response({
        "date": date_str,
        "total_employees": total_employees,
        "marked_count": marked_count,
        "present": present,
        "late": late,
        "half_day": half_day,
        "absent": absent,
        "on_leave": on_leave,
        "unmarked": unmarked,
        "attendance_rate": rate
    }, "Attendance summary retrieved")

@attendance_bp.route('', methods=['POST'])
@auth_required
def mark_attendance():
    db = get_db()
    data = request.get_json() or {}

    missing = validate_required_fields(data, ['employee_id', 'date', 'status'])
    if missing:
        return json_response(None, f"Missing required fields: {', '.join(missing)}", status=400, success=False)

    emp_id = data['employee_id'].strip()
    date_str = data['date'].strip()
    status = data['status'].strip()

    emp = db.employees.find_one({"employee_id": emp_id})
    if not emp:
        return json_response(None, f"Employee with ID '{emp_id}' not found", status=404, success=False)

    # Prevent duplicate
    existing = db.attendance.find_one({"employee_id": emp_id, "date": date_str})
    if existing:
        return json_response(None, f"Attendance for {emp.get('name')} on {date_str} is already recorded. Please edit the existing entry.", status=409, success=False)

    check_in = data.get('check_in', '-').strip()
    check_out = data.get('check_out', '-').strip()
    hours = float(data.get('working_hours', 0) or 0)
    if hours == 0.0 and check_in != '-' and check_out != '-':
        hours = calculate_hours(check_in, check_out)

    record = {
        "employee_id": emp_id,
        "employee_name": emp.get("name"),
        "department": emp.get("department"),
        "date": date_str,
        "status": status,
        "check_in": check_in,
        "check_out": check_out,
        "working_hours": hours,
        "notes": data.get('notes', '').strip(),
        "created_at": datetime.utcnow()
    }
    result = db.attendance.insert_one(record)
    record["_id"] = result.inserted_id

    log_activity(db, "Attendance Marked", f"Marked {status} for {emp.get('name')} on {date_str}")
    return json_response(serialize_doc(record), "Attendance marked successfully", status=201)

@attendance_bp.route('/<att_id>', methods=['PUT'])
@auth_required
def update_attendance(att_id):
    db = get_db()
    query = {}
    if ObjectId.is_valid(att_id):
        query["_id"] = ObjectId(att_id)
    else:
        return json_response(None, "Invalid attendance ID", status=400, success=False)

    existing = db.attendance.find_one(query)
    if not existing:
        return json_response(None, "Attendance record not found", status=404, success=False)

    data = request.get_json() or {}
    update_data = {}

    for field in ['status', 'check_in', 'check_out', 'notes', 'date']:
        if field in data:
            update_data[field] = data[field]

    check_in = update_data.get('check_in', existing.get('check_in', '-'))
    check_out = update_data.get('check_out', existing.get('check_out', '-'))

    if 'working_hours' in data:
        update_data['working_hours'] = float(data['working_hours'] or 0)
    elif check_in != '-' and check_out != '-':
        update_data['working_hours'] = calculate_hours(check_in, check_out)

    update_data['updated_at'] = datetime.utcnow()
    db.attendance.update_one({"_id": existing["_id"]}, {"$set": update_data})

    updated = db.attendance.find_one({"_id": existing["_id"]})
    log_activity(db, "Attendance Updated", f"Updated attendance for {existing.get('employee_name')} on {existing.get('date')}")
    return json_response(serialize_doc(updated), "Attendance updated successfully")

@attendance_bp.route('/<att_id>', methods=['DELETE'])
@auth_required
def delete_attendance(att_id):
    db = get_db()
    if not ObjectId.is_valid(att_id):
        return json_response(None, "Invalid attendance ID", status=400, success=False)

    existing = db.attendance.find_one({"_id": ObjectId(att_id)})
    if not existing:
        return json_response(None, "Attendance record not found", status=404, success=False)

    db.attendance.delete_one({"_id": ObjectId(att_id)})
    log_activity(db, "Attendance Deleted", f"Deleted attendance record for {existing.get('employee_name')} on {existing.get('date')}")
    return json_response(None, "Attendance record deleted successfully")
