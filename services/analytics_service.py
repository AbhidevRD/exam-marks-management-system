from config import supabase

def get_analytics_data():

    # 🔹 Subject-wise average
    subject_avg = supabase.rpc("subject_average", {}).execute().data

    # 🔹 Top 5 students
    top_students = supabase.rpc("top_students", {}).execute().data

    # 🔹 Pass vs Fail
    pass_fail = supabase.rpc("pass_fail_stats", {}).execute().data

    return {
        "subject_avg": subject_avg or [],
        "top_students": top_students or [],
        "pass_fail": pass_fail or []
    }