import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jira_service import JiraService


# ============================================================
# LOAD KNOWLEDGE BASE
# ============================================================

# Use the SAME knowledge base as Milestone 2
KNOWLEDGE_BASE_PATH = "data/knowledge_base.json"

with open(
    KNOWLEDGE_BASE_PATH,
    "r",
    encoding="utf-8"
) as file:
    KNOWLEDGE_BASE = json.load(file)


# ============================================================
# 1. DIAGNOSIS AGENT
# ============================================================

class DiagnosisAgent:

    def __init__(self):

        self.rules = {

            "Hardware": [
                "laptop",
                "computer",
                "keyboard",
                "mouse",
                "touchpad",
                "trackpad",
                "screen",
                "monitor",
                "display",
                "printer",
                "printing",
                "print"
            ],

            "VPN / Network": [
                "vpn",
                "network",
                "internet",
                "connection",
                "connect",
                "wifi",
                "wi-fi",
                "router",
                "ethernet"
            ],

            "Password / Access": [
                "password",
                "login",
                "sign in",
                "signin",
                "locked",
                "access",
                "permission"
            ],

            "Email": [
                "email",
                "mail",
                "outlook",
                "gmail",
                "mailbox"
            ],

            "Performance": [
                "slow",
                "lag",
                "freeze",
                "freezing",
                "performance",
                "hang",
                "hanging"
            ],

            "Software": [
                "software",
                "application",
                "app",
                "program",
                "crash",
                "error",
                "not responding"
            ]
        }


    def analyze(self, ticket):

        ticket_lower = ticket.lower()

        for category, keywords in self.rules.items():

            for keyword in keywords:

                if keyword in ticket_lower:

                    return {
                        "diagnosis": category,
                        "category": category,
                        "confidence": 0.80,
                        "message": (
                            f"Ticket classified as {category} "
                            "based on detected keywords."
                        )
                    }


        return {
            "diagnosis": "General IT Issue",
            "category": "General IT Issue",
            "confidence": 0.80,
            "message": (
                "No specific issue category was detected. "
                "Further investigation may be required."
            )
        }


# ============================================================
# 2. RETRIEVAL AGENT
# ============================================================

class RetrievalAgent:

    def __init__(self):

        self.documents = []

        for article in KNOWLEDGE_BASE:

            text = (
                article.get("category", "")
                + " "
                + article.get("subcategory", "")
                + " "
                + article.get("title", "")
                + " "
                + article.get("content", "")
            )

            self.documents.append(text)


        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2)
        )

        self.document_vectors = (
            self.vectorizer.fit_transform(
                self.documents
            )
        )


    def normalize_query(self, query):

        query = query.lower()

        replacements = {
            "log out": "logout",
            "logging out": "logout",
            "logs out": "logout",
            "logged out": "logout",
            "wi fi": "wifi",
            "wi-fi": "wifi"
        }

        for old, new in replacements.items():

            query = query.replace(
                old,
                new
            )

        return query


    def search(self, query):

        query = self.normalize_query(
            query
        )

        query_vector = (
            self.vectorizer.transform(
                [query]
            )
        )

        scores = cosine_similarity(
            query_vector,
            self.document_vectors
        )[0]


        # ----------------------------------------------------
        # KEYWORD-BASED RELEVANCE BOOST
        # ----------------------------------------------------

        query_words = set(
            re.findall(
                r"\b[a-zA-Z]{3,}\b",
                query
            )
        )

        boosted_scores = scores.copy()


        for index, article in enumerate(
            KNOWLEDGE_BASE
        ):

            title = article.get(
                "title",
                ""
            ).lower()

            subcategory = article.get(
                "subcategory",
                ""
            ).lower()

            category = article.get(
                "category",
                ""
            ).lower()

            important_text = (
                title
                + " "
                + subcategory
                + " "
                + category
            )

            important_words = set(
                re.findall(
                    r"\b[a-zA-Z]{3,}\b",
                    important_text
                )
            )


            matching_words = (
                query_words &
                important_words
            )


            if matching_words:

                bonus = (
                    len(matching_words)
                    /
                    max(
                        len(query_words),
                        1
                    )
                )

                boosted_scores[index] += (
                    0.30 * bonus
                )


            # Complete phrase match
            if query in important_text:

                boosted_scores[index] += 0.50


        # ----------------------------------------------------
        # FIND BEST ARTICLE
        # ----------------------------------------------------

        best_index = (
            boosted_scores.argmax()
        )

        best_score = float(
            min(
                boosted_scores[best_index],
                1.0
            )
        )


        # ----------------------------------------------------
        # MINIMUM RELEVANCE THRESHOLD
        # ----------------------------------------------------

        MIN_RETRIEVAL_SCORE = 0.25


        if best_score < MIN_RETRIEVAL_SCORE:

            return {
                "article": None,
                "similarity": 0.0,
                "message": (
                    "No relevant knowledge-base "
                    "article found."
                )
            }


        # ----------------------------------------------------
        # RELEVANT ARTICLE FOUND
        # ----------------------------------------------------

        article = KNOWLEDGE_BASE[
            best_index
        ]


        return {

            "article": article,

            "similarity": best_score,

            "message": (
                "Relevant knowledge-base "
                "article found."
            )
        }


# ============================================================
# 3. RESOLUTION AGENT
# ============================================================

class ResolutionAgent:

    def generate(
        self,
        diagnosis,
        article
    ):

        category = diagnosis["category"]


        # ----------------------------------------------------
        # NO RELEVANT ARTICLE
        # ----------------------------------------------------

        if article is None:

            return {

                "response": (
                    "No relevant knowledge-base article "
                    "was found for this ticket. Additional "
                    "investigation is required."
                ),

                "steps": []
            }


        # ----------------------------------------------------
        # EXTRACT TROUBLESHOOTING STEPS FROM ARTICLE
        # ----------------------------------------------------

        content = article.get(
            "content",
            ""
        )

        extracted_steps = []

        lines = content.split("\n")


        for line in lines:

            cleaned = line.strip()

            if not cleaned:
                continue


            if (
                cleaned.startswith("-")
                or
                cleaned.startswith("*")
                or
                re.match(
                    r"^\d+[\.\)]",
                    cleaned
                )
            ):

                cleaned = re.sub(
                    r"^[-*]\s*",
                    "",
                    cleaned
                )

                cleaned = re.sub(
                    r"^\d+[\.\)]\s*",
                    "",
                    cleaned
                )

                if cleaned:

                    extracted_steps.append(
                        cleaned
                    )


        # ----------------------------------------------------
        # USE ARTICLE STEPS IF AVAILABLE
        # ----------------------------------------------------

        if extracted_steps:

            steps = extracted_steps[:6]

        else:

            steps = [

                "Review the relevant knowledge-base article.",

                "Verify the affected device or application.",

                "Check the related configuration and connectivity.",

                "Restart the affected service or application if appropriate.",

                "Retry the operation.",

                "Contact IT support if the issue continues."
            ]


        response = (

            f"A relevant knowledge-base article "
            f"('{article.get('title', 'Knowledge Article')}') "
            "was found for this issue. "
            "Follow the recommended troubleshooting "
            "steps below."
        )


        return {

            "response": response,

            "steps": steps
        }


# ============================================================
# 4. VALIDATION AGENT
# ============================================================

class ValidationAgent:

    def validate(
        self,
        diagnosis,
        retrieval,
        resolution
    ):

        diagnosis_confidence = float(
            diagnosis.get(
                "confidence",
                0
            )
        )

        retrieval_similarity = float(
            retrieval.get(
                "similarity",
                0
            )
        )

        number_of_steps = len(
            resolution.get(
                "steps",
                []
            )
        )


        # ----------------------------------------------------
        # VALIDATION CONFIDENCE
        # ----------------------------------------------------

        confidence = (

            diagnosis_confidence * 0.40

            +

            retrieval_similarity * 0.40

            +

            min(
                number_of_steps / 6,
                1
            ) * 0.20
        )


        confidence_percentage = (
            confidence * 100
        )


        # ----------------------------------------------------
        # WORKFLOW DECISION
        # ----------------------------------------------------

        if confidence_percentage >= 70:

            status = "AUTO_RESOLVE"

            message = (
                "Confidence is high enough to "
                "automatically resolve the ticket."
            )

        else:

            status = "ESCALATE"

            message = (
                "Confidence is below the "
                "automatic-resolution threshold. "
                "The ticket should be escalated."
            )


        return {

            "confidence":
                confidence,

            "confidence_percentage":
                round(
                    confidence_percentage,
                    2
                ),

            "status":
                status,

            "message":
                message
        }


# ============================================================
# 5. ESCALATION AGENT
# ============================================================

class EscalationAgent:

    def evaluate(
        self,
        validation,
        priority="P4",
        resolution_failed=False,
        customer_requested_human=False,
        repeated_attempts=0
    ):

        # ----------------------------------------------------
        # VALIDATION INFORMATION
        # ----------------------------------------------------

        confidence = float(
            validation.get(
                "confidence",
                0
            )
        )

        validation_status = str(
            validation.get(
                "status",
                ""
            )
        ).upper()


        # ----------------------------------------------------
        # NORMALIZE PRIORITY
        # ----------------------------------------------------

        priority_value = str(
            priority or ""
        ).strip().upper()


        # ----------------------------------------------------
        # WEEK 7 ESCALATION CONDITIONS
        # ----------------------------------------------------

        # Assignment requirement:
        # priority == "Critical"
        #
        # SupportPilot normally uses P1/P2/P3/P4,
        # therefore P1 is also treated as critical.

        critical_priority = (
            priority_value == "CRITICAL"
            or
            priority_value == "P1"
        )


        # AI confidence below 70%
        low_confidence = (
            confidence < 0.70
        )


        # Validation agent itself requested escalation
        validation_failed = (
            validation_status
            ==
            "ESCALATE"
        )


        # Resolution failed
        failed_resolution = bool(
            resolution_failed
        )


        # Customer explicitly requested human support
        human_requested = bool(
            customer_requested_human
        )


        # Three or more repeated attempts
        try:

            attempts = int(
                repeated_attempts or 0
            )

        except (
            TypeError,
            ValueError
        ):

            attempts = 0


        too_many_attempts = (
            attempts >= 3
        )


        # ----------------------------------------------------
        # FINAL ESCALATION DECISION
        # ----------------------------------------------------

        should_escalate = (
            critical_priority
            or
            low_confidence
            or
            validation_failed
            or
            failed_resolution
            or
            human_requested
            or
            too_many_attempts
        )


        # ----------------------------------------------------
        # ESCALATION REASONS
        # ----------------------------------------------------

        reasons = []


        if critical_priority:

            reasons.append(
                "Critical priority ticket"
            )


        if low_confidence:

            reasons.append(
                "AI confidence below 70%"
            )


        if validation_failed:

            reasons.append(
                "Validation agent requested escalation"
            )


        if failed_resolution:

            reasons.append(
                "Resolution attempt failed"
            )


        if human_requested:

            reasons.append(
                "Customer requested human support"
            )


        if too_many_attempts:

            reasons.append(
                "Repeated resolution attempts reached 3 or more"
            )


        # ----------------------------------------------------
        # RETURN ESCALATED RESULT
        # ----------------------------------------------------

        if should_escalate:

            return {

                "escalate":
                    True,

                "message": (
                    "Ticket requires human support. "
                    "Escalation initiated."
                ),

                "reasons":
                    reasons,

                "conditions": {

                    "critical_priority":
                        critical_priority,

                    "low_confidence":
                        low_confidence,

                    "validation_failed":
                        validation_failed,

                    "resolution_failed":
                        failed_resolution,

                    "customer_requested_human":
                        human_requested,

                    "repeated_attempts":
                        too_many_attempts
                }
            }


        # ----------------------------------------------------
        # RETURN AUTO-RESOLUTION RESULT
        # ----------------------------------------------------

        return {

            "escalate":
                False,

            "message": (
                "Ticket can be automatically resolved."
            ),

            "reasons":
                [],

            "conditions": {

                "critical_priority":
                    False,

                "low_confidence":
                    False,

                "validation_failed":
                    False,

                "resolution_failed":
                    False,

                "customer_requested_human":
                    False,

                "repeated_attempts":
                    False
            }
        }


# ============================================================
# 6. SUPPORTPILOT ORCHESTRATOR
# ============================================================

class SupportPilot:

    def __init__(self):

        print(
            "\n==================================="
        )

        print(
            "SUPPORT PILOT - MULTI-AGENT SYSTEM"
        )

        print(
            "===================================\n"
        )


        # ----------------------------------------------------
        # INITIALIZE AGENTS
        # ----------------------------------------------------

        self.diagnosis_agent = (
            DiagnosisAgent()
        )

        self.retrieval_agent = (
            RetrievalAgent()
        )

        self.resolution_agent = (
            ResolutionAgent()
        )

        self.validation_agent = (
            ValidationAgent()
        )

        self.escalation_agent = (
            EscalationAgent()
        )


        # ----------------------------------------------------
        # JIRA SERVICE
        # ----------------------------------------------------

        self.jira_service = (
            JiraService()
        )


    def process_ticket(
        self,
        ticket,
        recipient_email=None,
        priority="P4",
        customer_requested_human=False,
        repeated_attempts=0
    ):

        # ====================================================
        # AGENT 1 — DIAGNOSIS
        # ====================================================

        diagnosis = (
            self.diagnosis_agent.analyze(
                ticket
            )
        )


        # ====================================================
        # AGENT 2 — RETRIEVAL
        # ====================================================

        retrieval = (
            self.retrieval_agent.search(
                ticket
            )
        )


        # ====================================================
        # AGENT 3 — RESOLUTION
        # ====================================================

        resolution = (
            self.resolution_agent.generate(
                diagnosis,
                retrieval.get(
                    "article"
                )
            )
        )


        # ====================================================
        # DETERMINE RESOLUTION FAILURE
        # ====================================================

        resolution_steps = (
            resolution.get(
                "steps",
                []
            )
            or
            []
        )


        resolution_failed = (
            len(resolution_steps) == 0
        )


        # ====================================================
        # AGENT 4 — VALIDATION
        # ====================================================

        validation = (
            self.validation_agent.validate(
                diagnosis,
                retrieval,
                resolution
            )
        )


        # ====================================================
        # AGENT 5 — ESCALATION
        # ====================================================

        escalation = (
            self.escalation_agent.evaluate(

                validation,

                priority=priority,

                resolution_failed=
                    resolution_failed,

                customer_requested_human=
                    customer_requested_human,

                repeated_attempts=
                    repeated_attempts
            )
        )


        # ====================================================
        # JIRA INTEGRATION
        # ====================================================

        jira_result = {

            "success":
                False,

            "message":
                "Jira escalation not required."
        }


        if escalation["escalate"]:

            jira_result = (
                self.jira_service.create_issue(

                    ticket,

                    diagnosis,

                    resolution,

                    priority=priority
                )
            )


        # ====================================================
        # FINAL RESULT
        # ====================================================

        return {

            "diagnosis":
                diagnosis,

            "retrieval":
                retrieval,

            "resolution":
                resolution,

            "validation":
                validation,

            "escalation":
                escalation,

            "jira":
                jira_result,

            "priority":
                priority,

            "customer_requested_human":
                customer_requested_human,

            "repeated_attempts":
                repeated_attempts,

            "resolution_failed":
                resolution_failed
        }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    system = SupportPilot()


    test_tickets = [

        "My laptop touchpad is not responding.",

        "My VPN is not connecting to the company network.",

        "My computer is very slow."
    ]


    print(
        "\n=========================================="
    )

    print(
        "       SUPPORTPILOT AGENT TEST"
    )

    print(
        "=========================================="
    )


    for test_ticket in test_tickets:

        print(
            "\n------------------------------------------"
        )

        print(
            "TEST TICKET:"
        )

        print(
            test_ticket
        )


        result = system.process_ticket(

            test_ticket,

            priority="P4"
        )


        print(
            "\nDiagnosis:"
        )

        print(
            result["diagnosis"]
        )


        print(
            "\nRetrieval:"
        )

        print(
            result["retrieval"]
        )


        print(
            "\nResolution:"
        )

        print(
            result["resolution"]
        )


        print(
            "\nValidation:"
        )

        print(
            result["validation"]
        )


        print(
            "\nEscalation:"
        )

        print(
            result["escalation"]
        )


        print(
            "\nJira:"
        )

        print(
            result["jira"]
        )