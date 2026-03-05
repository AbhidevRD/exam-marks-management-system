from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_student_code():
    students = supabase.table("students").select("student_code").execute()
    count = len(students.data) + 1
    return f"STU{count:03d}"

def generate_subject_code():
    subjects = supabase.table("subjects").select("subject_code").execute()
    count = len(subjects.data) + 1
    return f"SUB{count:03d}"

def generate_exam_code():
    exams = supabase.table("exams").select("exam_code").execute()
    count = len(exams.data) + 1
    return f"EXAM{count:03d}"