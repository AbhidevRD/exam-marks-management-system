from flask import Flask, render_template, request, redirect, session, send_file, flash
from config import supabase
from services.auth_service import login_user
from services.admin_service import (
    get_admin_dashboard_data,
    add_student,
    add_marks,
    add_subject
)
from services.student_service import get_student_dashboard_data
from services.pdf_service import generate_marksheet
from services.code_generator import generate_student_code
from werkzeug.security import generate_password_hash
import os
from services.admin_service import (
    get_top_students,
    get_recent_activity,
    get_pass_rate)
from services.excel_service import generate_all_students_excel
from flask import send_file

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")


# -----------------------
# LOGIN
# -----------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        unique_id = request.form["unique_id"]
        password = request.form["password"]
        role = request.form["role"]   # 🔥 get selected role

        # Pass role to service
        user = login_user(unique_id, password, role)

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin")
            else:
                return redirect("/student")

        flash("Invalid Credentials ❌")
        return redirect("/")

    return render_template("login.html")


# -----------------------
# REGISTER (Student Signup)
# -----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        student_class = request.form["class"]
        section = request.form["section"]
        unique_id = request.form["unique_id"]
        password = request.form["password"]

        # Check if user exists
        existing_user = supabase.table("users") \
            .select("*") \
            .eq("unique_id", unique_id) \
            .execute()

        if existing_user.data:
            flash("User ID already exists!")
            return redirect("/register")

        hashed_password = generate_password_hash(password)

        # Insert user
        user = supabase.table("users").insert({
            "unique_id": unique_id,
            "password_hash": hashed_password,
            "role": "student"
        }).execute()

        user_id = user.data[0]["id"]

        # Generate student code
        student_code = generate_student_code()

        # Insert student
        supabase.table("students").insert({
            "user_id": user_id,
            "student_code": student_code,
            "name": name,
            "class": student_class,
            "section": section
        }).execute()

        flash("Registration successful! Please login.")
        return redirect("/")

    return render_template("register.html")


# -----------------------
# ADMIN DASHBOARD
# -----------------------
@app.route('/admin')
def admin_dashboard():

    students = supabase.table("students").select("*").execute().data
    subjects = supabase.table("subjects").select("*").execute().data
    exams = supabase.table("exams").select("*").execute().data

    # ✅ Supabase version
    top_students = get_top_students(supabase)
    #recent_logs = get_recent_activity(supabase)
    recent_logs=[]
    pass_rate = get_pass_rate(supabase)

    return render_template(
        "admin_dashboard.html",
        students=students,
        subjects=subjects,
        exams=exams,
        top_students=top_students,
        recent_logs=recent_logs,
        pass_rate=pass_rate
        
    )

    return render_template(
    "admin_dashboard.html",
    students=students,
    subjects=subjects,
    exams=exams,
    top_students=top_students,
    recent_logs=recent_logs,
    pass_rate=pass_rate
)


@app.route("/add_subject", methods=["POST"])
def add_subject_route():
    if session.get("role") != "admin":
        return redirect("/")

    subject_name = request.form["subject_name"]
    max_marks = request.form["max_marks"]

    add_subject(subject_name, max_marks)

    flash("Subject added successfully ✅", "success")
    return redirect("/admin")

@app.route("/add_student", methods=["POST"])
def create_student():
    if session.get("role") != "admin":
        return redirect("/")

    add_student(
        request.form["name"],
        request.form["class"],
        request.form["section"],
        request.form["unique_id"],
        request.form["password"]
    )

    flash("Student added successfully ✅", "success")
    return redirect("/admin")


@app.route("/add_marks", methods=["POST"])
def create_marks():
    if session.get("role") != "admin":
        return redirect("/")

    add_marks(
        request.form["student_id"],
        request.form["subject_id"],
        request.form["exam_id"],
        int(request.form["marks"])
    )

    flash("Marks added successfully ✅", "success")
    return redirect("/admin")

    

@app.route("/admin/analytics")
def admin_analytics():
    if session.get("role") != "admin":
        return redirect("/")

    from services.analytics_service import get_analytics_data

    data = get_analytics_data()

    return render_template("admin_analytics.html", data=data)



@app.route("/download_all_excel")
def download_all_excel():

    # Fetch all subjects dynamically
    subjects = supabase.table("subjects").select("*").execute().data
    subject_names = [s["subject_name"] for s in subjects]

    # Fetch all students
    students = supabase.table("students").select("*").execute().data

    students_data = []

    for student in students:

        # Create subject dictionary initialized to 0
        subject_marks = {subject: 0 for subject in subject_names}

        # Fetch student marks with subject name
        marks = supabase.table("marks") \
            .select("marks_obtained, subjects(subject_name)") \
            .eq("student_id", student["id"]) \
            .execute().data

        for m in marks:
            subject_name = m["subjects"]["subject_name"]
            subject_marks[subject_name] = m["marks_obtained"]

        # Calculate total & average
        total = sum(subject_marks.values())
        average = round(total / len(subject_names), 2) if subject_names else 0

        # Grade logic
        if average >= 90:
            grade = "A+"
        elif average >= 75:
            grade = "A"
        elif average >= 60:
            grade = "B"
        elif average >= 50:
            grade = "C"
        else:
            grade = "F"

        result = "PASS" if grade != "F" else "FAIL"

        student_entry = {
            "name": student["name"],
            "subjects": subject_marks,
            "total": total,
            "average": average,
            "grade": grade,
            "result": result
        }

        students_data.append(student_entry)

    # Generate Excel
    excel_file = generate_all_students_excel(students_data, subject_names)

    return send_file(
        excel_file,
        as_attachment=True,
        download_name="All_Students_Marksheet.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# -----------------------
# STUDENT DASHBOARD
# -----------------------
@app.route("/student")
def student_dashboard():

    if session.get("role") != "student":
        return redirect("/")

    if "user_id" not in session:
        return redirect("/")

    # Get dictionary data
    data = get_student_dashboard_data(session["user_id"])

    return render_template(
        "student_dashboard.html",
        student=data["student"],
        marks=data["marks"],
        total=data["total"],
        percentage=data["percentage"],
        rank=data["rank"],
        status=data["status"],
        exam_name=data["exam_name"]
    )
@app.route("/download_marksheet")
def download_marksheet():
    if session.get("role") != "student":
        return redirect("/")

    data = get_student_dashboard_data(session["user_id"])

    student = data["student"]
    marks = data["marks"]
    total = data["total"]
    percentage = data["percentage"]
    rank = data["rank"]
    status = data["status"]
    exam_name = data["exam_name"]
    
    pdf = generate_marksheet(data)

    return send_file(pdf,
                     as_attachment=True,
                     download_name="marksheet.pdf")


# -----------------------
# DATABASE TEST
# -----------------------
@app.route("/test_db")
def test_db():
    try:
        response = supabase.table("users").select("*").execute()
        return {
            "status": "Database Connected",
            "rows_found": len(response.data)
        }
    except Exception as e:
        return {
            "status": "Database Error",
            "message": str(e)
        }




@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully ✅", "success")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)