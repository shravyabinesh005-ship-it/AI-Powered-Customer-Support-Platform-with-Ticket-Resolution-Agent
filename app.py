from flask import Flask, request, jsonify, render_template, redirect, session
import joblib
import sqlite3
from datetime import datetime

from severity_engine import determine_severity
from priority_engine import determine_priority


# ==========================================
# CREATE FLASK APP
# ==========================================

app = Flask(__name__)
app.secret_key = "supportpilot-secret-key"


# ==========================================
# LOAD AI MODEL
# ==========================================

model = joblib.load("ticket_classifier.joblib")


# ==========================================
# DATABASE FUNCTION
# ==========================================

def save_ticket(employee_name, department, description, category, severity, priority):

    connection = sqlite3.connect("supportpilot.db")

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO tickets
        (employee_name, department, description, category, severity, priority, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
        employee_name,
        department,
        description,
        category,
        severity,
        priority,
        "Open",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
))

    connection.commit()

    ticket_id = cursor.lastrowid

    connection.close()

    return ticket_id


# ==========================================
# TEST ROUTE
# ==========================================

@app.route("/")
def home():

    if "logged_in" not in session:
        return redirect("/login")

    return render_template("index.html")


# ==========================================
# TICKET SUBMISSION API
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Demo login credentials
        if username == "admin" and password == "admin123":

            session["logged_in"] = True

            return redirect("/")

        else:

            return render_template(
                "login.html",
                error="Invalid username or password"
            )

    return render_template("login.html")


@app.route("/submit", methods=["POST"])
def submit_ticket():

    data = request.get_json()

    employee_name = data.get("employee_name", "")
    department = data.get("department", "")
    description = data.get("description", "")

    if not description:
        return jsonify({
            "error": "Ticket description is required"
        }), 400


    # ------------------------------
    # AI CLASSIFICATION
    # ------------------------------

    category = model.predict([description])[0]


    # ------------------------------
    # SEVERITY
    # ------------------------------

    severity = determine_severity(description)


    # ------------------------------
    # BUSINESS IMPACT
    # ------------------------------

    impact = data.get("impact", "Single user")


    # ------------------------------
    # PRIORITY
    # ------------------------------

    priority = determine_priority(
        severity,
        impact
    )


    # ------------------------------
    # SAVE TO DATABASE
    # ------------------------------

    ticket_id = save_ticket(
        employee_name,
        department,
        description,
        category,
        severity,
        priority
    )


    # ------------------------------
    # RETURN RESULT
    # ------------------------------

    return jsonify({
        "ticket_id": ticket_id,
        "category": category,
        "severity": severity,
        "priority": priority,
        "status": "Open"
    })


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)