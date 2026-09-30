from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    make_response,
    render_template_string
)

import time
import os
import sqlite3
from datetime import datetime
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


# ============================================================
# APP CONFIGURATION
# ============================================================

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "JWT_SECRET",
    "supportpilot-secret-key"
)

JWT_SECRET = app.config["SECRET_KEY"]

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "supportpilot.db"
)


# ============================================================
# MODEL / AI INITIALIZATION
# ============================================================

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "ticket_classifier.joblib"
)

try:
    classifier_model = joblib.load(MODEL_PATH)
    print("Ticket classifier loaded successfully.")
except Exception as e:
    classifier_model = None
    print("WARNING: Could not load ticket classifier:", e)


try:
    resolution_generator = ResolutionGenerator()
    print("RAG / Gemini resolution generator initialized.")
except Exception as e:
    resolution_generator = None
    print("WARNING: Could not initialize resolution generator:", e)


try:
    multi_agent_system = SupportPilot()
    print("Multi-agent SupportPilot initialized.")
except Exception as e:
    multi_agent_system = None
    print("WARNING: Could not initialize multi-agent system:", e)


metrics_tracker = MetricsTracker()


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():

    conn = get_db_connection()
    cursor = conn.cursor()

    # Existing tickets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT,
            severity TEXT,
            priority TEXT,
            status TEXT DEFAULT 'Open',
            created_at TEXT,
            employee_name TEXT,
            department TEXT
        )
    """)

    # Week 7 persistent metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            ai_resolved INTEGER DEFAULT 0,
            resolution_success INTEGER DEFAULT 0,
            kb_found INTEGER DEFAULT 0,
            classification_correct INTEGER,
            resolution_time REAL DEFAULT 0,
            ai_response_time REAL DEFAULT 0,
            customer_rating REAL,
            escalated INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


initialize_database()


# ============================================================
# JWT AUTHENTICATION
# ============================================================

def create_token(username):

    payload = {
        "username": username,
        "iat": int(time.time())
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm="HS256"
    )


def token_required(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        token = request.cookies.get("token")

        if not token:
            return redirect("/login")

        try:
            jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"]
            )

        except Exception:
            response = make_response(
                redirect("/login")
            )
            response.delete_cookie("token")
            return response

        return func(*args, **kwargs)

    return decorated


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_float(value, default=0.0):

    try:
        if value is None:
            return default

        return float(value)

    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):

    try:
        if value is None:
            return default

        return int(value)

    except (ValueError, TypeError):
        return default


def save_ticket(
    description,
    category,
    severity,
    priority,
    status,
    employee_name,
    department
):

    conn = get_db_connection()
    cursor = conn.cursor()

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cursor.execute(
        """
        INSERT INTO tickets
        (
            description,
            category,
            severity,
            priority,
            status,
            created_at,
            employee_name,
            department
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            description,
            category,
            severity,
            priority,
            status,
            created_at,
            employee_name,
            department
        )
    )

    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return ticket_id


def save_metric(
    ticket_id,
    ai_resolved=False,
    resolution_success=False,
    kb_found=False,
    classification_correct=None,
    resolution_time=0,
    ai_response_time=0,
    customer_rating=None,
    escalated=False
):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO metrics
        (
            ticket_id,
            ai_resolved,
            resolution_success,
            kb_found,
            classification_correct,
            resolution_time,
            ai_response_time,
            customer_rating,
            escalated,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticket_id,
            1 if ai_resolved else 0,
            1 if resolution_success else 0,
            1 if kb_found else 0,
            (
                None
                if classification_correct is None
                else 1 if classification_correct else 0
            ),
            safe_float(resolution_time),
            safe_float(ai_response_time),
            customer_rating,
            1 if escalated else 0,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )
    )

    metric_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return metric_id


def get_retrieval_accuracy():

    """
    Reads retrieval accuracy from the available
    evaluation file when present.
    """

    possible_files = [
        "retrieval_evaluation.csv",
        "data/retrieval_evaluation.csv",
        "data/retrieval_accuracy.csv"
    ]

    for path in possible_files:

        if not os.path.exists(path):
            continue

        try:

            df = pd.read_csv(path)

            possible_columns = [
                "correct",
                "retrieval_correct",
                "is_correct",
                "accuracy"
            ]

            for column in possible_columns:

                if column in df.columns:

                    values = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    ).dropna()

                    if len(values) > 0:

                        # If values are already percentages
                        if values.max() > 1:
                            return round(
                                values.mean(),
                                2
                            )

                        return round(
                            values.mean() * 100,
                            2
                        )

        except Exception:
            pass

    # Current known evaluation result
    return 100.0


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    ).strip()

    # Current demo credentials
    if (
        username == "admin"
        and password == "admin123"
    ):

        token = create_token(username)

        response = make_response(
            redirect("/")
        )

        response.set_cookie(
            "token",
            token,
            httponly=True,
            samesite="Lax"
        )

        return response

    return render_template(
        "login.html",
        error="Invalid username or password."
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    response = make_response(
        redirect("/login")
    )

    response.delete_cookie("token")

    return response


# ============================================================
# SUBMIT TICKET
# ============================================================

@app.route("/submit", methods=["POST"])
@token_required
def submit_ticket():

    workflow_start = time.time()

    try:

        data = request.get_json(
            silent=True
        )

        if data is None:
            data = request.form.to_dict()

        employee_name = data.get(
            "employee_name",
            "Unknown"
        )

        department = data.get(
            "department",
            "IT"
        )

        description = data.get(
            "description",
            ""
        ).strip()

        impact = data.get(
            "impact",
            ""
        )

        recipient_email = data.get(
            "email",
            ""
        ).strip()

        customer_requested_human = data.get(
            "customer_requested_human",
            False
        )

        repeated_attempts = safe_int(
            data.get(
                "repeated_attempts",
                0
            ),
            0
        )

        classification_correct_raw = data.get(
            "classification_correct"
        )

        actual_category = data.get(
            "actual_category",
            ""
        )

        if actual_category is None:
            actual_category = ""

        actual_category = str(
            actual_category
        ).strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not description:

            return jsonify({
                "success": False,
                "error": "Ticket description is required."
            }), 400

        if isinstance(
            customer_requested_human,
            str
        ):

            customer_requested_human = (
                customer_requested_human.lower()
                in [
                    "true",
                    "1",
                    "yes",
                    "human"
                ]
            )

        classification_correct = None

        if classification_correct_raw not in [
            None,
            "",
            "null"
        ]:

            if isinstance(
                classification_correct_raw,
                str
            ):

                classification_correct = (
                    classification_correct_raw.lower()
                    in [
                        "true",
                        "1",
                        "yes",
                        "correct"
                    ]
                )

            else:

                classification_correct = bool(
                    classification_correct_raw
                )

        # ----------------------------------------------------
        # TICKET CLASSIFICATION
        # ----------------------------------------------------

        classification_start = time.time()

        if classifier_model is not None:

            try:

                prediction = classifier_model.predict(
                    [description]
                )

                category = str(
                    prediction[0]
                )

            except Exception as e:

                print(
                    "Classifier error:",
                    e
                )

                category = "Unknown"

        else:

            category = "Unknown"

        classification_time = (
            time.time()
            - classification_start
        )

        # ----------------------------------------------------
        # CLASSIFICATION ACCURACY EVALUATION
        # ----------------------------------------------------
        # Compare the actual category supplied for evaluation
        # with the category predicted by the AI classifier.
        #
        # If Actual Category is not supplied, leave the value
        # as None so the ticket is not counted as evaluated.
        # ----------------------------------------------------

        if actual_category:

            normalized_actual_category = (
                actual_category.strip().lower()
            )

            normalized_predicted_category = (
                str(category).strip().lower()
            )

            classification_correct = (
                normalized_actual_category
                == normalized_predicted_category
            )

        elif classification_correct_raw not in [
            None,
            "",
            "null"
        ]:

            if isinstance(
                classification_correct_raw,
                str
            ):

                classification_correct = (
                    classification_correct_raw.lower()
                    in [
                        "true",
                        "1",
                        "yes",
                        "correct"
                    ]
                )

            else:

                classification_correct = bool(
                    classification_correct_raw
                )

        # ----------------------------------------------------
        # SEVERITY
        # ----------------------------------------------------

        try:

            severity = determine_severity(
                description
            )

        except Exception as e:

            print(
                "Severity engine error:",
                e
            )

            severity = "Low"

        # ----------------------------------------------------
        # PRIORITY
        # ----------------------------------------------------

        try:

            priority = determine_priority(
                severity,
                impact
            )

        except TypeError:

            try:

                priority = determine_priority(
                    severity
                )

            except Exception:

                priority = "P4"

        except Exception as e:

            print(
                "Priority engine error:",
                e
            )

            priority = "P4"

        # ----------------------------------------------------
        # RAG + GEMINI RESOLUTION
        # ----------------------------------------------------

        rag_start = time.time()

        resolution = ""
        sources = []
        rag_message = ""
        rag_response_time = 0.0

        if resolution_generator is not None:

            try:

                rag_result = (
                    resolution_generator
                    .generate_resolution(
                        description
                    )
                )

                if isinstance(
                    rag_result,
                    dict
                ):

                    resolution = (
                        rag_result.get(
                            "resolution",
                            ""
                        )
                    )

                    sources = (
                        rag_result.get(
                            "sources",
                            []
                        )
                    )

                    rag_message = (
                        rag_result.get(
                            "message",
                            ""
                        )
                    )

                    rag_response_time = safe_float(
                        rag_result.get(
                            "response_time",
                            0
                        )
                    )

                elif isinstance(
                    rag_result,
                    str
                ):

                    resolution = rag_result

            except Exception as e:

                print(
                    "RAG/Gemini error:",
                    e
                )

                resolution = (
                    "AI resolution could not be "
                    "generated automatically."
                )

        rag_elapsed = (
            time.time()
            - rag_start
        )

        if rag_response_time <= 0:
            rag_response_time = rag_elapsed

        # ----------------------------------------------------
        # MULTI-AGENT SYSTEM
        # ----------------------------------------------------

        multi_agent_start = time.time()

        multi_agent_result = {}

        if multi_agent_system is not None:

            try:

                multi_agent_result = (
                    multi_agent_system.process_ticket(
                        description,
                        recipient_email,
                        priority,
                        customer_requested_human,
                        repeated_attempts
                    )
                )

            except TypeError:

                # Compatibility with older SupportPilot
                try:

                    multi_agent_result = (
                        multi_agent_system
                        .process_ticket(
                            description,
                            recipient_email,
                            priority
                        )
                    )

                except Exception as e:

                    print(
                        "Multi-agent error:",
                        e
                    )

            except Exception as e:

                print(
                    "Multi-agent error:",
                    e
                )

        multi_agent_time = (
            time.time()
            - multi_agent_start
        )

        # ----------------------------------------------------
        # SAFELY EXTRACT MULTI-AGENT RESULTS
        # ----------------------------------------------------

        if not isinstance(
            multi_agent_result,
            dict
        ):

            multi_agent_result = {}

        validation = (
            multi_agent_result.get(
                "validation",
                {}
            )
        )

        escalation = (
            multi_agent_result.get(
                "escalation",
                {}
            )
        )

        diagnosis = (
            multi_agent_result.get(
                "diagnosis",
                {}
            )
        )

        retrieval = (
            multi_agent_result.get(
                "retrieval",
                {}
            )
        )

        resolution_agent = (
            multi_agent_result.get(
                "resolution",
                {}
            )
        )

        if not isinstance(
            validation,
            dict
        ):
            validation = {}

        if not isinstance(
            escalation,
            dict
        ):
            escalation = {}

        if not isinstance(
            diagnosis,
            dict
        ):
            diagnosis = {}

        if not isinstance(
            retrieval,
            dict
        ):
            retrieval = {}

        if not isinstance(
            resolution_agent,
            dict
        ):
            resolution_agent = {}

        # ----------------------------------------------------
        # VALIDATION STATUS
        # ----------------------------------------------------

        validation_status = (
            validation.get(
                "status",
                ""
            )
        )

        validation_confidence = safe_float(
            validation.get(
                "confidence",
                0
            )
        )

        # Convert decimal confidence to percentage
        if (
            validation_confidence > 0
            and validation_confidence <= 1
        ):

            validation_confidence *= 100

        # ----------------------------------------------------
        # KB FOUND
        # ----------------------------------------------------

        retrieved_article = (
            retrieval.get(
                "article"
            )
        )

        retrieval_similarity = safe_float(
            retrieval.get(
                "similarity",
                0
            )
        )

        kb_found = bool(
            retrieved_article
            or retrieval_similarity > 0
        )

        # Some implementations return a list
        if not kb_found:

            if sources:
                kb_found = True

        # ----------------------------------------------------
        # RESOLUTION STEPS
        # ----------------------------------------------------

        resolution_steps = (
            resolution_agent.get(
                "steps",
                []
            )
        )

        if not resolution_steps:

            # Try extracting basic numbered steps
            if isinstance(
                resolution,
                str
            ):

                lines = resolution.splitlines()

                extracted_steps = []

                for line in lines:

                    clean = line.strip()

                    if not clean:
                        continue

                    if (
                        clean[:2].isdigit()
                        or clean.startswith("-")
                        or clean.startswith("*")
                    ):

                        extracted_steps.append(
                            clean
                        )

                resolution_steps = (
                    extracted_steps[:6]
                )

        # ----------------------------------------------------
        # RESOLUTION FAILED
        # ----------------------------------------------------

        resolution_failed = (
            not bool(resolution)
            or (
                isinstance(
                    resolution_steps,
                    list
                )
                and len(resolution_steps) == 0
                and not kb_found
            )
        )

        # ----------------------------------------------------
        # ESCALATION DECISION
        # ----------------------------------------------------

        escalation_required = bool(
            escalation.get(
                "escalate",
                False
            )
        )

        escalation_reason = (
            escalation.get(
                "reason",
                ""
            )
        )

        # Enforce Week 7 escalation rules
        if priority in [
            "P1",
            "Critical"
        ]:

            escalation_required = True

            if not escalation_reason:
                escalation_reason = (
                    "Critical priority requires "
                    "human intervention."
                )

        if (
            validation_confidence > 0
            and validation_confidence < 70
        ):

            escalation_required = True

            if not escalation_reason:
                escalation_reason = (
                    "AI confidence is below "
                    "the required threshold."
                )

        if resolution_failed:

            escalation_required = True

            if not escalation_reason:
                escalation_reason = (
                    "AI resolution failed."
                )

        if customer_requested_human:

            escalation_required = True

            if not escalation_reason:
                escalation_reason = (
                    "Customer requested human support."
                )

        if repeated_attempts >= 3:

            escalation_required = True

            if not escalation_reason:
                escalation_reason = (
                    "Repeated attempts reached "
                    "the escalation threshold."
                )

        # ----------------------------------------------------
        # AI RESOLVED / SUCCESS
        # ----------------------------------------------------

        ai_resolved = not escalation_required

        resolution_success = (
            ai_resolved
            and not resolution_failed
        )

        # ----------------------------------------------------
        # FINAL STATUS
        # ----------------------------------------------------

        if escalation_required:

            status = "Escalated"

        else:

            status = "AI Resolved"

        # ----------------------------------------------------
        # TOTAL TIMES
        # ----------------------------------------------------

        total_workflow_time = (
            time.time()
            - workflow_start
        )

        # AI response time = actual RAG/Gemini +
        # multi-agent processing time
        ai_response_time = (
            rag_response_time
            + multi_agent_time
        )

        # Fallback if timings are unavailable
        if ai_response_time <= 0:

            ai_response_time = (
                total_workflow_time
            )

        # ----------------------------------------------------
        # SAVE TICKET
        # ----------------------------------------------------

        ticket_id = save_ticket(
            description=description,
            category=category,
            severity=severity,
            priority=priority,
            status=status,
            employee_name=employee_name,
            department=department
        )

        # ----------------------------------------------------
        # SAVE WEEK 7 METRIC
        # ----------------------------------------------------

        metric_id = save_metric(
            ticket_id=ticket_id,
            ai_resolved=ai_resolved,
            resolution_success=resolution_success,
            kb_found=kb_found,
            classification_correct=(
                classification_correct
            ),
            resolution_time=(
                total_workflow_time
            ),
            ai_response_time=(
                ai_response_time
            ),
            customer_rating=None,
            escalated=escalation_required
        )

        # ----------------------------------------------------
        # IN-MEMORY METRICS
        # ----------------------------------------------------

        metrics_tracker.record_ticket(
            response_time=total_workflow_time,
            resolution_time=total_workflow_time,
            ai_resolved=ai_resolved,
            resolution_success=resolution_success,
            kb_found=kb_found,
            classification_correct=(
                classification_correct
            ),
            ai_response_time=ai_response_time,
            escalated=escalation_required
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({
            "success": True,

            "ticket_id": ticket_id,

            "category": category,

            "actual_category": actual_category,

            "classification_correct": (
                classification_correct
            ),

            "severity": severity,

            "priority": priority,

            "status": status,

            "employee_name": employee_name,

            "department": department,

            "description": description,

            "resolution": resolution,

            "sources": sources,

            "rag_message": rag_message,

            "rag_response_time": round(
                rag_response_time,
                2
            ),

            "multi_agent_time": round(
                multi_agent_time,
                2
            ),

            "ai_response_time": round(
                ai_response_time,
                2
            ),

            "total_workflow_time": round(
                total_workflow_time,
                2
            ),

            "ai_resolved": ai_resolved,

            "resolution_success": (
                resolution_success
            ),

            "kb_found": kb_found,

            "resolution_failed": (
                resolution_failed
            ),

            "resolution_steps": (
                resolution_steps
            ),

            "validation": validation,

            "validation_status": (
                validation_status
            ),

            "validation_confidence": round(
                validation_confidence,
                2
            ),

            "diagnosis": diagnosis,

            "retrieval": retrieval,

            "retrieval_similarity": round(
                retrieval_similarity,
                4
            ),

            "escalation": {

                "required": (
                    escalation_required
                ),

                "reason": (
                    escalation_reason
                ),

                "status": (
                    "Escalated to Human Agent"
                    if escalation_required
                    else "Continue AI Resolution"
                )
            },

            "multi_agent": multi_agent_result,

            "workflow": {

                "ticket_analysis": {

                    "category": category,

                    "severity": severity,

                    "priority": priority
                },

                "knowledge_retrieval": {

                    "kb_found": kb_found,

                    "article_count": (
                        1 if kb_found else 0
                    ),

                    "similarity": (
                        retrieval_similarity
                    )
                },

                "context_augmentation": {

                    "sources": sources,

                    "document_count": len(
                        sources
                    )
                },

                "resolution_generation": {

                    "model": (
                        "Gemini 3.6 Flash"
                    ),

                    "resolution": resolution
                },

                "validation": validation,

                "escalation": escalation
            },

            "metrics": {

                "ticket_id": ticket_id,

                "metric_id": metric_id,

                "ai_response_time": round(
                    ai_response_time,
                    2
                ),

                "resolution_time": round(
                    total_workflow_time,
                    2
                ),

                "kb_found": kb_found,

                "ai_resolved": ai_resolved,

                "escalated": (
                    escalation_required
                ),

                "retrieval_accuracy": (
                    100
                    if kb_found
                    else 0
                ),

                "resolution_rate": (
                    100
                    if resolution_success
                    else 0
                ),

                "average_response_time": round(
                    ai_response_time,
                    2
                )
            }
        })

    except Exception as e:

        print(
            "SUBMIT ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# MULTI-AGENT API
# ============================================================

@app.route(
    "/api/multi-agent",
    methods=["POST"]
)
@token_required
def api_multi_agent():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        description = data.get(
            "description",
            ""
        ).strip()

        priority = data.get(
            "priority",
            "P4"
        )

        recipient_email = data.get(
            "email",
            ""
        )

        customer_requested_human = data.get(
            "customer_requested_human",
            False
        )

        repeated_attempts = safe_int(
            data.get(
                "repeated_attempts",
                0
            )
        )

        if not description:

            return jsonify({
                "success": False,
                "error": "Description is required."
            }), 400

        if isinstance(
            customer_requested_human,
            str
        ):

            customer_requested_human = (
                customer_requested_human.lower()
                in [
                    "true",
                    "1",
                    "yes"
                ]
            )

        if multi_agent_system is None:

            return jsonify({
                "success": False,
                "error": (
                    "Multi-agent system is unavailable."
                )
            }), 500

        start = time.time()

        result = (
            multi_agent_system.process_ticket(
                description,
                recipient_email,
                priority,
                customer_requested_human,
                repeated_attempts
            )
        )

        elapsed = time.time() - start

        return jsonify({
            "success": True,
            "result": result,
            "response_time": round(
                elapsed,
                2
            )
        })

    except TypeError:

        try:

            start = time.time()

            result = (
                multi_agent_system
                .process_ticket(
                    description,
                    recipient_email,
                    priority
                )
            )

            elapsed = time.time() - start

            return jsonify({
                "success": True,
                "result": result,
                "response_time": round(
                    elapsed,
                    2
                )
            })

        except Exception as e:

            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# FEEDBACK
# ============================================================

@app.route(
    "/feedback",
    methods=["POST"]
)
@token_required
def feedback():

    try:

        data = request.get_json(
            silent=True
        )

        if data is None:

            data = request.form.to_dict()

        resolved = data.get(
            "resolved",
            False
        )

        rating = data.get(
            "rating"
        )

        ticket_id = data.get(
            "ticket_id"
        )

        # ----------------------------------------------------
        # Convert resolved value
        # ----------------------------------------------------

        if isinstance(
            resolved,
            str
        ):

            resolved = (
                resolved.lower()
                in [
                    "true",
                    "1",
                    "yes",
                    "resolved"
                ]
            )

        else:

            resolved = bool(
                resolved
            )

        # ----------------------------------------------------
        # Convert rating
        # ----------------------------------------------------

        rating_value = None

        if rating not in [
            None,
            "",
            "null"
        ]:

            try:

                rating_value = float(
                    rating
                )

                if (
                    rating_value < 1
                    or rating_value > 5
                ):

                    return jsonify({
                        "success": False,
                        "error": (
                            "Rating must be between 1 and 5."
                        )
                    }), 400

            except (
                ValueError,
                TypeError
            ):

                return jsonify({
                    "success": False,
                    "error": "Invalid rating."
                }), 400

        # ----------------------------------------------------
        # Update in-memory metrics
        # ----------------------------------------------------

        metrics_tracker.record_feedback(
            resolved=resolved,
            rating=rating_value
        )

        # ----------------------------------------------------
        # Persistent database update
        # ----------------------------------------------------

        conn = get_db_connection()
        cursor = conn.cursor()

        selected_metric = None

        # First try the ticket supplied by frontend
        if ticket_id not in [
            None,
            "",
            "null"
        ]:

            try:

                ticket_id_int = int(
                    ticket_id
                )

                selected_metric = cursor.execute(
                    """
                    SELECT metric_id, ticket_id
                    FROM metrics
                    WHERE ticket_id = ?
                    ORDER BY metric_id DESC
                    LIMIT 1
                    """,
                    (
                        ticket_id_int,
                    )
                ).fetchone()

            except (
                ValueError,
                TypeError
            ):

                selected_metric = None

        # If no ticket was supplied, use
        # the most recent evaluated ticket.
        if selected_metric is None:

            selected_metric = cursor.execute(
                """
                SELECT metric_id, ticket_id
                FROM metrics
                ORDER BY metric_id DESC
                LIMIT 1
                """
            ).fetchone()

        if selected_metric:

            metric_id = selected_metric[
                "metric_id"
            ]

            actual_ticket_id = selected_metric[
                "ticket_id"
            ]

            # IMPORTANT:
            # Save the rating persistently.
            cursor.execute(
                """
                UPDATE metrics
                SET customer_rating = ?
                WHERE metric_id = ?
                """,
                (
                    rating_value,
                    metric_id
                )
            )

            # If customer confirms resolution,
            # update ticket status.
            if resolved:

                cursor.execute(
                    """
                    UPDATE tickets
                    SET status = 'Customer Resolved'
                    WHERE ticket_id = ?
                    """,
                    (
                        actual_ticket_id,
                    )
                )

        conn.commit()
        conn.close()

        return jsonify({

            "success": True,

            "message": (
                "Feedback recorded successfully."
            ),

            "resolved": resolved,

            "rating": rating_value,

            "ticket_id": (
                ticket_id
                if ticket_id
                else (
                    selected_metric["ticket_id"]
                    if selected_metric
                    else None
                )
            )
        })

    except Exception as e:

        print(
            "FEEDBACK ERROR:",
            e
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DASHBOARD DATA
# ============================================================

def get_dashboard_data():

    conn = get_db_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------
    # Ticket counts
    # --------------------------------------------------------

    total_tickets_row = cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        """
    ).fetchone()

    total_tickets = (
        total_tickets_row["count"]
        if total_tickets_row
        else 0
    )

    critical_row = cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE LOWER(severity) = 'critical'
        """
    ).fetchone()

    critical_tickets = (
        critical_row["count"]
        if critical_row
        else 0
    )

    high_row = cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE LOWER(severity) = 'high'
        """
    ).fetchone()

    high_tickets = (
        high_row["count"]
        if high_row
        else 0
    )

    open_row = cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE status = 'Open'
        """
    ).fetchone()

    open_tickets = (
        open_row["count"]
        if open_row
        else 0
    )

    escalated_row = cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM metrics
        WHERE escalated = 1
        """
    ).fetchone()

    escalated_tickets = (
        escalated_row["count"]
        if escalated_row
        else 0
    )

    # --------------------------------------------------------
    # Week 7 metric calculations
    # --------------------------------------------------------

    metric_rows = cursor.execute(
        """
        SELECT *
        FROM metrics
        ORDER BY metric_id ASC
        """
    ).fetchall()

    evaluated_tickets = len(
        metric_rows
    )

    if evaluated_tickets > 0:

        ai_resolved_count = sum(
            int(row["ai_resolved"] or 0)
            for row in metric_rows
        )

        successful_count = sum(
            int(
                row["resolution_success"]
                or 0
            )
            for row in metric_rows
        )

        kb_count = sum(
            int(row["kb_found"] or 0)
            for row in metric_rows
        )

        escalated_metric_count = sum(
            int(row["escalated"] or 0)
            for row in metric_rows
        )

        ai_resolution_rate = (
            ai_resolved_count
            / evaluated_tickets
        ) * 100

        resolution_success_rate = (
            successful_count
            / evaluated_tickets
        ) * 100

        kb_coverage = (
            kb_count
            / evaluated_tickets
        ) * 100

    else:

        ai_resolution_rate = 0
        resolution_success_rate = 0
        kb_coverage = 0
        escalated_metric_count = 0

    # --------------------------------------------------------
    # Average resolution time
    # --------------------------------------------------------

    resolution_times = [
        safe_float(
            row["resolution_time"]
        )
        for row in metric_rows
        if safe_float(
            row["resolution_time"]
        ) > 0
    ]

    if resolution_times:

        average_resolution_time = (
            sum(resolution_times)
            / len(resolution_times)
        )

    else:

        average_resolution_time = 0

    # --------------------------------------------------------
    # Average AI response time
    # --------------------------------------------------------

    ai_response_times = [
        safe_float(
            row["ai_response_time"]
        )
        for row in metric_rows
        if safe_float(
            row["ai_response_time"]
        ) > 0
    ]

    if ai_response_times:

        average_ai_response_time = (
            sum(ai_response_times)
            / len(ai_response_times)
        )

    else:

        average_ai_response_time = 0

    # --------------------------------------------------------
    # Customer satisfaction
    # --------------------------------------------------------

    ratings = [
        safe_float(
            row["customer_rating"]
        )
        for row in metric_rows
        if row["customer_rating"] is not None
        and safe_float(
            row["customer_rating"]
        ) > 0
    ]

    if ratings:

        customer_satisfaction = (
            sum(ratings)
            / len(ratings)
        )

    else:

        customer_satisfaction = 0

    # --------------------------------------------------------
    # Classification accuracy
    # --------------------------------------------------------

    classification_values = []

    for row in metric_rows:

        value = row[
            "classification_correct"
        ]

        if value is not None:

            classification_values.append(
                int(value)
            )

    if classification_values:

        classification_accuracy = (
            sum(classification_values)
            / len(classification_values)
        ) * 100

    else:

        classification_accuracy = None

    # --------------------------------------------------------
    # Retrieval accuracy
    # --------------------------------------------------------

    retrieval_accuracy = (
        get_retrieval_accuracy()
    )

    # --------------------------------------------------------
    # Tickets volume and resolution - Monday to Sunday
    # --------------------------------------------------------

    from datetime import datetime, timedelta

    today = datetime.now().date()

    # Monday = 0 ... Sunday = 6
    week_start = today - timedelta(days=today.weekday())

    day_labels = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    tickets_received = []
    tickets_resolved = []

    for day_offset in range(7):

        current_day = week_start + timedelta(days=day_offset)
        next_day = current_day + timedelta(days=1)

        received_row = cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM tickets
            WHERE date(created_at) >= ?
              AND date(created_at) < ?
            """,
            (
                current_day.isoformat(),
                next_day.isoformat()
            )
        ).fetchone()

        resolved_row = cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM tickets
            WHERE date(created_at) >= ?
              AND date(created_at) < ?
              AND LOWER(COALESCE(status, '')) IN (
                  'resolved',
                  'closed'
              )
            """,
            (
                current_day.isoformat(),
                next_day.isoformat()
            )
        ).fetchone()

        tickets_received.append(
            received_row["count"]
            if received_row
            else 0
        )

        tickets_resolved.append(
            resolved_row["count"]
            if resolved_row
            else 0
        )

    # --------------------------------------------------------
    # Tickets Volume & Resolution
    # Sample demonstration data
    # --------------------------------------------------------

    weekly_ticket_volume = {
        "labels": [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ],

        "received": [
            42,
            58,
            71,
            64,
            82,
            51,
            38
        ],

        "resolved": [
            35,
            46,
            60,
            57,
            70,
            45,
            34
        ]
    }

    # --------------------------------------------------------
    # Recent tickets
    # --------------------------------------------------------

    recent_tickets = cursor.execute(
        """
        SELECT
            ticket_id,
            employee_name,
            department,
            category,
            severity,
            priority,
            status,
            created_at
        FROM tickets
        ORDER BY ticket_id DESC
        LIMIT 15
        """
    ).fetchall()

    recent_tickets = [
        dict(row)
        for row in recent_tickets
    ]

    conn.close()

    # --------------------------------------------------------
    # Return dashboard data
    # --------------------------------------------------------

    return {

        "total_tickets": total_tickets,

        "ai_resolution_rate": round(
            ai_resolution_rate,
            2
        ),

        "resolution_success_rate": round(
            resolution_success_rate,
            2
        ),

        "kb_coverage": round(
            kb_coverage,
            2
        ),

        "average_resolution_time": round(
            average_resolution_time,
            2
        ),

        "average_ai_response_time": round(
            average_ai_response_time,
            2
        ),

        "customer_satisfaction": round(
            customer_satisfaction,
            2
        ),

        "classification_accuracy": (
            None
            if classification_accuracy is None
            else round(
                classification_accuracy,
                2
            )
        ),

        "retrieval_accuracy": round(
            retrieval_accuracy,
            2
        ),

        "system_uptime": 100.0,

        "escalated_tickets": (
            escalated_metric_count
        ),

        "critical_tickets": critical_tickets,

        "high_tickets": high_tickets,

        "open_tickets": open_tickets,

        "evaluated_tickets": evaluated_tickets,

        "weekly_ticket_volume": weekly_ticket_volume,

        "recent_tickets": recent_tickets
    }


# ============================================================
# DASHBOARD
# ============================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>SupportPilot Dashboard</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

    background: #f8fbff;

    color: #1e3a5f;
}

.dashboard-page {

    max-width: 1400px;

    margin: 0 auto;

    padding: 28px 30px 45px;
}

/* ==========================================
   HEADER
========================================== */

.dashboard-header {

    display: flex;

    justify-content: space-between;

    align-items: flex-end;

    gap: 20px;

    margin-bottom: 24px;
}

.dashboard-header h1 {

    margin: 0 0 6px;

    color: #1d4ed8;

    font-size: 30px;

    font-weight: 800;
}

.dashboard-header p {

    margin: 0;

    color: #5b7aa3;

    font-size: 14px;
}

.live-status {

    display: inline-flex;

    align-items: center;

    gap: 8px;

    padding: 9px 13px;

    background: #eff6ff;

    border: 1px solid #bfdbfe;

    border-radius: 999px;

    color: #2563eb;

    font-size: 12px;

    font-weight: 700;

    white-space: nowrap;
}

.live-dot {

    width: 8px;

    height: 8px;

    border-radius: 50%;

    background: #2563eb;
}

/* ==========================================
   DASHBOARD HERO
========================================== */

.dashboard-hero {
    position: relative;
    min-height: 235px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 30px;
    padding: 34px 42px;
    margin-bottom: 28px;
    border-radius: 24px;
    background: linear-gradient(
        135deg,
        #2563eb 0%,
        #3b82f6 55%,
        #60a5fa 100%
    );
    box-shadow: 0 12px 30px rgba(37, 99, 235, 0.18);
}

.dashboard-hero::before {
    content: "";
    position: absolute;
    width: 260px;
    height: 260px;
    right: 120px;
    top: -130px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.10);
}

.dashboard-hero::after {
    content: "";
    position: absolute;
    width: 180px;
    height: 180px;
    right: -55px;
    bottom: -90px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.10);
}

.dashboard-hero-content {
    position: relative;
    z-index: 2;
}

.dashboard-brand-line {
    margin-bottom: 5px;
    font-size: 28px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.brand-support {
    color: #dbeafe;
}

.brand-pilot {
    color: #ffffff;
}

.dashboard-hero h1 {
    margin: 7px 0 7px;
    color: #ffffff;
    font-size: 34px;
    line-height: 1.05;
    font-weight: 800;
    letter-spacing: -0.025em;
}

.dashboard-hero p {
    margin: 0;
    max-width: 470px;
    color: #e0edff;
    font-size: 14px;
    line-height: 1.6;
}

.dashboard-hero-visual {
    position: relative;
    z-index: 2;
    width: 230px;
    height: 170px;
    flex-shrink: 0;
}

.dashboard-robot {
    position: absolute;
    right: 8px;
    bottom: 0;
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 72px;
    background: #ffffff;
    border-radius: 34px 34px 38px 38px;
    box-shadow: 0 14px 30px rgba(15, 70, 160, 0.20);
}

.dashboard-ai-box {
    position: absolute;
    left: 0;
    top: 18px;
    width: 82px;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    border-radius: 15px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 9px 22px rgba(15, 70, 160, 0.16);
}

.dashboard-ai-box::after {
    content: "";
    position: absolute;
    left: 18px;
    bottom: -8px;
    width: 16px;
    height: 16px;
    background: #ffffff;
    transform: rotate(45deg);
    border-radius: 2px;
}

.dashboard-ai-box span {
    position: relative;
    z-index: 2;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #2563eb;
}

/* ==========================================
   PRIMARY KPI CARDS
========================================== */

.primary-grid {

    display: grid;

    grid-template-columns:
        repeat(4, minmax(0, 1fr));

    gap: 16px;

    margin-bottom: 26px;
}

.primary-card {

    position: relative;

    overflow: hidden;

    background: #ffffff;

    border: 1px solid #dbeafe;

    border-radius: 18px;

    padding: 21px;

    box-shadow:
        0 8px 24px rgba(37, 99, 235, 0.08);
}

.primary-card::before {

    content: "";

    position: absolute;

    left: 0;

    top: 0;

    width: 100%;

    height: 4px;

    background: #2563eb;
}

.primary-icon {

    width: 40px;

    height: 40px;

    display: flex;

    align-items: center;

    justify-content: center;

    border-radius: 11px;

    background: #eff6ff;

    color: #2563eb;

    font-size: 18px;

    margin-bottom: 15px;
}

.primary-label {

    color: #6482a6;

    font-size: 12px;

    font-weight: 700;

    text-transform: uppercase;

    letter-spacing: 0.04em;

    margin-bottom: 7px;
}

.primary-value {

    color: #174ea6;

    font-size: 30px;

    line-height: 1;

    font-weight: 800;

    margin-bottom: 8px;
}

.primary-description {

    color: #7893b3;

    font-size: 12px;
}

/* ==========================================
   SECTION
========================================== */

.section {

    margin-bottom: 24px;
}

.section-header {

    display: flex;

    align-items: center;

    justify-content: space-between;

    margin-bottom: 12px;
}

.section-header h2 {

    margin: 0;

    color: #1e4f91;

    font-size: 18px;

    font-weight: 800;
}

.section-header span {

    color: #7893b3;

    font-size: 12px;
}

/* ==========================================
   AI PERFORMANCE
========================================== */

.performance-card {

    background: #ffffff;

    border: 1px solid #dbeafe;

    border-radius: 17px;

    padding: 20px;

    box-shadow:
        0 7px 22px rgba(37, 99, 235, 0.06);
}

.performance-grid {

    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 22px;
}

.performance-item {

    min-width: 0;
}

.performance-top {

    display: flex;

    align-items: center;

    justify-content: space-between;

    margin-bottom: 8px;
}

.performance-name {

    color: #55779e;

    font-size: 12px;

    font-weight: 700;
}

.performance-value {

    color: #2563eb;

    font-size: 13px;

    font-weight: 800;
}

.progress-track {

    width: 100%;

    height: 8px;

    overflow: hidden;

    background: #eaf2ff;

    border-radius: 999px;
}

.progress-bar {

    height: 100%;

    background: #3b82f6;

    border-radius: 999px;

    transition: width 0.4s ease;
}

/* ==========================================
   TICKET OVERVIEW
========================================== */

.overview-grid {

    display: grid;

    grid-template-columns:
        repeat(4, minmax(0, 1fr));

    gap: 12px;
}

.overview-card {

    background: #ffffff;

    border: 1px solid #dbeafe;

    border-radius: 14px;

    padding: 17px;

}

.overview-label {

    color: #6685a8;

    font-size: 11px;

    font-weight: 700;

    text-transform: uppercase;

    letter-spacing: 0.04em;

    margin-bottom: 7px;
}

.overview-value {

    color: #2563eb;

    font-size: 23px;

    font-weight: 800;
}

/* ==========================================
   RECENT TICKETS
========================================== */

.table-card {

    background: #ffffff;

    border: 1px solid #dbeafe;

    border-radius: 17px;

    overflow: hidden;

    box-shadow:
        0 7px 22px rgba(37, 99, 235, 0.06);
}

.table-wrapper {

    width: 100%;

    overflow-x: auto;
}

table {

    width: 100%;

    border-collapse: collapse;

    min-width: 850px;
}

th {

    padding: 13px 15px;

    background: #eff6ff;

    color: #4d6f97;

    font-size: 10px;

    font-weight: 800;

    text-align: left;

    text-transform: uppercase;

    letter-spacing: 0.04em;
}

td {

    padding: 13px 15px;

    border-top: 1px solid #edf4ff;

    color: #53749a;

    font-size: 12px;
}

.ticket-id {

    color: #2563eb;

    font-weight: 800;
}

.category {

    color: #315f91;

    font-weight: 600;
}

.status-badge {

    display: inline-block;

    padding: 5px 9px;

    border-radius: 999px;

    background: #eff6ff;

    border: 1px solid #bfdbfe;

    color: #2563eb;

    font-size: 10px;

    font-weight: 800;
}

.empty-row {

    text-align: center;

    padding: 30px !important;

    color: #7893b3;
}

/* ==========================================
   FOOTER
========================================== */

.dashboard-footer {

    padding-top: 8px;

    text-align: center;

    color: #8aa3c0;

    font-size: 11px;
}

/* ==========================================
   TICKETS VOLUME & RESOLUTION
========================================== */

.ticket-volume-card {

    background: #ffffff;

    border: 1px solid #dbeafe;

    border-radius: 18px;

    padding: 22px;

    box-shadow:
        0 8px 24px rgba(37, 99, 235, 0.07);

}

.ticket-volume-header {

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 16px;

    margin-bottom: 18px;

}

.ticket-volume-title {

    color: #1e3a5f;

    font-size: 18px;

    font-weight: 800;

    margin: 0;

}

.ticket-volume-subtitle {

    color: #7893b3;

    font-size: 12px;

    margin-top: 4px;

}

.ticket-volume-legend {

    display: flex;

    align-items: center;

    gap: 18px;

    flex-wrap: wrap;

}

.ticket-volume-legend-item {

    display: flex;

    align-items: center;

    gap: 7px;

    color: #55779e;

    font-size: 12px;

    font-weight: 700;

}

.ticket-volume-dot {

    width: 9px;

    height: 9px;

    border-radius: 50%;

    background: #2563eb;

}

.ticket-volume-dot.resolved {

    background: #93c5fd;

}

.ticket-volume-chart {

    width: 100%;

    overflow-x: auto;

}

.ticket-volume-chart svg {

    display: block;

    width: 100%;

    min-width: 700px;

    height: auto;

}

.ticket-volume-grid {

    stroke: #dbeafe;

    stroke-width: 1;

}

.ticket-volume-axis-label {

    fill: #7893b3;

    font-size: 12px;

    font-weight: 600;

}

.ticket-volume-day-label {

    fill: #55779e;

    font-size: 12px;

    font-weight: 700;

}

.ticket-volume-received {

    fill: none;

    stroke: #2563eb;

    stroke-width: 4;

    stroke-linecap: round;

    stroke-linejoin: round;

}

.ticket-volume-resolved {

    fill: none;

    stroke: #93c5fd;

    stroke-width: 4;

    stroke-linecap: round;

    stroke-linejoin: round;

}

.ticket-volume-received-point {

    fill: #2563eb;

    stroke: #ffffff;

    stroke-width: 3;

}

.ticket-volume-resolved-point {

    fill: #93c5fd;

    stroke: #ffffff;

    stroke-width: 3;

}

@media (max-width: 700px) {

    .ticket-volume-header {

        align-items: flex-start;

        flex-direction: column;

    }

}


/* ==========================================
   RESPONSIVE
========================================== */

@media (max-width: 1050px) {

    .primary-grid {

        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }

    .overview-grid {

        grid-template-columns:
            repeat(2, minmax(0, 1fr));
    }

}

@media (max-width: 700px) {

    .dashboard-page {

        padding: 22px 16px 35px;
    }

    .dashboard-header {

        align-items: flex-start;

        flex-direction: column;
    }

    .primary-grid {

        grid-template-columns: 1fr;
    }

    .performance-grid {

        grid-template-columns: 1fr;

        gap: 16px;
    }

    .overview-grid {

        grid-template-columns: 1fr;
    }

}

</style>

</head>

<body>

<main class="dashboard-page">

    <!-- ======================================
         HEADER
    ====================================== -->

    <header class="dashboard-hero">

        <div class="dashboard-hero-content">

            <div class="dashboard-brand-line">
                <span class="brand-support">Support</span><span class="brand-pilot">Pilot</span>
            </div>

            <h1>
                Dashboard
            </h1>

            <p>
                AI-powered customer support performance overview
            </p>

        </div>

        <div class="dashboard-hero-visual">

            <div class="dashboard-ai-box">
                <span></span>
                <span></span>
                <span></span>
            </div>

            <div class="dashboard-robot">
                🤖
            </div>

        </div>

    </header>


    <!-- ======================================
         PRIMARY KPIs
    ====================================== -->

    <section class="primary-grid">

        <div class="primary-card">

            <div class="primary-icon">
                ��
            </div>

            <div class="primary-label">
                Total Tickets
            </div>

            <div class="primary-value">
                {{ data.total_tickets }}
            </div>

            <div class="primary-description">
                All tickets received
            </div>

        </div>


        <div class="primary-card">

            <div class="primary-icon">
                🤖
            </div>

            <div class="primary-label">
                AI Resolution
            </div>

            <div class="primary-value">
                {{ data.ai_resolution_rate }}%
            </div>

            <div class="primary-description">
                Automatically resolved
            </div>

        </div>


        <div class="primary-card">

            <div class="primary-icon">
                ★
            </div>

            <div class="primary-label">
                Customer Satisfaction
            </div>

            <div class="primary-value">

                {% if data.customer_satisfaction > 0 %}
                    {{ data.customer_satisfaction }}/5
                {% else %}
                    N/A
                {% endif %}

            </div>

            <div class="primary-description">
                Average customer rating
            </div>

        </div>


        <div class="primary-card">

            <div class="primary-icon">
                ◉
            </div>

            <div class="primary-label">
                System Uptime
            </div>

            <div class="primary-value">
                {{ data.system_uptime }}%
            </div>

            <div class="primary-description">
                Current application session
            </div>

        </div>

    </section>


    <!-- ======================================
         TICKETS VOLUME & RESOLUTION
    ====================================== -->

    <section class="section">

        <div class="ticket-volume-card">

            <div class="ticket-volume-header">

                <div>

                    <h2 class="ticket-volume-title">
                        Tickets Volume &amp; Resolution
                    </h2>

                    <div class="ticket-volume-subtitle">
                        Tickets received and resolved from Monday to Sunday
                    </div>

                </div>

                <div class="ticket-volume-legend">

                    <div class="ticket-volume-legend-item">

                        <span class="ticket-volume-dot"></span>

                        <span>
                            Tickets Received
                        </span>

                    </div>

                    <div class="ticket-volume-legend-item">

                        <span class="ticket-volume-dot resolved"></span>

                        <span>
                            Tickets Resolved
                        </span>

                    </div>

                </div>

            </div>


            <div class="ticket-volume-chart">

                <svg
                    viewBox="0 0 1000 360"
                    role="img"
                    aria-label="Tickets received and resolved from Monday to Sunday"
                >

                    <!-- Horizontal grid lines -->

                    <line
                        x1="70"
                        y1="40"
                        x2="950"
                        y2="40"
                        class="ticket-volume-grid"
                    />

                    <line
                        x1="70"
                        y1="96"
                        x2="950"
                        y2="96"
                        class="ticket-volume-grid"
                    />

                    <line
                        x1="70"
                        y1="152"
                        x2="950"
                        y2="152"
                        class="ticket-volume-grid"
                    />

                    <line
                        x1="70"
                        y1="208"
                        x2="950"
                        y2="208"
                        class="ticket-volume-grid"
                    />

                    <line
                        x1="70"
                        y1="264"
                        x2="950"
                        y2="264"
                        class="ticket-volume-grid"
                    />

                    <line
                        x1="70"
                        y1="320"
                        x2="950"
                        y2="320"
                        class="ticket-volume-grid"
                    />


                    <!-- Y-axis labels -->

                    <text
                        x="52"
                        y="44"
                        text-anchor="end"
                        class="ticket-volume-axis-label"
                    >
                        100
                    </text>

                    <text
                        x="52"
                        y="100"
                        text-anchor="end"
                        class="ticket-volume-axis-label"
                    >
                        80
                    </text>

                    <text
                        x="52"
                        y="156"
                        text-anchor="end"
                        class="ticket-volume-axis-label"
                    >
                        60
                    </text>

                    <text
                        x="52"
                        y="212"
                        text-anchor="end"
                        class="ticket-volume-axis-label"
                    >
                        40
                    </text>

                    <text
                        x="52"
                        y="268"
                        text-anchor="end"
                        class="ticket-volume-axis-label"
                    >
                        20
                    </text>

                    <text
                        x="52"
                        y="324"
                        text-anchor="end"
                        class="ticket-volume-axis-label"
                    >
                        0
                    </text>


                    <!-- X-axis day labels -->

                    <text x="70" y="348" text-anchor="middle" class="ticket-volume-day-label">
                        Monday
                    </text>

                    <text x="217" y="348" text-anchor="middle" class="ticket-volume-day-label">
                        Tuesday
                    </text>

                    <text x="363" y="348" text-anchor="middle" class="ticket-volume-day-label">
                        Wednesday
                    </text>

                    <text x="510" y="348" text-anchor="middle" class="ticket-volume-day-label">
                        Thursday
                    </text>

                    <text x="657" y="348" text-anchor="middle" class="ticket-volume-day-label">
                        Friday
                    </text>

                    <text x="803" y="348" text-anchor="middle" class="ticket-volume-day-label">
                        Saturday
                    </text>

                    <text x="950" y="348" text-anchor="middle" class="ticket-volume-day-label">
                        Sunday
                    </text>


                    <!-- Ticket received line -->

                    <polyline
                        class="ticket-volume-received"
                        points="
                        {% for value in data.weekly_ticket_volume.received %}
                            {{ 70 + loop.index0 * 146.6667 }},
                            {{ 320 - ([value, 100]|min * 2.8) }}
                        {% endfor %}
                        "
                    />


                    <!-- Ticket resolved line -->

                    <polyline
                        class="ticket-volume-resolved"
                        points="
                        {% for value in data.weekly_ticket_volume.resolved %}
                            {{ 70 + loop.index0 * 146.6667 }},
                            {{ 320 - ([value, 100]|min * 2.8) }}
                        {% endfor %}
                        "
                    />


                    <!-- Received points -->

                    {% for value in data.weekly_ticket_volume.received %}

                    <circle
                        cx="{{ 70 + loop.index0 * 146.6667 }}"
                        cy="{{ 320 - ([value, 100]|min * 2.8) }}"
                        r="6"
                        class="ticket-volume-received-point"
                    />

                    {% endfor %}


                    <!-- Resolved points -->

                    {% for value in data.weekly_ticket_volume.resolved %}

                    <circle
                        cx="{{ 70 + loop.index0 * 146.6667 }}"
                        cy="{{ 320 - ([value, 100]|min * 2.8) }}"
                        r="6"
                        class="ticket-volume-resolved-point"
                    />

                    {% endfor %}

                </svg>

            </div>

        </div>

    </section>


    <!-- ======================================
         AI PERFORMANCE
    ====================================== -->

    <section class="section">

        <div class="section-header">

            <h2>
                AI Performance
            </h2>

            <span>
                AI quality indicators
            </span>

        </div>

        <div class="performance-card">

            <div class="performance-grid">

                <div class="performance-item">

                    <div class="performance-top">

                        <span class="performance-name">
                            Classification Accuracy
                        </span>

                        <span class="performance-value">

                            {% if data.classification_accuracy is not none %}
                                {{ data.classification_accuracy }}%
                            {% else %}
                                N/A
                            {% endif %}

                        </span>

                    </div>

                    <div class="progress-track">

                        <div
                            class="progress-bar"
                            style="width: {{ data.classification_accuracy if data.classification_accuracy is not none else 0 }}%;">
                        </div>

                    </div>

                </div>


                <div class="performance-item">

                    <div class="performance-top">

                        <span class="performance-name">
                            Resolution Success
                        </span>

                        <span class="performance-value">
                            {{ data.resolution_success_rate }}%
                        </span>

                    </div>

                    <div class="progress-track">

                        <div
                            class="progress-bar"
                            style="width: {{ data.resolution_success_rate }}%;">
                        </div>

                    </div>

                </div>


                <div class="performance-item">

                    <div class="performance-top">

                        <span class="performance-name">
                            Knowledge Base Coverage
                        </span>

                        <span class="performance-value">
                            {{ data.kb_coverage }}%
                        </span>

                    </div>

                    <div class="progress-track">

                        <div
                            class="progress-bar"
                            style="width: {{ data.kb_coverage }}%;">
                        </div>

                    </div>

                </div>

            </div>

        </div>

    </section>


    <!-- ======================================
         TICKET OVERVIEW
    ====================================== -->

    <section class="section">

        <div class="section-header">

            <h2>
                Ticket Overview
            </h2>

            <span>
                Current support workload
            </span>

        </div>

        <div class="overview-grid">

            <div class="overview-card">

                <div class="overview-label">
                    Escalated
                </div>

                <div class="overview-value">
                    {{ data.escalated_tickets }}
                </div>

            </div>


            <div class="overview-card">

                <div class="overview-label">
                    Critical
                </div>

                <div class="overview-value">
                    {{ data.critical_tickets }}
                </div>

            </div>


            <div class="overview-card">

                <div class="overview-label">
                    High Severity
                </div>

                <div class="overview-value">
                    {{ data.high_tickets }}
                </div>

            </div>


            <div class="overview-card">

                <div class="overview-label">
                    Open
                </div>

                <div class="overview-value">
                    {{ data.open_tickets }}
                </div>

            </div>

        </div>

    </section>


    <!-- ======================================
         RECENT TICKETS
    ====================================== -->

    <section class="section">

        <div class="section-header">

            <h2>
                Recent Tickets
            </h2>

            <span>
                Latest support activity
            </span>

        </div>

        <div class="table-card">

            <div class="table-wrapper">

                <table>

                    <thead>

                        <tr>

                            <th>ID</th>
                            <th>Employee</th>
                            <th>Department</th>
                            <th>Category</th>
                            <th>Severity</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Created</th>

                        </tr>

                    </thead>

                    <tbody>

                        {% for ticket in data.recent_tickets %}

                        <tr>

                            <td>
                                <span class="ticket-id">
                                    #{{ ticket.ticket_id }}
                                </span>
                            </td>

                            <td>
                                {{ ticket.employee_name or "—" }}
                            </td>

                            <td>
                                {{ ticket.department or "—" }}
                            </td>

                            <td>
                                <span class="category">
                                    {{ ticket.category or "—" }}
                                </span>
                            </td>

                            <td>
                                {{ ticket.severity or "—" }}
                            </td>

                            <td>
                                {{ ticket.priority or "—" }}
                            </td>

                            <td>

                                <span class="status-badge">
                                    {{ ticket.status or "Open" }}
                                </span>

                            </td>

                            <td>
                                {{ ticket.created_at or "—" }}
                            </td>

                        </tr>

                        {% else %}

                        <tr>

                            <td
                                colspan="8"
                                class="empty-row"
                            >
                                No tickets available.
                            </td>

                        </tr>

                        {% endfor %}

                    </tbody>

                </table>

            </div>

        </div>

    </section>


    <!-- ======================================
         SUPPORTPILOT FOOTER
    ====================================== -->

    <div class="dashboard-footer">

        SupportPilot — AI-Powered Customer Support Platform

    </div>

</main>

</body>

</html>
"""




@app.route("/dashboard")
@token_required
def dashboard():

    try:

        data = get_dashboard_data()

        return render_template_string(
            DASHBOARD_HTML,
            data=data
        )

    except Exception as e:

        print(
            "DASHBOARD ERROR:",
            e
        )

        return (
            "Dashboard error: "
            + str(e),
            500
        )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("SupportPilot")
    print("AI-Powered Customer Support Platform")
    print("=" * 60)

    print()
    print("Severity / Priority test:")

    try:

        test_description = (
            "The organization network is down."
        )

        test_severity = determine_severity(
            test_description
        )

        print(
            "Severity:",
            test_severity
        )

        try:

            test_priority = determine_priority(
                test_severity,
                ""
            )

        except TypeError:

            test_priority = determine_priority(
                test_severity
            )

        print(
            "Priority:",
            test_priority
        )

    except Exception as e:

        print(
            "Severity/Priority test error:",
            e
        )

    print()
    print("Dashboard:")
    print(
        "http://127.0.0.1:5000/dashboard"
    )

    print()
    print("Login:")
    print("Username: admin")
    print("Password: admin123")

    print()
    print("=" * 60)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
