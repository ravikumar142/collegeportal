
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime
import os

# Optional: Google Sheet sync
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GS_ENABLED = True
except:
    GS_ENABLED = False

app = Flask(__name__)
app.secret_key = "secret123"

DATA_FILE = "data.xlsx"

# ---------- Google Sheet Sync ----------
def sync_from_google_sheet():
    if not GS_ENABLED:
        return
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("HostelData").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.to_excel(DATA_FILE, index=False)

# ---------- Auto dues calculation ----------
def calculate_dues(row):
    total = row.get("Total Payable", 0)
    paid = row.get("Total Paid", 0)
    due = total - paid
    refund = abs(due) if due < 0 else 0
    due = due if due > 0 else 0
    return total, paid, due, refund

# ---------- PDF Generation ----------
def generate_pdf(student):
    styles = getSampleStyleSheet()
    filename = f"bill_{student['Reg No']}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []

    elements.append(Paragraph("ITM GIDA", styles["Title"]))
    elements.append(Paragraph("Hostel and Mess Bill", styles["Heading2"]))
    elements.append(Paragraph(datetime.now().strftime("%d-%b-%Y"), styles["Normal"]))
    elements.append(Spacer(1, 12))

    total, paid, due, refund = calculate_dues(student)

    data = [["Field", "Value"]]
    for k, v in student.items():
        data.append([k, str(v)])

    data += [
        ["Total Payable", total],
        ["Paid", paid],
        ["Due", due],
        ["Refund", refund],
    ]

    table = Table(data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
        ('GRID',(0,0),(-1,-1),0.5,colors.black),
        ('ALIGN',(0,0),(-1,-1),'CENTER')
    ]))

    elements.append(table)
    doc.build(elements)
    return filename

# ---------- Routes ----------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        reg = request.form["reg"]
        dob = request.form["dob"]

        df = pd.read_excel(DATA_FILE)
        student = df[(df["Reg No"]==reg) & (df["DOB"]==dob)]

        if not student.empty:
            session["reg"] = reg
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid login")

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    df = pd.read_excel(DATA_FILE)
    student = df[df["Reg No"]==session["reg"]].iloc[0].to_dict()
    totals = calculate_dues(student)
    return render_template("dashboard.html",
                           student=student,
                           totals=totals)

# ---------- Admin Panel ----------
@app.route("/admin", methods=["GET","POST"])
def admin():
    df = pd.read_excel(DATA_FILE)

    if request.method == "POST":
        reg = request.form["reg"]
        field = request.form["field"]
        value = request.form["value"]

        df.loc[df["Reg No"]==reg, field] = value
        df.to_excel(DATA_FILE, index=False)

    data = df.to_dict(orient="records")
    return render_template("admin.html", data=data)

# ---------- PDF Export ----------
@app.route("/export")
def export_pdf():
    df = pd.read_excel(DATA_FILE)
    student = df[df["Reg No"]==session["reg"]].iloc[0].to_dict()
    pdf = generate_pdf(student)
    return send_file(pdf, as_attachment=True)

# ---------- Payment Gateway Placeholder ----------
@app.route("/pay")
def pay():
    return "Payment gateway integration placeholder."

if __name__ == "__main__":
    app.run(debug=True)
