from flask import Blueprint, request
from bson import ObjectId
from datetime import datetime
from database import get_db
from utils.helpers import json_response, serialize_doc, serialize_docs, log_activity, auth_required
from utils.validators import validate_required_fields

performance_bp = Blueprint('performance', __name__, url_prefix='/api/performance')

@performance_bp.route('', methods=['GET'])
@auth_required
def list_performance():
    db = get_db()
    query = {}

    emp_id = request.args.get('employee_id', '').strip()
    department = request.args.get('department', '').strip()
    period = request.args.get('period', '').strip()
    min_rating = request.args.get('rating', '').strip()

    if emp_id:
        query["employee_id"] = emp_id
    if department and department != 'All':
        query["department"] = department
    if period and period != 'All':
        query["review_period"] = period
    if min_rating and min_rating != 'All':
        try:
            query["rating"] = int(min_rating)
        except ValueError:
            pass

    reviews = serialize_docs(db.performance_reviews.find(query).sort([("review_date", -1), ("created_at", -1)]))
    return json_response(reviews, "Performance reviews retrieved successfully")

@performance_bp.route('/analytics', methods=['GET'])
@auth_required
def get_performance_analytics():
    db = get_db()
    reviews = list(db.performance_reviews.find())
    departments = list(db.departments.find())

    dept_stats = []
    for dept in departments:
        dname = dept.get("name")
        d_reviews = [r for r in reviews if r.get("department") == dname]
        if d_reviews:
            avg_rating = round(sum(r.get("rating", 0) for r in d_reviews) / len(d_reviews), 2)
            avg_productivity = round(sum(r.get("productivity_score", 0) for r in d_reviews) / len(d_reviews), 1)
            avg_task_completion = round(sum(r.get("task_completion_rate", 0) for r in d_reviews) / len(d_reviews), 1)
        else:
            avg_rating = 0.0
            avg_productivity = 0.0
            avg_task_completion = 0.0

        dept_stats.append({
            "department": dname,
            "reviews_count": len(d_reviews),
            "avg_rating": avg_rating,
            "avg_productivity": avg_productivity,
            "avg_task_completion": avg_task_completion
        })

    # Overall top performers
    sorted_reviews = sorted(reviews, key=lambda r: (r.get("rating", 0), r.get("productivity_score", 0)), reverse=True)
    top_performers = serialize_docs(sorted_reviews[:5])

    total_reviews = len(reviews)
    avg_org_rating = round(sum(r.get("rating", 0) for r in reviews) / total_reviews, 2) if total_reviews > 0 else 0
    avg_org_productivity = round(sum(r.get("productivity_score", 0) for r in reviews) / total_reviews, 1) if total_reviews > 0 else 0

    return json_response({
        "department_analytics": dept_stats,
        "top_performers": top_performers,
        "total_reviews": total_reviews,
        "org_avg_rating": avg_org_rating,
        "org_avg_productivity": avg_org_productivity
    }, "Performance analytics retrieved successfully")

@performance_bp.route('/<rev_id>', methods=['GET'])
@auth_required
def get_review(rev_id):
    db = get_db()
    if not ObjectId.is_valid(rev_id):
        return json_response(None, "Invalid review ID", status=400, success=False)

    review = db.performance_reviews.find_one({"_id": ObjectId(rev_id)})
    if not review:
        return json_response(None, "Review not found", status=404, success=False)

    return json_response(serialize_doc(review), "Review retrieved successfully")

@performance_bp.route('', methods=['POST'])
@auth_required
def create_review():
    db = get_db()
    data = request.get_json() or {}

    missing = validate_required_fields(data, ['employee_id', 'rating', 'productivity_score', 'review_period'])
    if missing:
        return json_response(None, f"Missing required fields: {', '.join(missing)}", status=400, success=False)

    emp_id = data['employee_id'].strip()
    emp = db.employees.find_one({"employee_id": emp_id})
    if not emp:
        return json_response(None, f"Employee '{emp_id}' not found", status=404, success=False)

    admin_name = request.current_admin.get("name", "Admin") if hasattr(request, "current_admin") else "Admin"

    review = {
        "employee_id": emp_id,
        "employee_name": emp.get("name"),
        "department": emp.get("department"),
        "reviewer_name": data.get("reviewer_name", admin_name).strip(),
        "review_period": data.get("review_period", "Current").strip(),
        "rating": max(1, min(5, int(data.get("rating", 3)))),
        "productivity_score": max(0.0, min(100.0, float(data.get("productivity_score", 85)))),
        "task_completion_rate": max(0.0, min(100.0, float(data.get("task_completion_rate", 90)))),
        "communication_rating": max(1.0, min(5.0, float(data.get("communication_rating", 4.0)))),
        "technical_competence": max(1.0, min(5.0, float(data.get("technical_competence", 4.0)))),
        "remarks": data.get("remarks", "").strip(),
        "review_date": data.get("review_date", datetime.utcnow().strftime("%Y-%m-%d")),
        "created_at": datetime.utcnow()
    }
    result = db.performance_reviews.insert_one(review)
    review["_id"] = result.inserted_id

    log_activity(db, "Performance Review Added", f"Added {review['review_period']} evaluation for {emp.get('name')}")
    return json_response(serialize_doc(review), "Performance review added successfully", status=201)

@performance_bp.route('/<rev_id>', methods=['PUT'])
@auth_required
def update_review(rev_id):
    db = get_db()
    if not ObjectId.is_valid(rev_id):
        return json_response(None, "Invalid review ID", status=400, success=False)

    existing = db.performance_reviews.find_one({"_id": ObjectId(rev_id)})
    if not existing:
        return json_response(None, "Review not found", status=404, success=False)

    data = request.get_json() or {}
    update_data = {}

    for field in ['review_period', 'reviewer_name', 'remarks', 'review_date']:
        if field in data:
            update_data[field] = data[field]

    if 'rating' in data:
        update_data['rating'] = max(1, min(5, int(data['rating'])))
    if 'productivity_score' in data:
        update_data['productivity_score'] = max(0.0, min(100.0, float(data['productivity_score'])))
    if 'task_completion_rate' in data:
        update_data['task_completion_rate'] = max(0.0, min(100.0, float(data['task_completion_rate'])))
    if 'communication_rating' in data:
        update_data['communication_rating'] = max(1.0, min(5.0, float(data['communication_rating'])))
    if 'technical_competence' in data:
        update_data['technical_competence'] = max(1.0, min(5.0, float(data['technical_competence'])))

    update_data['updated_at'] = datetime.utcnow()
    db.performance_reviews.update_one({"_id": ObjectId(rev_id)}, {"$set": update_data})

    updated = db.performance_reviews.find_one({"_id": ObjectId(rev_id)})
    log_activity(db, "Performance Review Updated", f"Updated review for {existing.get('employee_name')}")
    return json_response(serialize_doc(updated), "Review updated successfully")

@performance_bp.route('/<rev_id>', methods=['DELETE'])
@auth_required
def delete_review(rev_id):
    db = get_db()
    if not ObjectId.is_valid(rev_id):
        return json_response(None, "Invalid review ID", status=400, success=False)

    existing = db.performance_reviews.find_one({"_id": ObjectId(rev_id)})
    if not existing:
        return json_response(None, "Review not found", status=404, success=False)

    db.performance_reviews.delete_one({"_id": ObjectId(rev_id)})
    log_activity(db, "Performance Review Deleted", f"Deleted review for {existing.get('employee_name')}")
    return json_response(None, "Performance review deleted successfully")
