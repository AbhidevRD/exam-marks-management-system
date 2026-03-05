from config import supabase
from werkzeug.security import check_password_hash
from services.code_generator import generate_student_code
def login_user(unique_id, password, role):

    # Fetch user by unique_id AND role
    response = supabase.table("users") \
        .select("*") \
        .eq("unique_id", unique_id) \
        .eq("role", role) \
        .execute()

    if response.data:
        user = response.data[0]

        # Check hashed password
        if check_password_hash(user["password_hash"], password):
            return user

    return None
