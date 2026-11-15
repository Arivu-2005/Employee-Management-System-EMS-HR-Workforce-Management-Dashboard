import csv
import io
from flask import Blueprint, request, Response
from datetime import datetime
from database import get_db
from utils.helpers import json_response, serialize_docs, auth_required

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/employees', methods=['GET'])
@auth_required
def report_employees():
    db = get_db()
    query = {}

    dept = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()
    emp_type = request.args.get('employment_type', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    if dept and dept != 'All':
        query["department"] = dept
    if status and status != 'All':
        query["status"] = status
    if emp_type and emp_type != 'All':
        query["employment_type"] = emp_type
    if start_date and end_date:
        query["joining_date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["joining_date"] = {"$gte": start_date}

    employees = serialize_docs(db.employees.find(query).sort([("employee_id", 1)]))

    total_gross = sum(e.get("salary", {}).get("gross", 0) for e in employees)
    total_net = sum(e.get("salary", {}).get("net", 0) for e in employees)

    return json_response({
        "records": employees,
        "summary": {
            "total_count": len(employees),
            "active_count": sum(1 for e in employees if e.get("status") == "Active"),
            "total_gross_salary": round(total_gross, 2),
            "total_net_salary": round(total_net, 2)
        }
    }, "Employee report retrieved")

@reports_bp.route('/attendance', methods=['GET'])
@auth_required
def report_attendance():
    db = get_db()
    query = {}

    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    dept = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()

    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["date"] = {"$gte": start_date}
    if dept and dept != 'All':
        query["department"] = dept
    if status and status != 'All':
        query["status"] = status

    records = serialize_docs(db.attendance.find(query).sort([("date", -1)]))

    total = len(records)
    present_cnt = sum(1 for r in records if r.get("status") in ["Present", "Late", "Half-Day"])
    absent_cnt = sum(1 for r in records if r.get("status") == "Absent")
    leave_cnt = sum(1 for r in records if r.get("status") == "Leave")
    total_hours = sum(r.get("working_hours", 0) for r in records)

    return json_response({
        "records": records,
        "summary": {
            "total_records": total,
            "present_count": present_cnt,
            "absent_count": absent_cnt,
            "leave_count": leave_cnt,
            "total_hours": round(total_hours, 1),
            "attendance_rate": round(present_cnt / total * 100, 1) if total > 0 else 0
        }
    }, "Attendance report retrieved")

@reports_bp.route('/leaves', methods=['GET'])
@auth_required
def report_leaves():
    db = get_db()
    query = {}

    status = request.args.get('status', '').strip()
    leave_type = request.args.get('type', '').strip()
    dept = request.args.get('department', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    if status and status != 'All':
        query["status"] = status
    if leave_type and leave_type != 'All':
        query["leave_type"] = leave_type
    if dept and dept != 'All':
        query["department"] = dept
    if start_date and end_date:
        query["start_date"] = {"$gte": start_date, "$lte": end_date}

    records = serialize_docs(db.leaves.find(query).sort([("applied_at", -1)]))

    return json_response({
        "records": records,
        "summary": {
            "total_requests": len(records),
            "approved": sum(1 for r in records if r.get("status") == "Approved"),
            "pending": sum(1 for r in records if r.get("status") == "Pending"),
            "rejected": sum(1 for r in records if r.get("status") == "Rejected"),
            "total_days": sum(r.get("days_count", 0) for r in records if r.get("status") == "Approved")
        }
    }, "Leave report retrieved")

@reports_bp.route('/payroll', methods=['GET'])
@auth_required
def report_payroll():
    db = get_db()
    query = {}

    month = request.args.get('month', '').strip()
    year = request.args.get('year', '').strip()
    dept = request.args.get('department', '').strip()
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
    if status and status != 'All':
        query["payment_status"] = status

    records = serialize_docs(db.payroll.find(query).sort([("year", -1), ("created_at", -1)]))

    total_gross = sum(r.get("gross_salary", 0) for r in records)
    total_net = sum(r.get("net_salary", 0) for r in records)
    total_tax = sum(r.get("tax_deductions", 0) for r in records)
    total_bonus = sum(r.get("bonus", 0) for r in records)

    return json_response({
        "records": records,
        "summary": {
            "total_slips": len(records),
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
            "total_tax": round(total_tax, 2),
            "total_bonus": round(total_bonus, 2)
        }
    }, "Payroll report retrieved")

@reports_bp.route('/export-csv', methods=['GET'])
@auth_required
def export_csv():
    db = get_db()
    report_type = request.args.get('type', 'employees').lower()

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'employees':
        writer.writerow(["Employee ID", "Full Name", "Email", "Phone", "Department", "Designation", "Employment Type", "Joining Date", "Status", "Basic Salary", "Net Salary"])
        for emp in db.employees.find().sort([("employee_id", 1)]):
            sal = emp.get("salary", {})
            writer.writerow([
                emp.get("employee_id"), emp.get("name"), emp.get("email"), emp.get("phone"),
                emp.get("department"), emp.get("designation"), emp.get("employment_type"),
                emp.get("joining_date"), emp.get("status"), sal.get("basic", 0), sal.get("net", 0)
            ])
        filename = f"employees_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    elif report_type == 'attendance':
        writer.writerow(["Date", "Employee ID", "Employee Name", "Department", "Status", "Check In", "Check Out", "Working Hours", "Notes"])
        for att in db.attendance.find().sort([("date", -1)]):
            writer.writerow([
                att.get("date"), att.get("employee_id"), att.get("employee_name"),
                att.get("department"), att.get("status"), att.get("check_in"),
                att.get("check_out"), att.get("working_hours"), att.get("notes")
            ])
        filename = f"attendance_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    elif report_type == 'leaves':
        writer.writerow(["Employee ID", "Employee Name", "Department", "Leave Type", "Start Date", "End Date", "Days", "Reason", "Status", "Reviewed By"])
        for lv in db.leaves.find().sort([("applied_at", -1)]):
            writer.writerow([
                lv.get("employee_id"), lv.get("employee_name"), lv.get("department"),
                lv.get("leave_type"), lv.get("start_date"), lv.get("end_date"),
                lv.get("days_count"), lv.get("reason"), lv.get("status"), lv.get("reviewed_by")
            ])
        filename = f"leaves_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    elif report_type == 'payroll':
        writer.writerow(["Payroll ID", "Employee ID", "Employee Name", "Department", "Month", "Year", "Basic Salary", "HRA", "Allowances", "Overtime Pay", "Bonus", "Gross Salary", "Deductions", "Net Salary", "Status"])
        for p in db.payroll.find().sort([("year", -1), ("created_at", -1)]):
            writer.writerow([
                p.get("payroll_id"), p.get("employee_id"), p.get("employee_name"),
                p.get("department"), p.get("month"), p.get("year"),
                p.get("basic_salary"), p.get("hra"), p.get("allowances"),
                p.get("overtime_pay"), p.get("bonus"), p.get("gross_salary"),
                p.get("total_deductions"), p.get("net_salary"), p.get("payment_status")
            ])
        filename = f"payroll_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    else:
        return json_response(None, "Unsupported report type for CSV export", status=400, success=False)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
