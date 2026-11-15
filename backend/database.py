import os
from datetime import datetime, date, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash
from config import Config

_client = None
_db = None

def get_db():
    global _client, _db
    if _db is not None:
        return _db

    uri = Config.MONGO_URI
    db_name = Config.DB_NAME

    try:
        # Try real MongoDB connection with a short timeout to prevent blocking if offline
        client = MongoClient(uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
        # Verify connection
        client.admin.command('ping')
        _client = client
        _db = client[db_name]
        print(f"[Database] Successfully connected to MongoDB: {db_name}")
    except Exception as e:
        print(f"[Database] MongoDB connection error ({e}). Initializing in-memory MongoMock for seamless local testing.")
        import mongomock
        client = mongomock.MongoClient()
        _client = client
        _db = client[db_name]

    init_indexes(_db)
    seed_demo_data_if_empty(_db)
    return _db

def init_indexes(db):
    try:
        # Admins
        db.admins.create_index([("email", ASCENDING)], unique=True)
        # Employees
        db.employees.create_index([("employee_id", ASCENDING)], unique=True)
        db.employees.create_index([("email", ASCENDING)], unique=True)
        db.employees.create_index([("department", ASCENDING)])
        db.employees.create_index([("status", ASCENDING)])
        # Departments
        db.departments.create_index([("name", ASCENDING)], unique=True)
        # Attendance: compound unique for employee_id and date (YYYY-MM-DD)
        db.attendance.create_index([("employee_id", ASCENDING), ("date", ASCENDING)], unique=True)
        # Leaves
        db.leaves.create_index([("employee_id", ASCENDING)])
        db.leaves.create_index([("status", ASCENDING)])
        # Payroll: compound unique for employee_id, month, year
        db.payroll.create_index([("employee_id", ASCENDING), ("month", ASCENDING), ("year", ASCENDING)], unique=True)
        # Performance
        db.performance_reviews.create_index([("employee_id", ASCENDING)])
        # Activities
        db.activities.create_index([("created_at", DESCENDING)])
    except Exception as e:
        print(f"[Database] Notice during index creation: {e}")

def seed_demo_data_if_empty(db):
    if db.admins.count_documents({}) == 0:
        seed_all_data(db)

def seed_all_data(db):
    print("[Database] Seeding initial demo data...")
    # 1. Admin
    admin_pw = generate_password_hash("admin123")
    db.admins.insert_one({
        "name": "Alex Mercer",
        "email": "admin@ems.com",
        "password": admin_pw,
        "role": "Super Admin",
        "phone": "+1 (555) 019-2834",
        "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=300&q=80",
        "created_at": datetime.utcnow()
    })

    # 2. Company Settings
    db.settings.delete_many({})
    db.settings.insert_one({
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
    })

    # 3. Departments
    departments_data = [
        {
            "name": "Engineering",
            "description": "Software architecture, full-stack development, and infrastructure.",
            "manager_name": "Marcus Vance",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Human Resources",
            "description": "Talent acquisition, employee welfare, performance, and culture.",
            "manager_name": "Elena Rostova",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Finance",
            "description": "Financial planning, accounting, payroll management, and reporting.",
            "manager_name": "David Sterling",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Marketing",
            "description": "Brand strategy, digital marketing campaigns, and lead generation.",
            "manager_name": "Sophia Chen",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Sales",
            "description": "Global enterprise sales, client partnerships, and revenue expansion.",
            "manager_name": "Liam Gallagher",
            "created_at": datetime.utcnow()
        }
    ]
    db.departments.insert_many(departments_data)

    # 4. Employees
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    employees_data = [
        {
            "employee_id": "EMP-1001",
            "first_name": "Marcus",
            "last_name": "Vance",
            "name": "Marcus Vance",
            "email": "marcus.vance@apexenterprise.io",
            "phone": "+1 555-234-5678",
            "gender": "Male",
            "dob": "1988-04-12",
            "address": "742 Evergreen Terrace, San Francisco, CA",
            "department": "Engineering",
            "designation": "Lead Solutions Architect",
            "employment_type": "Full-Time",
            "joining_date": "2021-03-15",
            "status": "Active",
            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 8500,
                "hra": 2500,
                "allowances": 1200,
                "deductions": 700,
                "gross": 12200,
                "net": 11500
            },
            "leave_balance": {"casual": 10, "sick": 8, "earned": 14},
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1002",
            "first_name": "Elena",
            "last_name": "Rostova",
            "name": "Elena Rostova",
            "email": "elena.rostova@apexenterprise.io",
            "phone": "+1 555-345-6789",
            "gender": "Female",
            "dob": "1991-08-23",
            "address": "450 Geary St, San Francisco, CA",
            "department": "Human Resources",
            "designation": "HR Director",
            "employment_type": "Full-Time",
            "joining_date": "2021-06-01",
            "status": "Active",
            "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 7000,
                "hra": 2000,
                "allowances": 900,
                "deductions": 600,
                "gross": 9900,
                "net": 9300
            },
            "leave_balance": {"casual": 11, "sick": 9, "earned": 13},
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1003",
            "first_name": "Sophia",
            "last_name": "Chen",
            "name": "Sophia Chen",
            "email": "sophia.chen@apexenterprise.io",
            "phone": "+1 555-456-7890",
            "gender": "Female",
            "dob": "1993-11-05",
            "address": "1280 Mission St, San Francisco, CA",
            "department": "Marketing",
            "designation": "Head of Growth & Brand",
            "employment_type": "Full-Time",
            "joining_date": "2022-01-10",
            "status": "Active",
            "avatar": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 6500,
                "hra": 1800,
                "allowances": 850,
                "deductions": 550,
                "gross": 9150,
                "net": 8600
            },
            "leave_balance": {"casual": 8, "sick": 10, "earned": 12},
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1004",
            "first_name": "David",
            "last_name": "Sterling",
            "name": "David Sterling",
            "email": "david.sterling@apexenterprise.io",
            "phone": "+1 555-567-8901",
            "gender": "Male",
            "dob": "1986-02-17",
            "address": "88 King St, San Francisco, CA",
            "department": "Finance",
            "designation": "Chief Financial Officer",
            "employment_type": "Full-Time",
            "joining_date": "2020-11-15",
            "status": "Active",
            "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 9500,
                "hra": 2800,
                "allowances": 1500,
                "deductions": 900,
                "gross": 13800,
                "net": 12900
            },
            "leave_balance": {"casual": 12, "sick": 10, "earned": 15},
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1005",
            "first_name": "Liam",
            "last_name": "Gallagher",
            "name": "Liam Gallagher",
            "email": "liam.gallagher@apexenterprise.io",
            "phone": "+1 555-678-9012",
            "gender": "Male",
            "dob": "1990-09-30",
            "address": "333 Fremont St, San Francisco, CA",
            "department": "Sales",
            "designation": "VP of Global Sales",
            "employment_type": "Full-Time",
            "joining_date": "2022-04-20",
            "status": "Active",
            "avatar": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 8000,
                "hra": 2200,
                "allowances": 1400,
                "deductions": 750,
                "gross": 11600,
                "net": 10850
            },
            "leave_balance": {"casual": 9, "sick": 7, "earned": 11},
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1006",
            "first_name": "Aria",
            "last_name": "Montgomery",
            "name": "Aria Montgomery",
            "email": "aria.montgomery@apexenterprise.io",
            "phone": "+1 555-789-0123",
            "gender": "Female",
            "dob": "1995-07-14",
            "address": "200 Brannan St, San Francisco, CA",
            "department": "Engineering",
            "designation": "Senior Full-Stack Engineer",
            "employment_type": "Full-Time",
            "joining_date": "2022-09-01",
            "status": "Active",
            "avatar": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 6800,
                "hra": 1900,
                "allowances": 800,
                "deductions": 580,
                "gross": 9500,
                "net": 8920
            },
            "leave_balance": {"casual": 10, "sick": 10, "earned": 14},
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1007",
            "first_name": "Julian",
            "last_name": "Barnes",
            "name": "Julian Barnes",
            "email": "julian.barnes@apexenterprise.io",
            "phone": "+1 555-890-1234",
            "gender": "Male",
            "dob": "1994-03-25",
            "address": "550 Battery St, San Francisco, CA",
            "department": "Marketing",
            "designation": "Content & Media Strategist",
            "employment_type": "Part-Time",
            "joining_date": "2023-02-15",
            "status": "Active",
            "avatar": "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 3800,
                "hra": 1000,
                "allowances": 400,
                "deductions": 300,
                "gross": 5200,
                "net": 4900
            },
            "leave_balance": {"casual": 6, "sick": 6, "earned": 8},
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1008",
            "first_name": "Chloe",
            "last_name": "Bennett",
            "name": "Chloe Bennett",
            "email": "chloe.bennett@apexenterprise.io",
            "phone": "+1 555-901-2345",
            "gender": "Female",
            "dob": "1996-12-09",
            "address": "100 Van Ness Ave, San Francisco, CA",
            "department": "Sales",
            "designation": "Enterprise Account Executive",
            "employment_type": "Full-Time",
            "joining_date": "2023-05-10",
            "status": "On Leave",
            "avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=300&q=80",
            "salary": {
                "basic": 5500,
                "hra": 1500,
                "allowances": 700,
                "deductions": 480,
                "gross": 7700,
                "net": 7220
            },
            "leave_balance": {"casual": 7, "sick": 9, "earned": 10},
            "created_at": datetime.utcnow()
        }
    ]
    db.employees.insert_many(employees_data)

    # 5. Attendance (for today and previous days)
    attendance_records = [
        {"employee_id": "EMP-1001", "employee_name": "Marcus Vance", "department": "Engineering", "date": today_str, "status": "Present", "check_in": "08:55", "check_out": "17:30", "working_hours": 8.5, "notes": "On-time arrival"},
        {"employee_id": "EMP-1002", "employee_name": "Elena Rostova", "department": "Human Resources", "date": today_str, "status": "Present", "check_in": "09:02", "check_out": "17:45", "working_hours": 8.7, "notes": "On-time arrival"},
        {"employee_id": "EMP-1003", "employee_name": "Sophia Chen", "department": "Marketing", "date": today_str, "status": "Late", "check_in": "09:40", "check_out": "18:15", "working_hours": 8.5, "notes": "Traffic delay on bridge"},
        {"employee_id": "EMP-1004", "employee_name": "David Sterling", "department": "Finance", "date": today_str, "status": "Present", "check_in": "08:45", "check_out": "17:15", "working_hours": 8.5, "notes": "Early check-in"},
        {"employee_id": "EMP-1005", "employee_name": "Liam Gallagher", "department": "Sales", "date": today_str, "status": "Half-Day", "check_in": "09:00", "check_out": "13:00", "working_hours": 4.0, "notes": "Client on-site visit in afternoon"},
        {"employee_id": "EMP-1006", "employee_name": "Aria Montgomery", "department": "Engineering", "date": today_str, "status": "Present", "check_in": "09:10", "check_out": "18:00", "working_hours": 8.8, "notes": "Sprint delivery"},
        {"employee_id": "EMP-1007", "employee_name": "Julian Barnes", "department": "Marketing", "date": today_str, "status": "Absent", "check_in": "-", "check_out": "-", "working_hours": 0.0, "notes": "Unexcused absence"},
        {"employee_id": "EMP-1008", "employee_name": "Chloe Bennett", "department": "Sales", "date": today_str, "status": "Leave", "check_in": "-", "check_out": "-", "working_hours": 0.0, "notes": "Approved Casual Leave"}
    ]
    db.attendance.insert_many(attendance_records)

    # 6. Leaves
    leaves_data = [
        {
            "employee_id": "EMP-1008",
            "employee_name": "Chloe Bennett",
            "department": "Sales",
            "leave_type": "Casual Leave",
            "start_date": today_str,
            "end_date": (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "days_count": 3,
            "reason": "Personal family commitment and travel",
            "status": "Approved",
            "applied_at": datetime.utcnow() - timedelta(days=2),
            "reviewed_by": "Alex Mercer",
            "review_comment": "Approved as per company policy."
        },
        {
            "employee_id": "EMP-1003",
            "employee_name": "Sophia Chen",
            "department": "Marketing",
            "leave_type": "Sick Leave",
            "start_date": (datetime.utcnow() + timedelta(days=4)).strftime("%Y-%m-%d"),
            "end_date": (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d"),
            "days_count": 2,
            "reason": "Scheduled minor dental procedure and recovery",
            "status": "Pending",
            "applied_at": datetime.utcnow() - timedelta(hours=6),
            "reviewed_by": None,
            "review_comment": None
        },
        {
            "employee_id": "EMP-1006",
            "employee_name": "Aria Montgomery",
            "department": "Engineering",
            "leave_type": "Earned Leave",
            "start_date": (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "end_date": (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "days_count": 5,
            "reason": "Annual vacation trip with family",
            "status": "Pending",
            "applied_at": datetime.utcnow() - timedelta(hours=14),
            "reviewed_by": None,
            "review_comment": None
        },
        {
            "employee_id": "EMP-1005",
            "employee_name": "Liam Gallagher",
            "department": "Sales",
            "leave_type": "Casual Leave",
            "start_date": (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "end_date": (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d"),
            "days_count": 2,
            "reason": "Moving into new apartment",
            "status": "Approved",
            "applied_at": datetime.utcnow() - timedelta(days=18),
            "reviewed_by": "Alex Mercer",
            "review_comment": "Approved."
        }
    ]
    db.leaves.insert_many(leaves_data)

    # 7. Payroll
    current_month = datetime.utcnow().strftime("%B")
    current_year = datetime.utcnow().year
    payroll_data = [
        {
            "payroll_id": "PAY-2026-1001",
            "employee_id": "EMP-1001",
            "employee_name": "Marcus Vance",
            "department": "Engineering",
            "designation": "Lead Solutions Architect",
            "month": current_month,
            "year": current_year,
            "basic_salary": 8500.0,
            "hra": 2500.0,
            "allowances": 1200.0,
            "overtime_hours": 10.0,
            "overtime_pay": 500.0,
            "bonus": 1000.0,
            "gross_salary": 13700.0,
            "tax_deductions": 900.0,
            "other_deductions": 300.0,
            "total_deductions": 1200.0,
            "net_salary": 12500.0,
            "payment_status": "Paid",
            "payment_date": today_str,
            "payment_method": "Direct Bank Deposit",
            "created_at": datetime.utcnow()
        },
        {
            "payroll_id": "PAY-2026-1002",
            "employee_id": "EMP-1002",
            "employee_name": "Elena Rostova",
            "department": "Human Resources",
            "designation": "HR Director",
            "month": current_month,
            "year": current_year,
            "basic_salary": 7000.0,
            "hra": 2000.0,
            "allowances": 900.0,
            "overtime_hours": 0.0,
            "overtime_pay": 0.0,
            "bonus": 500.0,
            "gross_salary": 10400.0,
            "tax_deductions": 700.0,
            "other_deductions": 200.0,
            "total_deductions": 900.0,
            "net_salary": 9500.0,
            "payment_status": "Paid",
            "payment_date": today_str,
            "payment_method": "Direct Bank Deposit",
            "created_at": datetime.utcnow()
        },
        {
            "payroll_id": "PAY-2026-1004",
            "employee_id": "EMP-1004",
            "employee_name": "David Sterling",
            "department": "Finance",
            "designation": "Chief Financial Officer",
            "month": current_month,
            "year": current_year,
            "basic_salary": 9500.0,
            "hra": 2800.0,
            "allowances": 1500.0,
            "overtime_hours": 0.0,
            "overtime_pay": 0.0,
            "bonus": 1500.0,
            "gross_salary": 15300.0,
            "tax_deductions": 1200.0,
            "other_deductions": 400.0,
            "total_deductions": 1600.0,
            "net_salary": 13700.0,
            "payment_status": "Paid",
            "payment_date": today_str,
            "payment_method": "Direct Bank Deposit",
            "created_at": datetime.utcnow()
        }
    ]
    db.payroll.insert_many(payroll_data)

    # 8. Performance Reviews
    reviews_data = [
        {
            "employee_id": "EMP-1001",
            "employee_name": "Marcus Vance",
            "department": "Engineering",
            "reviewer_name": "Alex Mercer",
            "review_period": "Q3 2026",
            "rating": 5,
            "productivity_score": 96.5,
            "task_completion_rate": 98.0,
            "communication_rating": 4.8,
            "technical_competence": 5.0,
            "remarks": "Exceptional leadership in architecting the core cloud infrastructure. Consistently exceeds sprint targets.",
            "review_date": (datetime.utcnow() - timedelta(days=12)).strftime("%Y-%m-%d"),
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1002",
            "employee_name": "Elena Rostova",
            "department": "Human Resources",
            "reviewer_name": "Alex Mercer",
            "review_period": "Q3 2026",
            "rating": 4,
            "productivity_score": 91.0,
            "task_completion_rate": 94.0,
            "communication_rating": 5.0,
            "technical_competence": 4.5,
            "remarks": "Excellent talent retention programs implemented this quarter. Employee satisfaction rating up by 18%.",
            "review_date": (datetime.utcnow() - timedelta(days=15)).strftime("%Y-%m-%d"),
            "created_at": datetime.utcnow()
        },
        {
            "employee_id": "EMP-1006",
            "employee_name": "Aria Montgomery",
            "department": "Engineering",
            "reviewer_name": "Marcus Vance",
            "review_period": "Q3 2026",
            "rating": 5,
            "productivity_score": 94.0,
            "task_completion_rate": 97.5,
            "communication_rating": 4.7,
            "technical_competence": 4.9,
            "remarks": "High-velocity contributor. Delivered the RESTful API revamp 2 weeks ahead of scheduled deadline.",
            "review_date": (datetime.utcnow() - timedelta(days=20)).strftime("%Y-%m-%d"),
            "created_at": datetime.utcnow()
        }
    ]
    db.performance_reviews.insert_many(reviews_data)

    # 9. Activities
    activities_data = [
        {"action": "Demo Data Initialized", "details": "System pre-populated with standard organization dataset", "admin_name": "Alex Mercer", "admin_email": "admin@ems.com", "created_at": datetime.utcnow() - timedelta(minutes=15)},
        {"action": "Payroll Generated", "details": "Generated monthly payroll for Marcus Vance (EMP-1001)", "admin_name": "Alex Mercer", "admin_email": "admin@ems.com", "created_at": datetime.utcnow() - timedelta(minutes=10)},
        {"action": "Leave Approved", "details": "Approved Casual Leave request for Chloe Bennett (EMP-1008)", "admin_name": "Alex Mercer", "admin_email": "admin@ems.com", "created_at": datetime.utcnow() - timedelta(minutes=5)}
    ]
    db.activities.insert_many(activities_data)
    print("[Database] Demo data seeding completed successfully!")

def reset_demo_data(db):
    collections = ["admins", "employees", "departments", "attendance", "leaves", "payroll", "performance_reviews", "activities", "settings"]
    for col in collections:
        db[col].delete_many({})
    init_indexes(db)
    seed_all_data(db)
    return True
