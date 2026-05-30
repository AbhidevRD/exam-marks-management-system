from flask import Flask, render_template, request, redirect, session, send_file, flash
from config import supabase
from services.auth_service import login_user
from services.admin_service import (
    get_admin_dashboard_data,
    add_student,
    add_marks,
    add_subject,
    add_exam
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
# RESET PASSWORD
# -----------------------
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        unique_id = request.form["unique_id"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match! ❌", "error")
            return redirect("/reset_password")

        # Check if user exists as student
        user_response = supabase.table("users") \
            .select("*") \
            .eq("unique_id", unique_id) \
            .eq("role", "student") \
            .execute()

        if not user_response.data:
            flash("Student with this Unique ID not found! ❌", "error")
            return redirect("/reset_password")

        # Update password hash
        hashed_password = generate_password_hash(new_password)
        supabase.table("users") \
            .update({"password_hash": hashed_password}) \
            .eq("unique_id", unique_id) \
            .eq("role", "student") \
            .execute()

        # Add audit log
        try:
            supabase.table("audit_logs").insert({
                "action_type": "RESET_PASSWORD",
                "description": f"Password reset for student unique ID: {unique_id}"
            }).execute()
        except Exception:
            pass

        flash("Password reset successfully! Please login with your new password. ✅", "success")
        return redirect("/")

    return render_template("reset_password.html")


# -----------------------
# ADMIN DASHBOARD
# -----------------------
@app.route('/admin')
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/")

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


@app.route('/admin/students')
def admin_students():
    if session.get("role") != "admin":
        return redirect("/")
    
    students = supabase.table("students").select("*").execute().data
    
    return render_template("admin_students.html", students=students)


@app.route('/admin/subjects')
def admin_subjects():
    if session.get("role") != "admin":
        return redirect("/")
    
    subjects = supabase.table("subjects").select("*").execute().data
    
    return render_template("admin_subjects.html", subjects=subjects)


@app.route('/admin/exams')
def admin_exams():
    if session.get("role") != "admin":
        return redirect("/")
    
    exams = supabase.table("exams").select("*").execute().data
    
    return render_template("admin_exams.html", exams=exams)


@app.route('/admin/marks')
def admin_marks():
    if session.get("role") != "admin":
        return redirect("/")
    
    students = supabase.table("students").select("*").execute().data
    subjects = supabase.table("subjects").select("*").execute().data
    exams = supabase.table("exams").select("*").execute().data
    
    return render_template(
        "admin_marks.html",
        students=students,
        subjects=subjects,
        exams=exams
    )


@app.route('/admin/downloads')
def admin_downloads():
    if session.get("role") != "admin":
        return redirect("/")
    
    students = supabase.table("students").select("*").execute().data
    subjects = supabase.table("subjects").select("*").execute().data
    exams = supabase.table("exams").select("*").execute().data
    
    return render_template(
        "admin_downloads.html",
        students=students,
        subjects=subjects,
        exams=exams
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


@app.route("/admin/view_marks")
def admin_view_marks():
    if session.get("role") != "admin":
        return redirect("/")

    marks = supabase.table("marks") \
        .select("*, students(*), subjects(*), exams(*)") \
        .execute().data
        
    students = supabase.table("students").select("*").execute().data
    subjects = supabase.table("subjects").select("*").execute().data
    exams = supabase.table("exams").select("*").execute().data
    
    classes = sorted(list(set(s["class"] for s in students if s.get("class"))))
    sections = sorted(list(set(s["section"] for s in students if s.get("section"))))
    
    return render_template(
        "admin_view_marks.html",
        marks=marks,
        students=students,
        subjects=subjects,
        exams=exams,
        classes=classes,
        sections=sections
    )


@app.route("/add_exam", methods=["POST"])
def create_exam():
    if session.get("role") != "admin":
        return redirect("/")

    exam_name = request.form["exam_name"]
    add_exam(exam_name)

    flash("Exam added successfully ✅", "success")
    return redirect("/admin/exams")


# -----------------------
# ADMIN EDIT/DELETE CRUD
# -----------------------
@app.route("/admin/edit_student/<id>", methods=["GET", "POST"])
def edit_student(id):
    if session.get("role") != "admin":
        return redirect("/")

    student_response = supabase.table("students").select("*").eq("id", id).execute()
    if not student_response.data:
        flash("Student not found ❌", "error")
        return redirect("/admin/students")
    
    student = student_response.data[0]
    
    user_response = supabase.table("users").select("*").eq("id", student["user_id"]).execute()
    user = user_response.data[0] if user_response.data else None

    if request.method == "POST":
        name = request.form["name"]
        student_class = request.form["class"]
        section = request.form["section"]
        unique_id = request.form["unique_id"]
        password = request.form.get("password")

        user_update = {"unique_id": unique_id}
        if password:
            user_update["password_hash"] = generate_password_hash(password)
            
        supabase.table("users").update(user_update).eq("id", student["user_id"]).execute()

        supabase.table("students").update({
            "name": name,
            "class": student_class,
            "section": section
        }).eq("id", id).execute()

        try:
            supabase.table("audit_logs").insert({
                "action_type": "EDIT_STUDENT",
                "description": f"Edited student: {name} (Class {student_class}-{section})"
            }).execute()
        except Exception:
            pass

        flash("Student updated successfully! ✅", "success")
        return redirect("/admin/students")

    return render_template("admin_edit_student.html", student=student, user=user)


@app.route("/admin/delete_student/<id>", methods=["POST"])
def delete_student(id):
    if session.get("role") != "admin":
        return redirect("/")

    student_response = supabase.table("students").select("*").eq("id", id).execute()
    if not student_response.data:
        flash("Student not found ❌", "error")
        return redirect("/admin/students")
    
    student = student_response.data[0]
    user_id = student["user_id"]
    student_name = student["name"]

    supabase.table("marks").delete().eq("student_id", id).execute()
    supabase.table("students").delete().eq("id", id).execute()
    supabase.table("users").delete().eq("id", user_id).execute()

    try:
        supabase.table("audit_logs").insert({
            "action_type": "DELETE_STUDENT",
            "description": f"Deleted student: {student_name}"
        }).execute()
    except Exception:
        pass

    flash("Student and all associated records deleted successfully! ✅", "success")
    return redirect("/admin/students")


@app.route("/admin/edit_subject/<id>", methods=["GET", "POST"])
def edit_subject(id):
    if session.get("role") != "admin":
        return redirect("/")

    subject_response = supabase.table("subjects").select("*").eq("id", id).execute()
    if not subject_response.data:
        flash("Subject not found ❌", "error")
        return redirect("/admin/subjects")
    
    subject = subject_response.data[0]

    if request.method == "POST":
        subject_name = request.form["subject_name"]
        max_marks = request.form["max_marks"]

        supabase.table("subjects").update({
            "subject_name": subject_name,
            "max_marks": int(max_marks)
        }).eq("id", id).execute()

        try:
            supabase.table("audit_logs").insert({
                "action_type": "EDIT_SUBJECT",
                "description": f"Edited subject: {subject_name}"
            }).execute()
        except Exception:
            pass

        flash("Subject updated successfully! ✅", "success")
        return redirect("/admin/subjects")

    return render_template("admin_edit_subject.html", subject=subject)


@app.route("/admin/delete_subject/<id>", methods=["POST"])
def delete_subject(id):
    if session.get("role") != "admin":
        return redirect("/")

    subject_response = supabase.table("subjects").select("*").eq("id", id).execute()
    if not subject_response.data:
        flash("Subject not found ❌", "error")
        return redirect("/admin/subjects")
    
    subject_name = subject_response.data[0]["subject_name"]

    supabase.table("marks").delete().eq("subject_id", id).execute()
    supabase.table("subjects").delete().eq("id", id).execute()

    try:
        supabase.table("audit_logs").insert({
            "action_type": "DELETE_SUBJECT",
            "description": f"Deleted subject: {subject_name}"
        }).execute()
    except Exception:
        pass

    flash("Subject and associated marks deleted successfully! ✅", "success")
    return redirect("/admin/subjects")


@app.route("/admin/edit_exam/<id>", methods=["GET", "POST"])
def edit_exam(id):
    if session.get("role") != "admin":
        return redirect("/")

    exam_response = supabase.table("exams").select("*").eq("id", id).execute()
    if not exam_response.data:
        flash("Exam not found ❌", "error")
        return redirect("/admin/exams")
    
    exam = exam_response.data[0]

    if request.method == "POST":
        exam_name = request.form["exam_name"]

        supabase.table("exams").update({
            "exam_name": exam_name
        }).eq("id", id).execute()

        try:
            supabase.table("audit_logs").insert({
                "action_type": "EDIT_EXAM",
                "description": f"Edited exam: {exam_name}"
            }).execute()
        except Exception:
            pass

        flash("Exam updated successfully! ✅", "success")
        return redirect("/admin/exams")

    return render_template("admin_edit_exam.html", exam=exam)


@app.route("/admin/delete_exam/<id>", methods=["POST"])
def delete_exam(id):
    if session.get("role") != "admin":
        return redirect("/")

    exam_response = supabase.table("exams").select("*").eq("id", id).execute()
    if not exam_response.data:
        flash("Exam not found ❌", "error")
        return redirect("/admin/exams")
    
    exam_name = exam_response.data[0]["exam_name"]

    supabase.table("marks").delete().eq("exam_id", id).execute()
    supabase.table("exams").delete().eq("id", id).execute()

    try:
        supabase.table("audit_logs").insert({
            "action_type": "DELETE_EXAM",
            "description": f"Deleted exam: {exam_name}"
        }).execute()
    except Exception:
        pass

    flash("Exam and associated marks deleted successfully! ✅", "success")
    return redirect("/admin/exams")


@app.route("/admin/edit_mark/<id>", methods=["GET", "POST"])
def edit_mark(id):
    if session.get("role") != "admin":
        return redirect("/")

    mark_response = supabase.table("marks") \
        .select("*, students(*), subjects(*), exams(*)") \
        .eq("id", id) \
        .execute()
        
    if not mark_response.data:
        flash("Mark record not found ❌", "error")
        return redirect("/admin/view_marks")
    
    mark = mark_response.data[0]

    if request.method == "POST":
        marks_obtained = int(request.form["marks_obtained"])

        max_marks = mark["subjects"]["max_marks"] if mark.get("subjects") else 100
        if marks_obtained > max_marks:
            flash(f"Error: Marks obtained ({marks_obtained}) cannot exceed maximum marks ({max_marks})! ❌", "error")
            return redirect(f"/admin/edit_mark/{id}")

        supabase.table("marks").update({
            "marks_obtained": marks_obtained
        }).eq("id", id).execute()

        try:
            student_name = mark["students"]["name"] if mark.get("students") else "Unknown"
            subject_name = mark["subjects"]["subject_name"] if mark.get("subjects") else "Unknown"
            supabase.table("audit_logs").insert({
                "action_type": "EDIT_MARKS",
                "description": f"Updated marks for {student_name} in {subject_name} to {marks_obtained}"
            }).execute()
        except Exception:
            pass

        flash("Mark record updated successfully! ✅", "success")
        return redirect("/admin/view_marks")

    return render_template("admin_edit_mark.html", mark=mark)


@app.route("/admin/delete_mark/<id>", methods=["POST"])
def delete_mark(id):
    if session.get("role") != "admin":
        return redirect("/")

    mark_response = supabase.table("marks") \
        .select("*, students(*), subjects(*)") \
        .eq("id", id) \
        .execute()
        
    if not mark_response.data:
        flash("Mark record not found ❌", "error")
        return redirect("/admin/view_marks")
    
    mark = mark_response.data[0]
    student_name = mark["students"]["name"] if mark.get("students") else "Unknown"
    subject_name = mark["subjects"]["subject_name"] if mark.get("subjects") else "Unknown"

    supabase.table("marks").delete().eq("id", id).execute()

    try:
        supabase.table("audit_logs").insert({
            "action_type": "DELETE_MARKS",
            "description": f"Deleted marks for {student_name} in {subject_name}"
        }).execute()
    except Exception:
        pass

    flash("Mark record deleted successfully! ✅", "success")
    return redirect("/admin/view_marks")


@app.route("/admin/analytics")
def admin_analytics():
    if session.get("role") != "admin":
        return redirect("/")

    from services.analytics_service import get_analytics_data

    data = get_analytics_data()

    return render_template("admin_analytics.html", data=data)



@app.route("/download_all_excel")
def download_all_excel():
    if session.get("role") != "admin":
        return redirect("/")

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


@app.route("/download_subject_wise_excel", methods=["POST"])
def download_subject_wise_excel():
    if session.get("role") != "admin":
        return redirect("/")
    
    subject_id = request.form.get("subject_id")
    
    if not subject_id:
        flash("Please select a subject", "error")
        return redirect("/admin/downloads")
    
    # Get subject name
    subject = supabase.table("subjects").select("*").eq("id", subject_id).execute().data
    if not subject:
        flash("Subject not found", "error")
        return redirect("/admin/downloads")
    
    subject_name = subject[0]["subject_name"]
    
    # Fetch all students
    students = supabase.table("students").select("*").execute().data
    
    students_data = []
    
    for student in students:
        subject_marks = {subject_name: 0}
        
        # Fetch student marks for this subject
        marks = supabase.table("marks") \
            .select("marks_obtained") \
            .eq("student_id", student["id"]) \
            .eq("subject_id", subject_id) \
            .execute().data
        
        if marks:
            subject_marks[subject_name] = marks[0]["marks_obtained"]
        
        student_entry = {
            "name": student["name"],
            "subjects": subject_marks
        }
        
        students_data.append(student_entry)
    
    # Generate Excel
    from services.excel_service import generate_subject_wise_excel
    excel_file = generate_subject_wise_excel(students_data, subject_name)
    
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=f"{subject_name}_Marksheet.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/download_exam_wise_excel", methods=["POST"])
def download_exam_wise_excel():
    if session.get("role") != "admin":
        return redirect("/")
    
    exam_id = request.form.get("exam_id")
    
    if not exam_id:
        flash("Please select an exam", "error")
        return redirect("/admin/downloads")
    
    # Get exam name
    exam = supabase.table("exams").select("*").eq("id", exam_id).execute().data
    if not exam:
        flash("Exam not found", "error")
        return redirect("/admin/downloads")
    
    exam_name = exam[0]["exam_name"]
    
    # Fetch all subjects
    subjects = supabase.table("subjects").select("*").execute().data
    subject_names = [s["subject_name"] for s in subjects]
    
    # Fetch all students
    students = supabase.table("students").select("*").execute().data
    
    students_data = []
    
    for student in students:
        subject_marks = {subject: 0 for subject in subject_names}
        
        # Fetch student marks for this exam
        marks = supabase.table("marks") \
            .select("marks_obtained, subjects(subject_name)") \
            .eq("student_id", student["id"]) \
            .eq("exam_id", exam_id) \
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
    from services.excel_service import generate_exam_wise_excel
    excel_file = generate_exam_wise_excel(students_data, subject_names, exam_name)
    
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=f"{exam_name}_Marksheet.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/download_student_wise_excel", methods=["POST"])
def download_student_wise_excel():
    if session.get("role") != "admin":
        return redirect("/")
    
    student_id = request.form.get("student_id")
    
    if not student_id:
        flash("Please select a student", "error")
        return redirect("/admin/downloads")
    
    # Get student
    student = supabase.table("students").select("*").eq("id", student_id).execute().data
    if not student:
        flash("Student not found", "error")
        return redirect("/admin/downloads")
    
    student_name = student[0]["name"]
    
    # Fetch all subjects
    subjects = supabase.table("subjects").select("*").execute().data
    subject_names = [s["subject_name"] for s in subjects]
    
    # Create subject marks dictionary
    subject_marks = {subject: 0 for subject in subject_names}
    
    # Fetch student marks
    marks = supabase.table("marks") \
        .select("marks_obtained, subjects(subject_name)") \
        .eq("student_id", student_id) \
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
    
    student_data = {
        "name": student_name,
        "subjects": subject_marks,
        "total": total,
        "average": average,
        "grade": grade,
        "result": result
    }
    
    # Generate Excel
    from services.excel_service import generate_student_wise_excel
    excel_file = generate_student_wise_excel(student_data, subject_names)
    
    return send_file(
        excel_file,
        as_attachment=True,
        download_name=f"{student_name}_Marksheet.xlsx",
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