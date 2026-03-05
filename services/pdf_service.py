from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import io


def calculate_grade(marks):
    if marks >= 90:
        return "A+"
    elif marks >= 80:
        return "A"
    elif marks >= 70:
        return "B"
    elif marks >= 60:
        return "C"
    elif marks >= 50:
        return "D"
    else:
        return "F"


def generate_marksheet(data):
    """
    data = {
        student,
        marks,
        total,
        percentage,
        rank,
        status,
        exam_name
    }
    """

    student = data["student"]
    marks = data["marks"]
    total = data["total"]
    percentage = data["percentage"]
    rank = data["rank"]
    status = data["status"]
    exam_name = data["exam_name"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        alignment=1,
        textColor=colors.darkblue
    )

    # 🔹 Title
    elements.append(Paragraph("JNV Tumkur", title_style))
    elements.append(Paragraph("Certificate of Marks", title_style))
    elements.append(Spacer(1, 16))

    # 🔹 Student Info
    elements.append(Paragraph(f"<b>Student Name:</b> {student['name']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Student ID:</b> {student.get('student_code', '')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Class:</b> {student['class']} &nbsp;&nbsp; <b>Section:</b> {student['section']}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Exam:</b> {exam_name}", styles["Normal"]))
    elements.append(Spacer(1, 16))

    # 🔹 Marks Table
    table_data = [["Subject", "Marks", "Grade"]]

    for m in marks:
        subject_name = m["subjects"]["subject_name"]
        marks_obtained = m["marks_obtained"]
        grade = calculate_grade(marks_obtained)

        table_data.append([
            subject_name,
            str(marks_obtained),
            grade
        ])

    table_data.append(["", "", ""])
    table_data.append(["Total", str(total), ""])

    table = Table(table_data, colWidths=[240, 100, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E3F2FD")),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # 🔹 Summary
    elements.append(Paragraph(f"<b>Percentage:</b> {percentage}%", styles["Normal"]))
    elements.append(Paragraph(f"<b>Rank:</b> {rank if rank else 'N/A'}", styles["Normal"]))

    status_color = "green" if status == "Pass" else "red"

    elements.append(
    Paragraph(
        f"<b>Status:</b> <font color='{status_color}'>{status}</font>",
        styles["Normal"]
    )
)

    # 🔹 Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "Congrajulations on completing the exam! Keep up the good work.",
        ParagraphStyle("footer", alignment=1, textColor=colors.grey)
    ))

    doc.build(elements)
    buffer.seek(0)

    return buffer