from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    make_response
)

import time
import os
import sqlite3

from datetime import datetime, timedelta, timezone
from functools import wraps

import joblib
import pandas as pd
import jwt

from dotenv import load_dotenv

from metrics import MetricsTracker
from severity_engine import determine_severity
from priority_engine import determine_priority
from rag.generator import ResolutionGenerator
from agents import SupportPilot


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)


# =========================================================
# JWT CONFIGURATION
# =========================================================

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is missing. "
        "Please add it to your .env file."
    )

JWT_ALGORITHM = "HS256"

JWT_EXPIRATION_HOURS = 1

JWT_COOKIE_NAME = "supportpilot_token"


# =========================================================
# JWT AUTHENTICATION DECORATOR
# =========================================================

def jwt_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        token = request.cookies.get(
            JWT_COOKIE_NAME
        )

        if not token:

            if request.path in [
                "/submit",
                "/feedback",
                "/api/multi-agent"
            ]:
                return jsonify({
                    "error":
                        "Authentication required. "
                        "Please log in."
                }), 401

            return redirect("/login")

        try:

            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )

            request.current_user = payload.get(
                "sub"
            )

        except jwt.ExpiredSignatureError:

            if request.path in [
                "/submit",
                "/feedback",
                "/api/multi-agent"
            ]:
                return jsonify({
                    "error":
                        "Your session has expired. "
                        "Please log in again."
                }), 401

            return redirect("/login")

        except jwt.InvalidTokenError:

            if request.path in [
                "/submit",
                "/feedback",
                "/api/multi-agent"
            ]:
                return jsonify({
                    "error":
                        "Invalid authentication token. "
                        "Please log in again."
                }), 401

            return redirect("/login")

        return function(*args, **kwargs)

    return decorated_function


# =========================================================
# LOAD AI MODEL
# =========================================================

model = joblib.load(
    "ticket_classifier.joblib"
)


# =========================================================
# MILESTONE 2 RAG
# =========================================================

resolution_generator = ResolutionGenerator()


# =========================================================
# MILESTONE 3 MULTI-AGENT SYSTEM
# =========================================================

multi_agent_system = SupportPilot()


# =========================================================
# METRICS
# =========================================================

metrics_tracker = MetricsTracker()


# =========================================================
# LOAD REAL RETRIEVAL ACCURACY
# =========================================================

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


RETRIEVAL_ACCURACY = (
    load_retrieval_accuracy()
)


# =========================================================
# SAVE TICKET TO DATABASE
# =========================================================

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


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
@jwt_required
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# LOGIN
# =========================================================

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

        if (
            username == "admin"
            and
            password == "admin123"
        ):

            now = datetime.now(
                timezone.utc
            )

            payload = {
                "sub": username,
                "iat": now,
                "exp":
                    now + timedelta(
                        hours=JWT_EXPIRATION_HOURS
                    )
            }

            token = jwt.encode(
                payload,
                JWT_SECRET_KEY,
                algorithm=JWT_ALGORITHM
            )

            response = make_response(
                redirect("/")
            )

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


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    response = make_response(
        redirect("/login")
    )

    response.delete_cookie(
        JWT_COOKIE_NAME
    )

    return response


# =========================================================
# SUBMIT SUPPORT TICKET
# =========================================================

@app.route(
    "/submit",
    methods=["POST"]
)
@jwt_required
def submit_ticket():

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Invalid request data."
        }), 400

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

    recipient_email = data.get(
        "email",
        ""
    )

    if not recipient_email:

        recipient_email = os.getenv(
            "SMTP_EMAIL"
        )

    # --------------------------------------
    # VALIDATE DESCRIPTION
    # --------------------------------------

    if not description:

        return jsonify({
            "error":
                "Ticket description is required"
        }), 400


    # =====================================================
    # MILESTONE 1: TICKET ANALYSIS
    # =====================================================

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


    # =====================================================
    # MILESTONE 2: RAG PIPELINE
    # =====================================================

    start_time = time.time()

    try:

        resolution_result = (
            resolution_generator
            .generate_resolution(
                description
            )
        )

    except Exception as error:

        print(
            "RAG processing error:",
            error
        )

        resolution_result = {
            "resolution":
                "The AI resolution service "
                "could not complete the request. "
                "Additional investigation is required.",
            "sources": [],
            "query": description,
            "context": "",
            "workflow": {
                "ticket_analysis": "failed",
                "knowledge_retrieval": "failed",
                "context_augmentation": "failed",
                "resolution_generation": "failed"
            }
        }

    response_time = (
        time.time() -
        start_time
    )

    metrics_tracker.record_ticket(
        response_time=response_time
    )


    # --------------------------------------
    # GET RAG RESULTS SAFELY
    # --------------------------------------

    if not isinstance(
        resolution_result,
        dict
    ):
        resolution_result = {}

    resolution = (
        resolution_result.get(
            "resolution"
        )
        or
        "No resolution generated."
    )

    sources = (
        resolution_result.get(
            "sources"
        )
        or
        []
    )

    query = (
        resolution_result.get(
            "query"
        )
        or
        description
    )

    context = (
        resolution_result.get(
            "context"
        )
        or
        ""
    )

    workflow = (
        resolution_result.get(
            "workflow"
        )
        or
        {}
    )


    # =====================================================
    # MILESTONE 3: MULTI-AGENT WORKFLOW
    # =====================================================

    multi_agent_start = time.time()

    try:

        multi_agent_result = (
            multi_agent_system.process_ticket(
                description,
                recipient_email,
                priority
            )
        )

    except Exception as error:

        print(
            "Multi-agent processing error:",
            error
        )

        multi_agent_result = {

            "diagnosis": {
                "category":
                    "Multi-Agent Error",

                "diagnosis":
                    str(error),

                "confidence":
                    0
            },

            "retrieval": {
                "article":
                    None,

                "similarity":
                    0,

                "message":
                    "Retrieval failed."
            },

            "resolution": {
                "response":
                    "Multi-agent workflow "
                    "could not be completed.",

                "steps":
                    []
            },

            "validation": {
                "confidence":
                    0,

                "status":
                    "ESCALATE"
            },

            "escalation":
                True,

            "jira": {
                "success":
                    False,

                "message":
                    "Multi-agent processing failed."
            },

            "email": {
                "success":
                    False,

                "message":
                    "Multi-agent processing failed."
            },

            "priority":
                priority
        }


    multi_agent_time = (
        time.time() -
        multi_agent_start
    )


    # =====================================================
    # SAFELY EXTRACT MULTI-AGENT RESULTS
    # =====================================================

    if not isinstance(
        multi_agent_result,
        dict
    ):
        multi_agent_result = {}


    agent_diagnosis = (
        multi_agent_result.get(
            "diagnosis"
        )
        or
        {}
    )

    agent_retrieval = (
        multi_agent_result.get(
            "retrieval"
        )
        or
        {}
    )

    agent_resolution = (
        multi_agent_result.get(
            "resolution"
        )
        or
        {}
    )

    agent_validation = (
        multi_agent_result.get(
            "validation"
        )
        or
        {}
    )

    agent_escalation = bool(
        multi_agent_result.get(
            "escalation",
            False
        )
    )

    jira_result = (
        multi_agent_result.get(
            "jira"
        )
        or
        {}
    )

    email_result = (
        multi_agent_result.get(
            "email"
        )
        or
        {}
    )


    # =====================================================
    # IMPORTANT:
    # RETRIEVAL ARTICLE CAN BE NONE
    # =====================================================

    retrieved_article = (
        agent_retrieval.get(
            "article"
        )
        or
        {}
    )

    retrieved_article_title = (
        retrieved_article.get(
            "title"
        )
        or
        "No relevant article"
    )


    # =====================================================
    # COMBINED WORKFLOW INFORMATION
    # =====================================================

    multi_agent_workflow = {

        "diagnosis_agent": {

            "status":
                "COMPLETED",

            "category":
                agent_diagnosis.get(
                    "category",
                    ""
                ),

            "confidence":
                agent_diagnosis.get(
                    "confidence",
                    0
                )
        },


        "retrieval_agent": {

            "status":
                "COMPLETED",

            "article":
                retrieved_article_title,

            "similarity":
                round(
                    (
                        agent_retrieval.get(
                            "similarity",
                            0
                        )
                        or
                        0
                    ) * 100,
                    2
                )
        },


        "resolution_agent": {

            "status":
                "COMPLETED",

            "steps":
                agent_resolution.get(
                    "steps",
                    []
                )
                or
                []
        },


        "validation_agent": {

            "status":
                agent_validation.get(
                    "status",
                    "UNKNOWN"
                ),

            "confidence":
                agent_validation.get(
                    "confidence",
                    0
                )
                or
                0
        },


        "escalation_agent": {

            "status":
                "ESCALATED"
                if agent_escalation
                else
                "NOT REQUIRED"
        },


        "jira":
            jira_result,


        "email":
            email_result,


        "processing_time":
            round(
                multi_agent_time,
                3
            )
    }


    # =====================================================
    # SAVE TICKET
    # =====================================================

    ticket_id = save_ticket(

        employee_name,

        department,

        description,

        category,

        severity,

        priority
    )


    # =====================================================
    # GET CURRENT METRICS
    # =====================================================

    metrics = (
        metrics_tracker.get_metrics(
            retrieval_accuracy=
                RETRIEVAL_ACCURACY
        )
    )


    # =====================================================
    # RETURN COMPLETE RESPONSE
    # =====================================================

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


        # -----------------------------
        # MILESTONE 2 RAG
        # -----------------------------

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


        # -----------------------------
        # MILESTONE 3
        # -----------------------------

        "multi_agent":
            multi_agent_result,

        "multi_agent_workflow":
            multi_agent_workflow,


        # -----------------------------
        # METRICS
        # -----------------------------

        "metrics":
            metrics
    })


# =========================================================
# MULTI-AGENT API
# =========================================================

@app.route(
    "/api/multi-agent",
    methods=["POST"]
)
@jwt_required
def multi_agent_api():

    data = request.get_json()

    if not data:

        return jsonify({
            "error":
                "Invalid request data."
        }), 400


    ticket = data.get(
        "ticket",
        ""
    )

    recipient = data.get(
        "email",
        ""
    )

    impact = data.get(
        "impact",
        "Single user"
    )


    if not ticket:

        return jsonify({
            "error":
                "Ticket description is required."
        }), 400


    if not recipient:

        recipient = os.getenv(
            "SMTP_EMAIL"
        )


    # =====================================================
    # CALCULATE SEVERITY AND PRIORITY
    # =====================================================

    severity = determine_severity(
        ticket
    )

    priority = determine_priority(
        severity,
        impact
    )


    # =====================================================
    # RUN MULTI-AGENT SYSTEM
    # =====================================================

    start_time = time.time()

    try:

        result = (
            multi_agent_system.process_ticket(
                ticket,
                recipient,
                priority
            )
        )

    except Exception as error:

        print(
            "Multi-agent API error:",
            error
        )

        result = {

            "diagnosis": {
                "category":
                    "Multi-Agent Error",

                "diagnosis":
                    str(error),

                "confidence":
                    0
            },

            "retrieval": {
                "article":
                    None,

                "similarity":
                    0
            },

            "resolution": {
                "response":
                    "Multi-agent workflow "
                    "could not be completed.",

                "steps":
                    []
            },

            "validation": {
                "confidence":
                    0,

                "status":
                    "ESCALATE"
            },

            "escalation":
                True,

            "jira": {
                "success":
                    False
            },

            "email": {
                "success":
                    False
            }
        }


    processing_time = (
        time.time() -
        start_time
    )


    if not isinstance(
        result,
        dict
    ):
        result = {}


    result["processing_time"] = round(
        processing_time,
        3
    )

    result["severity"] = severity

    result["priority"] = priority

    result["impact"] = impact


    return jsonify(
        result
    )


# =========================================================
# RESOLUTION FEEDBACK
# =========================================================

@app.route(
    "/feedback",
    methods=["POST"]
)
@jwt_required
def feedback():

    data = request.get_json()

    if not data:

        return jsonify({
            "error":
                "Invalid feedback data."
        }), 400


    resolved = data.get(
        "resolved",
        False
    )


    resolved = bool(
        resolved
    )


    metrics_tracker.record_feedback(
        resolved=resolved
    )


    metrics = (
        metrics_tracker.get_metrics(
            retrieval_accuracy=
                RETRIEVAL_ACCURACY
        )
    )


    return jsonify({

        "success":
            True,

        "metrics":
            metrics
    })


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )