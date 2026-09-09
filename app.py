from flask import Flask, request, jsonify, render_template, redirect, make_response
import time
from metrics import MetricsTracker
import joblib
import sqlite3
from datetime import datetime, timedelta, timezone
import os
import pandas as pd
import jwt
from functools import wraps
from dotenv import load_dotenv

from severity_engine import determine_severity
from priority_engine import determine_priority
from rag.generator import ResolutionGenerator


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# FLASK APPLICATION
# ==========================================

app = Flask(__name__)


# ==========================================
# JWT CONFIGURATION
# ==========================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing. "
        "Please add it to your .env file."
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 1
JWT_COOKIE_NAME = "supportpilot_token"


# ==========================================
# JWT AUTHENTICATION DECORATOR
# ==========================================

def jwt_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        token = request.cookies.get(
            JWT_COOKIE_NAME
        )

        if not token:

            # API requests should receive JSON
            if request.path in ["/submit", "/feedback"]:

                return jsonify({
                    "error":
                        "Authentication required. Please log in."
                }), 401

            return redirect("/login")


        try:

            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )

            # Store authenticated username
            request.current_user = payload.get(
                "sub"
            )

        except jwt.ExpiredSignatureError:

            if request.path in ["/submit", "/feedback"]:

                return jsonify({
                    "error":
                        "Your session has expired. Please log in again."
                }), 401

            return redirect("/login")

        except jwt.InvalidTokenError:

            if request.path in ["/submit", "/feedback"]:

                return jsonify({
                    "error":
                        "Invalid authentication token. Please log in again."
                }), 401

            return redirect("/login")


        return function(*args, **kwargs)

    return decorated_function


# ==========================================
# LOAD AI MODEL
# ==========================================

model = joblib.load(
    "ticket_classifier.joblib"
)

resolution_generator = ResolutionGenerator()

metrics_tracker = MetricsTracker()


# ==========================================
# LOAD REAL RETRIEVAL ACCURACY
# ==========================================

def load_retrieval_accuracy():

    evaluation_file = (
        "retrieval_evaluation_results.csv"
    )

    if not os.path.exists(
        evaluation_file
    ):

        return 0


    try:

        df = pd.read_csv(
            evaluation_file
        )

        if len(df) == 0:

            return 0


        correct_retrievals = (
            df["Correct"]
            .astype(str)
            .str.lower()
            .eq("true")
            .sum()
        )


        total_tickets = len(df)


        accuracy = (
            correct_retrievals /
            total_tickets
        ) * 100


        return round(
            accuracy,
            1
        )


    except Exception as error:

        print(
            "Could not load retrieval evaluation:",
            error
        )

        return 0


# Load the actual evaluated accuracy
RETRIEVAL_ACCURACY = (
    load_retrieval_accuracy()
)


# ==========================================
# SAVE TICKET TO DATABASE
# ==========================================

def save_ticket(
    employee_name,
    department,
    description,
    category,
    severity,
    priority
):

    connection = sqlite3.connect(
        "supportpilot.db"
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO tickets
        (
            employee_name,
            department,
            description,
            category,
            severity,
            priority,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            employee_name,
            department,
            description,
            category,
            severity,
            priority,
            "Open",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    connection.commit()

    ticket_id = cursor.lastrowid

    connection.close()

    return ticket_id


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
@jwt_required
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# LOGIN
# ==========================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        password = request.form.get(
            "password"
        )


        # --------------------------------------
        # CHECK LOGIN CREDENTIALS
        # --------------------------------------

        if (
            username == "admin"
            and
            password == "admin123"
        ):

            # ----------------------------------
            # CREATE JWT PAYLOAD
            # ----------------------------------

            now = datetime.now(
                timezone.utc
            )

            payload = {

                "sub":
                    username,

                "iat":
                    now,

                "exp":
                    now + timedelta(
                        hours=JWT_EXPIRATION_HOURS
                    )
            }


            # ----------------------------------
            # GENERATE JWT
            # ----------------------------------

            token = jwt.encode(
                payload,
                JWT_SECRET_KEY,
                algorithm=JWT_ALGORITHM
            )


            # ----------------------------------
            # REDIRECT TO DASHBOARD
            # ----------------------------------

            response = make_response(
                redirect("/")
            )


            # ----------------------------------
            # STORE JWT IN HTTPONLY COOKIE
            # ----------------------------------

            response.set_cookie(

                JWT_COOKIE_NAME,

                token,

                httponly=True,

                secure=False,

                samesite="Lax",

                max_age=(
                    JWT_EXPIRATION_HOURS *
                    60 *
                    60
                )
            )


            return response


        else:

            return render_template(
                "login.html",
                error="Invalid username or password"
            )


    return render_template(
        "login.html"
    )


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    response = make_response(
        redirect("/login")
    )

    response.delete_cookie(
        JWT_COOKIE_NAME
    )

    return response


# ==========================================
# SUBMIT SUPPORT TICKET
# ==========================================

@app.route(
    "/submit",
    methods=["POST"]
)
@jwt_required
def submit_ticket():

    data = request.get_json()

    employee_name = data.get(
        "employee_name",
        ""
    )

    department = data.get(
        "department",
        ""
    )

    description = data.get(
        "description",
        ""
    )

    impact = data.get(
        "impact",
        "Single user"
    )


    # --------------------------------------
    # VALIDATE DESCRIPTION
    # --------------------------------------

    if not description:

        return jsonify({
            "error":
                "Ticket description is required"
        }), 400


    # --------------------------------------
    # TICKET ANALYSIS
    # --------------------------------------

    category = model.predict(
        [description]
    )[0]

    severity = determine_severity(
        description
    )

    priority = determine_priority(
        severity,
        impact
    )


    # --------------------------------------
    # RAG PIPELINE
    # --------------------------------------

    start_time = time.time()

    resolution_result = (
        resolution_generator
        .generate_resolution(
            description
        )
    )

    response_time = (
        time.time() -
        start_time
    )


    # --------------------------------------
    # RECORD ACTUAL PROCESSING METRIC
    # --------------------------------------

    metrics_tracker.record_ticket(
        response_time=response_time
    )


    # --------------------------------------
    # GET RAG RESULTS
    # --------------------------------------

    resolution = (
        resolution_result.get(
            "resolution",
            "No resolution generated."
        )
    )

    sources = (
        resolution_result.get(
            "sources",
            []
        )
    )

    query = (
        resolution_result.get(
            "query",
            description
        )
    )

    context = (
        resolution_result.get(
            "context",
            ""
        )
    )

    workflow = (
        resolution_result.get(
            "workflow",
            {}
        )
    )


    # --------------------------------------
    # SAVE TICKET
    # --------------------------------------

    ticket_id = save_ticket(
        employee_name,
        department,
        description,
        category,
        severity,
        priority
    )


    # --------------------------------------
    # GET CURRENT METRICS
    # --------------------------------------

    metrics = (
        metrics_tracker.get_metrics(
            retrieval_accuracy=
                RETRIEVAL_ACCURACY
        )
    )


    # ======================================
    # RETURN COMPLETE RESPONSE
    # ======================================

    return jsonify({

        "ticket_id":
            ticket_id,

        "category":
            category,

        "severity":
            severity,

        "priority":
            priority,

        "impact":
            impact,

        "status":
            "Open",

        "resolution":
            resolution,

        "sources":
            sources,

        "query":
            query,

        "context":
            context,

        "workflow":
            workflow,

        "metrics":
            metrics

    })


# ==========================================
# RESOLUTION FEEDBACK
# ==========================================

@app.route(
    "/feedback",
    methods=["POST"]
)
@jwt_required
def feedback():

    data = request.get_json()

    resolved = data.get(
        "resolved",
        False
    )


    # Make sure the value is Boolean
    resolved = bool(
        resolved
    )


    # Record actual user feedback
    metrics_tracker.record_feedback(
        resolved=resolved
    )


    # Return updated metrics
    metrics = (
        metrics_tracker.get_metrics(
            retrieval_accuracy=
                RETRIEVAL_ACCURACY
        )
    )


    return jsonify({

        "success": True,

        "metrics":
            metrics

    })


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )