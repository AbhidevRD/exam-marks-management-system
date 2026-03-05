from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from io import BytesIO

def generate_all_students_excel(students_data, subject_names):

    wb = Workbook()
    ws = wb.active
    ws.title = "All Students Marksheet"

    # Header
    headers = ["Sr No", "Name"] + subject_names + ["Total", "Average", "Grade", "Result"]
    ws.append(headers)

    # Style header
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # Insert student rows
    for index, student in enumerate(students_data, start=1):

        subject_values = [student["subjects"][sub] for sub in subject_names]

        row = [
            index,
            student["name"],
            *subject_values,
            student["total"],
            student["average"],
            student["grade"],
            student["result"]
        ]

        ws.append(row)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer