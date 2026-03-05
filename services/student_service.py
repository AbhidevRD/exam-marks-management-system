from config import supabase


def get_student_dashboard_data(user_id):

    # 🔹 1️⃣ Get student details
    student_response = supabase.table("students") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    if not student_response.data:
        return {
            "student": None,
            "marks": [],
            "total": 0,
            "percentage": 0,
            "rank": None,
            "status": None,
            "exam_name": None
        }

    student = student_response.data[0]

    # 🔹 2️⃣ Get marks + subject + exam (JOIN style)
    marks_response = supabase.table("marks") \
        .select("*, subjects(subject_name, max_marks), exams(exam_name)") \
        .eq("student_id", student["id"]) \
        .execute()

    marks = marks_response.data if marks_response.data else []

    # 🔹 3️⃣ Calculate total and max_total
    total = 0
    max_total = 0

    for m in marks:
        total += m.get("marks_obtained", 0)

        # safer access to max_marks
        if m.get("subjects") and m["subjects"].get("max_marks"):
            max_total += m["subjects"]["max_marks"]

    # 🔹 4️⃣ Calculate percentage safely
    percentage = round((total / max_total) * 100, 2) if max_total > 0 else 0

    # 🔹 5️⃣ Pass / Fail logic
    status = "Pass" if percentage >= 35 else "Fail"

    # 🔹 6️⃣ Get exam name safely
    exam_name = None
    if marks and marks[0].get("exams"):
        exam_name = marks[0]["exams"].get("exam_name")

    # 🔹 7️⃣ Rank (only if exam exists)
    rank = None

    if marks:
        exam_id = marks[0].get("exam_id")

        if exam_id:
            rank_response = supabase.rpc(
                "calculate_rank",
                {"exam_uuid": exam_id}
            ).execute()

            if rank_response.data:
                for r in rank_response.data:
                    if r["student_id"] == student["id"]:
                        rank = r["rank"]
                        break

    # 🔹 8️⃣ Return dictionary (IMPORTANT)
    return {
        "student": student,
        "marks": marks,
        "total": total,
        "percentage": percentage,
        "rank": rank,
        "status": status,
        "exam_name": exam_name
    }