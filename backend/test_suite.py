import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from database import get_db

def run_tests():
    print("=" * 70)
    print("APEX EMPLOYEE MANAGEMENT SYSTEM (EMS) - INTEGRATED TEST SUITE")
    print("=" * 70)

    client = app.test_client()
    passed = 0
    total = 0

    def assert_test(name, condition, details=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"[PASS] {name}")
        else:
            print(f"[FAIL] {name} - {details}")

    # 1. Health check
    res = client.get('/api/health')
    assert_test("API Health Check", res.status_code == 200 and res.get_json().get("status") == "healthy")

    # 2. Authentication: Login
    res = client.post('/api/auth/login', json={'email': 'admin@ems.com', 'password': 'wrongpassword'})
    assert_test("Auth: Reject Invalid Password", res.status_code == 401)

    res = client.post('/api/auth/login', json={'email': 'admin@ems.com', 'password': 'admin123'})
    login_data = res.get_json()
    assert_test("Auth: Successful Login", res.status_code == 200 and login_data.get("success") is True)

    token = login_data['data']['token']
    auth_headers = {'Authorization': f'Bearer {token}'}

    # 3. Auth: Profile
    res = client.get('/api/auth/profile', headers=auth_headers)
    assert_test("Auth: Get Admin Profile", res.status_code == 200 and res.get_json()['data']['email'] == 'admin@ems.com')

    # 4. Dashboard Stats & Analytics
    res = client.get('/api/dashboard/stats', headers=auth_headers)
    assert_test("Dashboard: Fetch Stats", res.status_code == 200 and 'total_employees' in res.get_json()['data'])

    res = client.get('/api/dashboard/analytics', headers=auth_headers)
    assert_test("Dashboard: Fetch Analytics Data", res.status_code == 200 and 'department_distribution' in res.get_json()['data'])

    # 5. Department CRUD
    dept_res = client.post('/api/departments', headers=auth_headers, json={
        'name': 'Test Innovation Lab',
        'description': 'Advanced R&D for AI automation',
        'manager_name': 'Dr. Alan Turing'
    })
    assert_test("Departments: Create Department", dept_res.status_code == 201)
    dept_id = dept_res.get_json()['data']['_id']

    dept_list = client.get('/api/departments', headers=auth_headers)
    assert_test("Departments: List Departments", dept_list.status_code == 200 and len(dept_list.get_json()['data']) >= 6)

    # 6. Employee CRUD
    new_emp_res = client.post('/api/employees', headers=auth_headers, json={
        'first_name': 'Alexander',
        'last_name': 'Hamilton',
        'email': 'alexander.hamilton@apexenterprise.io',
        'phone': '+1 555-999-8888',
        'department': 'Finance',
        'designation': 'Senior Financial Analyst',
        'employment_type': 'Full-Time',
        'basic_salary': 7500,
        'hra': 2000,
        'allowances': 800,
        'deductions': 600
    })
    assert_test("Employees: Create Employee", new_emp_res.status_code == 201)
    emp_data = new_emp_res.get_json()['data']
    test_emp_id = emp_data['employee_id']
    assert_test("Employees: Auto-Generated ID Format", test_emp_id.startswith('EMP-'))

    # Read Single Employee
    get_emp_res = client.get(f'/api/employees/{test_emp_id}', headers=auth_headers)
    assert_test("Employees: Get Single Employee Details", get_emp_res.status_code == 200 and get_emp_res.get_json()['data']['name'] == 'Alexander Hamilton')

    # Update Employee
    upd_emp_res = client.put(f'/api/employees/{test_emp_id}', headers=auth_headers, json={
        'designation': 'Lead Treasury Strategist',
        'basic_salary': 8000
    })
    assert_test("Employees: Update Employee", upd_emp_res.status_code == 200 and upd_emp_res.get_json()['data']['designation'] == 'Lead Treasury Strategist')

    # 7. Attendance: Mark & Duplicate Prevention
    att_res = client.post('/api/attendance', headers=auth_headers, json={
        'employee_id': test_emp_id,
        'date': '2026-11-15',
        'status': 'Present',
        'check_in': '08:50',
        'check_out': '17:20',
        'notes': 'First day orientation'
    })
    assert_test("Attendance: Mark Attendance", att_res.status_code == 201)

    # Duplicate check
    dup_att_res = client.post('/api/attendance', headers=auth_headers, json={
        'employee_id': test_emp_id,
        'date': '2026-11-15',
        'status': 'Present'
    })
    assert_test("Attendance: Prevent Duplicate Attendance for Same Day", dup_att_res.status_code == 409)

    # Attendance Summary
    att_sum = client.get('/api/attendance/summary?date=2026-11-15', headers=auth_headers)
    assert_test("Attendance: Daily Summary Aggregation", att_sum.status_code == 200 and att_sum.get_json()['data']['present'] >= 1)

    # 8. Leaves: Application & Approval
    leave_app = client.post('/api/leaves', headers=auth_headers, json={
        'employee_id': test_emp_id,
        'leave_type': 'Casual Leave',
        'start_date': '2026-11-20',
        'end_date': '2026-11-21',
        'reason': 'Personal family celebration'
    })
    assert_test("Leaves: Submit Leave Application", leave_app.status_code == 201)
    leave_id = leave_app.get_json()['data']['_id']

    # Approve Leave
    leave_appr = client.put(f'/api/leaves/{leave_id}/approve', headers=auth_headers, json={
        'review_comment': 'Approved by HR Lead'
    })
    assert_test("Leaves: Approve Leave Request", leave_appr.status_code == 200 and leave_appr.get_json()['data']['status'] == 'Approved')

    # Verify that attendance was automatically synchronized
    att_sync_check = client.get(f'/api/attendance?employee_id={test_emp_id}&date=2026-11-20', headers=auth_headers)
    assert_test("Leaves: Attendance Auto-Synced to Leave Status", att_sync_check.status_code == 200 and len(att_sync_check.get_json()['data']) > 0 and att_sync_check.get_json()['data'][0]['status'] == 'Leave')

    # 9. Payroll: Generate & Salary Slip
    payroll_gen = client.post('/api/payroll/generate', headers=auth_headers, json={
        'employee_id': test_emp_id,
        'month': 'December',
        'year': 2026,
        'overtime_hours': 5,
        'bonus': 500
    })
    assert_test("Payroll: Generate Monthly Payroll", payroll_gen.status_code == 201)
    pay_record = payroll_gen.get_json()['data']['records'][0]
    pay_id = pay_record['payroll_id']

    # Duplicate Payroll prevention
    dup_payroll = client.post('/api/payroll/generate', headers=auth_headers, json={
        'employee_id': test_emp_id,
        'month': 'December',
        'year': 2026
    })
    assert_test("Payroll: Prevent Duplicate Payroll Generation", dup_payroll.get_json()['data']['skipped_count'] >= 1)

    # Salary Slip Fetch
    slip_res = client.get(f'/api/payroll/{pay_id}/slip', headers=auth_headers)
    assert_test("Payroll: Retrieve Salary Slip with Earnings & Deductions", slip_res.status_code == 200 and 'payroll' in slip_res.get_json()['data'])

    # 10. Performance Review
    perf_res = client.post('/api/performance', headers=auth_headers, json={
        'employee_id': test_emp_id,
        'review_period': 'Q4 2026',
        'rating': 5,
        'productivity_score': 97.0,
        'task_completion_rate': 99.0,
        'remarks': 'Outstanding onboarding speed and financial analysis accuracy.'
    })
    assert_test("Performance: Create Review Evaluation", perf_res.status_code == 201)

    perf_analytics = client.get('/api/performance/analytics', headers=auth_headers)
    assert_test("Performance: Fetch Performance Analytics", perf_analytics.status_code == 200 and 'department_analytics' in perf_analytics.get_json()['data'])

    # 11. Reports & CSV Export
    emp_rep = client.get('/api/reports/employees', headers=auth_headers)
    assert_test("Reports: Employees Report Data", emp_rep.status_code == 200 and len(emp_rep.get_json()['data']['records']) > 0)

    csv_res = client.get('/api/reports/export-csv?type=employees', headers=auth_headers)
    assert_test("Reports: Export CSV Formatted Stream", csv_res.status_code == 200 and 'text/csv' in csv_res.content_type)

    # 12. Clean Up Test Employee & Department
    del_emp = client.delete(f'/api/employees/{test_emp_id}', headers=auth_headers)
    assert_test("Employees: Delete Employee Record", del_emp.status_code == 200)

    del_dept = client.delete(f'/api/departments/{dept_id}', headers=auth_headers)
    assert_test("Departments: Delete Department", del_dept.status_code == 200)

    # 13. Settings: Reset Demo Data
    reset_res = client.post('/api/settings/reset-demo-data', headers=auth_headers)
    assert_test("Settings: Reset Demo Data Operation", reset_res.status_code == 200)

    # 14. Static Web Pages Serving
    pages = ['index.html', 'dashboard.html', 'employees.html', 'departments.html', 'attendance.html', 'leaves.html', 'payroll.html', 'performance.html', 'reports.html', 'settings.html']
    all_pages_ok = True
    for p in pages:
        res = client.get(f'/{p}')
        if res.status_code != 200:
            all_pages_ok = False
            print(f"Failed to serve /{p}: {res.status_code}")
    assert_test("Frontend: Serve All 10 HTML Pages & Assets", all_pages_ok)

    print("=" * 70)
    print(f"TEST RESULTS: {passed}/{total} Passed ({round(passed/total*100, 1)}%)")
    print("=" * 70)
    return passed == total

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
