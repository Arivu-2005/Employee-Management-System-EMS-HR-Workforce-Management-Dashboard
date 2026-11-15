from flask import Blueprint, request
from bson import ObjectId
from datetime import datetime
from database import get_db
from utils.helpers import json_response, serialize_doc, serialize_docs, log_activity, auth_required
from utils.validators import validate_required_fields

payroll_bp = Blueprint('payroll', __name__, url_prefix='/api/payroll')

@payroll_bp.route('', methods=['GET'])
@auth_required
def list_payroll():
    db = get_db()
    query = {}

    month = request.args.get('month', '').strip()
    year = request.args.get('year', '').strip()
    dept = request.args.get('department', '').strip()
    emp_id = request.args.get('employee_id', '').strip()
    status = request.args.get('status', '').strip()

    if month and month != 'All':
        query["month"] = month
    if year and year != 'All':
        try:
            query["year"] = int(year)
        except ValueError:
            query["year"] = year
    if dept and dept != 'All':
        query["department"] = dept
    if emp_id:
        query["employee_id"] = emp_id
    if status and status != 'All':
        query["payment_status"] = status

    records = serialize_docs(db.payroll.find(query).sort([("year", -1), ("created_at", -1)]))
    return json_response(records, "Payroll records retrieved successfully")

@payroll_bp.route('/<pay_id>', methods=['GET'])
@auth_required
def get_payroll(pay_id):
    db = get_db()
    query = {}
    if ObjectId.is_valid(pay_id):
        query["_id"] = ObjectId(pay_id)
    else:
        query["payroll_id"] = pay_id

    record = db.payroll.find_one(query)
    if not record:
        return json_response(None, "Payroll record not found", status=404, success=False)

    return json_response(serialize_doc(record), "Payroll record retrieved")

@payroll_bp.route('/<pay_id>/slip', methods=['GET'])
@auth_required
def get_payroll_slip(pay_id):
    db = get_db()
    query = {}
    if ObjectId.is_valid(pay_id):
        query["_id"] = ObjectId(pay_id)
    else:
        query["payroll_id"] = pay_id

    record = db.payroll.find_one(query)
    if not record:
        return json_response(None, "Payroll record not found", status=404, success=False)

    emp = db.employees.find_one({"employee_id": record.get("employee_id")})
    company = db.settings.find_one() or {}

    slip_data = {
        "payroll": serialize_doc(record),
        "employee": serialize_doc(emp) if emp else {},
        "company": serialize_doc(company),
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    }
    return json_response(slip_data, "Salary slip data retrieved successfully")

@payroll_bp.route('/generate', methods=['POST'])
@auth_required
def generate_payroll():
    db = get_db()
    data = request.get_json() or {}

    month = data.get('month', datetime.utcnow().strftime("%B")).strip()
    year = int(data.get('year', datetime.utcnow().year))
    target_emp_id = data.get('employee_id', '').strip()  # If empty, generate for all active employees

    emp_query = {"status": "Active"}
    if target_emp_id and target_emp_id != 'ALL':
        emp_query["employee_id"] = target_emp_id

    employees = list(db.employees.find(emp_query))
    if not employees:
        return json_response(None, "No eligible active employees found for payroll generation", status=404, success=False)

    generated = []
    skipped = []

    for emp in employees:
        e_id = emp["employee_id"]
        # Check duplicate
        exists = db.payroll.find_one({"employee_id": e_id, "month": month, "year": year})
        if exists:
            skipped.append(f"{emp.get('name')} ({e_id})")
            continue

        sal_conf = emp.get('salary', {})
        basic = float(data.get('basic_salary', sal_conf.get('basic', 5000)) or 0)
        hra = float(data.get('hra', sal_conf.get('hra', 1500)) or 0)
        allowances = float(data.get('allowances', sal_conf.get('allowances', 500)) or 0)
        deductions = float(data.get('deductions', sal_conf.get('deductions', 400)) or 0)

        # Overtime calculation
        ot_hours = float(data.get('overtime_hours', 0) or 0)
        hourly_rate = (basic / 160) if basic > 0 else 25.0
        ot_pay = round(ot_hours * hourly_rate * 1.5, 2)

        bonus = float(data.get('bonus', 0) or 0)
        tax = float(data.get('tax_deductions', deductions * 0.7) or 0)
        other_deduct = float(data.get('other_deductions', deductions * 0.3) or 0)

        gross = round(basic + hra + allowances + ot_pay + bonus, 2)
        total_deductions = round(tax + other_deduct, 2)
        net = max(0.0, round(gross - total_deductions, 2))

        pay_id = f"PAY-{year}-{e_id.replace('EMP-', '')}-{int(datetime.utcnow().timestamp()) % 10000}"

        payroll_entry = {
            "payroll_id": pay_id,
            "employee_id": e_id,
            "employee_name": emp.get("name"),
            "department": emp.get("department"),
            "designation": emp.get("designation"),
            "month": month,
            "year": year,
            "basic_salary": basic,
            "hra": hra,
            "allowances": allowances,
            "overtime_hours": ot_hours,
            "overtime_pay": ot_pay,
            "bonus": bonus,
            "gross_salary": gross,
            "tax_deductions": tax,
            "other_deductions": other_deduct,
            "total_deductions": total_deductions,
            "net_salary": net,
            "payment_status": data.get("payment_status", "Paid"),
            "payment_date": data.get("payment_date", datetime.utcnow().strftime("%Y-%m-%d")),
            "payment_method": data.get("payment_method", "Direct Bank Deposit"),
            "created_at": datetime.utcnow()
        }
        res = db.payroll.insert_one(payroll_entry)
        payroll_entry["_id"] = res.inserted_id
        generated.append(serialize_doc(payroll_entry))

    msg = f"Generated payroll for {len(generated)} employee(s)."
    if skipped:
        msg += f" Skipped {len(skipped)} already generated ({', '.join(skipped[:3])}{'...' if len(skipped)>3 else ''})."

    log_activity(db, "Payroll Generated", f"Generated {len(generated)} payroll records for {month} {year}")

    return json_response({
        "generated_count": len(generated),
        "skipped_count": len(skipped),
        "records": generated,
        "skipped": skipped
    }, msg, status=201 if generated else 200)

@payroll_bp.route('/<pay_id>', methods=['PUT'])
@auth_required
def update_payroll(pay_id):
    db = get_db()
    query = {}
    if ObjectId.is_valid(pay_id):
        query["_id"] = ObjectId(pay_id)
    else:
        query["payroll_id"] = pay_id

    existing = db.payroll.find_one(query)
    if not existing:
        return json_response(None, "Payroll record not found", status=404, success=False)

    data = request.get_json() or {}
    update_data = {}

    for field in ['payment_status', 'payment_date', 'payment_method', 'bonus', 'overtime_hours', 'tax_deductions', 'other_deductions']:
        if field in data:
            update_data[field] = data[field]

    # Recalculate if numbers changed
    if any(k in update_data for k in ['bonus', 'overtime_hours', 'tax_deductions', 'other_deductions']):
        basic = existing.get("basic_salary", 0)
        hra = existing.get("hra", 0)
        allowances = existing.get("allowances", 0)
        ot_hours = float(update_data.get("overtime_hours", existing.get("overtime_hours", 0)))
        hourly_rate = (basic / 160) if basic > 0 else 25.0
        ot_pay = round(ot_hours * hourly_rate * 1.5, 2)
        bonus = float(update_data.get("bonus", existing.get("bonus", 0)))
        tax = float(update_data.get("tax_deductions", existing.get("tax_deductions", 0)))
        other_deduct = float(update_data.get("other_deductions", existing.get("other_deductions", 0)))

        gross = round(basic + hra + allowances + ot_pay + bonus, 2)
        total_ded = round(tax + other_deduct, 2)
        net = max(0.0, round(gross - total_ded, 2))

        update_data["overtime_pay"] = ot_pay
        update_data["gross_salary"] = gross
        update_data["total_deductions"] = total_ded
        update_data["net_salary"] = net

    update_data["updated_at"] = datetime.utcnow()
    db.payroll.update_one({"_id": existing["_id"]}, {"$set": update_data})

    updated = db.payroll.find_one({"_id": existing["_id"]})
    log_activity(db, "Payroll Updated", f"Updated payroll record {existing.get('payroll_id')} for {existing.get('employee_name')}")
    return json_response(serialize_doc(updated), "Payroll record updated successfully")

@payroll_bp.route('/<pay_id>', methods=['DELETE'])
@auth_required
def delete_payroll(pay_id):
    db = get_db()
    query = {}
    if ObjectId.is_valid(pay_id):
        query["_id"] = ObjectId(pay_id)
    else:
        query["payroll_id"] = pay_id

    existing = db.payroll.find_one(query)
    if not existing:
        return json_response(None, "Payroll record not found", status=404, success=False)

    db.payroll.delete_one({"_id": existing["_id"]})
    log_activity(db, "Payroll Deleted", f"Deleted payroll record {existing.get('payroll_id')}")
    return json_response(None, "Payroll record deleted successfully")
