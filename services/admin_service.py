from config import supabase
from services.code_generator import (
    generate_student_code,
    generate_subject_code
)
from werkzeug.security import generate_password_hash
import uuid

# =========================================
# ADMIN DASHBOARD DATA
# =========================================
def get_admin_dashboard_data():
    students = supabase.table("students") \
        .select("*") \
        .execute()

    exams = supabase.table("exams") \
        .select("*") \
        .execute()

    subjects = supabase.table("subjects") \
        .select("*") \
        .execute()

    return students.data, exams.data, subjects.data


# =========================================
# ADD SUBJECT
# =========================================
def add_subject(subject_name, max_marks):
    

    supabase.table("subjects").insert({
    
        "subject_name": subject_name,
        "max_marks": int(max_marks)
    }).execute()

    supabase.table("students").insert({
    "user_id": user_id,
    "name": name,
    "class": student_class,
    "section": section
    }).execute()


# =========================================
# ADD STUDENT (Admin creates student)
# =========================================
def generate_student_code():
    return "STU-" + str(uuid.uuid4())[:8].upper()


def add_student(name, student_class, section, unique_id, password):

    # 1️⃣ Hash password
    hashed_password = generate_password_hash(password)

    # 2️⃣ Insert into users table
    user = supabase.table("users").insert({
        "unique_id": unique_id,
        "password_hash": hashed_password,
        "role": "student"
    }).execute()

    user_id = user.data[0]["id"]

    # 3️⃣ Generate student code
    student_code = generate_student_code()

    # 4️⃣ Insert into students table
    supabase.table("students").insert({
        "user_id": user_id,
        "name": name,
        "class": student_class,
        "section": section,
        "student_code": student_code   # 🔥 THIS WAS MISSING
    }).execute()
    supabase.table("audit_logs").insert({
        "action_type": "ADD_STUDENT",
        "description": f"New student added: {name}"
    }).execute()
    


# =========================================
# ADD MARKS
# =========================================
def add_marks(student_id, subject_id, exam_id, marks):

    # 1️⃣ Insert marks
    supabase.table("marks").insert({
        "student_id": student_id,
        "subject_id": subject_id,
        "exam_id": exam_id,
        "marks_obtained": marks
    }).execute()

    # 2️⃣ Get student name
    student = supabase.table("students") \
        .select("name") \
        .eq("id", student_id) \
        .single() \
        .execute()

    student_name = student.data["name"] if student.data else "Unknown"

    # 3️⃣ Insert audit log
    supabase.table("audit_logs").insert({
        "action_type": "ADD_MARKS",
        "description": f"Marks added for {student_name}"
    }).execute()

    

def get_top_students(supabase):
    marks = supabase.table("marks").select("student_id, marks_obtained").execute().data

    totals = {}

    for m in marks:
        sid = m["student_id"]
        totals[sid] = totals.get(sid, 0) + m["marks_obtained"]

    # Sort by total descending
    sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:5]

    result = []

    for sid, total in sorted_totals:
        student = supabase.table("students").select("name").eq("id", sid).single().execute().data
        if student:
            result.append({
                "name": student["name"],
                "total": total
            })

    return result

def get_recent_activity(supabase):
    logs = supabase.table("audit_logs") \
        .select("action_type, description, created_at") \
        .order("created_at", desc=True) \
        .limit(5) \
        .execute()

    return logs.data

def get_pass_rate(supabase):
    marks = supabase.table("marks").select("student_id, marks_obtained").execute().data

    student_results = {}

    for m in marks:
        sid = m["student_id"]
        student_results.setdefault(sid, []).append(m["marks_obtained"])

    total_students = len(student_results)
    passed = 0

    for scores in student_results.values():
        if all(score >= 40 for score in scores):
            passed += 1

    if total_students == 0:
        return 0

    return round((passed / total_students) * 100, 2)