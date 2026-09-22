import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jira_service import JiraService


# ============================================================
# LOAD KNOWLEDGE BASE
# ============================================================

with open(
    "knowledge_base/knowledge.json",
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

            "VPN / Network": [
                "vpn",
                "network",
                "internet",
                "connection",
                "connect",
                "wifi",
                "wi-fi"
            ],

            "Password / Access": [
                "password",
                "login",
                "sign in",
                "signin",
                "locked",
                "access"
            ],

            "Email": [
                "email",
                "mail",
                "outlook",
                "gmail"
            ],

            "Printer": [
                "printer",
                "printing",
                "print"
            ],

            "Performance": [
                "slow",
                "lag",
                "freeze",
                "freezing",
                "performance"
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
                article.get("title", "")
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


    def search(self, query):

        query_vector = self.vectorizer.transform(
            [query]
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
                query.lower()
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

            title_words = set(
                re.findall(
                    r"\b[a-zA-Z]{3,}\b",
                    title
                )
            )


            if query_words.intersection(
                title_words
            ):

                boosted_scores[index] += 0.20


        # ----------------------------------------------------
        # FIND BEST ARTICLE
        # ----------------------------------------------------

        best_index = boosted_scores.argmax()

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
                    "No relevant knowledge-base article found."
                )
            }


        # ----------------------------------------------------
        # RELEVANT ARTICLE FOUND
        # ----------------------------------------------------

        return {
            "article": KNOWLEDGE_BASE[best_index],
            "similarity": best_score,
            "message": (
                "Relevant knowledge-base article found."
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
        # NO RELEVANT KNOWLEDGE-BASE ARTICLE
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
        # VPN / NETWORK
        # ----------------------------------------------------

        if category == "VPN / Network":

            steps = [
                "Check whether the device has an active internet connection.",
                "Verify that the VPN client is installed and running.",
                "Check the VPN server address and connection settings.",
                "Disconnect and reconnect the VPN connection.",
                "Restart the VPN client if the connection still fails.",
                "Contact the IT support team if the issue continues."
            ]

            response = (
                "The issue appears to be related to "
                "VPN or network connectivity. "
                "Follow the troubleshooting steps below."
            )


        # ----------------------------------------------------
        # PASSWORD / ACCESS
        # ----------------------------------------------------

        elif category == "Password / Access":

            steps = [
                "Verify that the username is correct.",
                "Check whether the account is locked.",
                "Use the organization's password reset process.",
                "Enter the new password carefully.",
                "Try signing in again.",
                "Contact IT support if access is still unavailable."
            ]

            response = (
                "The issue appears to be related to "
                "password or account access."
            )


        # ----------------------------------------------------
        # EMAIL
        # ----------------------------------------------------

        elif category == "Email":

            steps = [
                "Check whether the device has an active internet connection.",
                "Verify the email account configuration.",
                "Restart the email application.",
                "Check whether the mailbox is full.",
                "Try accessing the account through webmail.",
                "Contact IT support if the email service remains unavailable."
            ]

            response = (
                "The issue appears to be related to "
                "email service or configuration."
            )


        # ----------------------------------------------------
        # PRINTER
        # ----------------------------------------------------

        elif category == "Printer":

            steps = [
                "Check that the printer is powered on.",
                "Verify that the printer is connected to the network.",
                "Check the printer queue for stuck documents.",
                "Remove any blocked print jobs.",
                "Restart the printer.",
                "Contact IT support if printing still does not work."
            ]

            response = (
                "The issue appears to be related to "
                "printer connectivity or printing."
            )


        # ----------------------------------------------------
        # PERFORMANCE
        # ----------------------------------------------------

        elif category == "Performance":

            steps = [
                "Restart the computer.",
                "Close unnecessary applications.",
                "Check available storage space.",
                "Check whether background applications are consuming resources.",
                "Install available system updates.",
                "Contact IT support if the computer remains slow."
            ]

            response = (
                "The issue appears to be related to "
                "computer performance."
            )


        # ----------------------------------------------------
        # GENERAL IT ISSUE
        # ----------------------------------------------------

        else:

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
                    or cleaned.startswith("*")
                    or re.match(
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


            if extracted_steps:

                steps = extracted_steps[:6]

                response = (
                    "A relevant knowledge-base article "
                    "was found for this issue. "
                    "Follow the recommended troubleshooting "
                    "steps below."
                )

            else:

                steps = [
                    "Review the relevant knowledge-base article.",
                    "Verify the issue and affected system.",
                    "Check the available configuration and connectivity.",
                    "Restart the affected service or application if appropriate.",
                    "Retry the operation.",
                    "Contact IT support if the issue continues."
                ]

                response = (
                    "A relevant knowledge-base article was "
                    "found, but additional investigation may "
                    "be required."
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

        diagnosis_confidence = diagnosis.get(
            "confidence",
            0
        )

        retrieval_similarity = retrieval.get(
            "similarity",
            0
        )

        number_of_steps = len(
            resolution.get(
                "steps",
                []
            )
        )


        # ----------------------------------------------------
        # VALIDATION CONFIDENCE FORMULA
        # ----------------------------------------------------

        confidence = (
            diagnosis_confidence * 0.40
            + retrieval_similarity * 0.40
            + min(
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
                "Confidence is high enough to automatically "
                "resolve the ticket."
            )

        else:

            status = "ESCALATE"

            message = (
                "Confidence is below the automatic-resolution "
                "threshold. The ticket should be escalated."
            )


        return {
            "confidence": confidence,
            "confidence_percentage": round(
                confidence_percentage,
                2
            ),
            "status": status,
            "message": message
        }


# ============================================================
# 5. ESCALATION AGENT
# ============================================================

class EscalationAgent:

    def evaluate(
        self,
        validation
    ):

        should_escalate = (
            validation["status"]
            == "ESCALATE"
        )

        if should_escalate:

            return {
                "escalate": True,
                "message": (
                    "Ticket requires human support. "
                    "Escalation initiated."
                )
            }

        return {
            "escalate": False,
            "message": (
                "Ticket can be automatically resolved."
            )
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
        # INITIALIZE ALL AGENTS
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
        priority="P4"
    ):

        # ====================================================
        # AGENT 1
        # DIAGNOSIS
        # ====================================================

        diagnosis = (
            self.diagnosis_agent.analyze(
                ticket
            )
        )


        # ====================================================
        # AGENT 2
        # RETRIEVAL
        # ====================================================

        retrieval = (
            self.retrieval_agent.search(
                ticket
            )
        )


        # ====================================================
        # AGENT 3
        # RESOLUTION
        # ====================================================

        resolution = (
            self.resolution_agent.generate(
                diagnosis,
                retrieval.get("article")
            )
        )


        # ====================================================
        # AGENT 4
        # VALIDATION
        # ====================================================

        validation = (
            self.validation_agent.validate(
                diagnosis,
                retrieval,
                resolution
            )
        )


        # ====================================================
        # AGENT 5
        # ESCALATION
        # ====================================================

        escalation = (
            self.escalation_agent.evaluate(
                validation
            )
        )


        # ====================================================
        # JIRA INTEGRATION
        # ====================================================

        jira_result = {
            "success": False,
            "message": (
                "Jira escalation not required."
            )
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

            "diagnosis": diagnosis,

            "retrieval": retrieval,

            "resolution": resolution,

            "validation": validation,

            "escalation": escalation,

            "jira": jira_result,

            "priority": priority

        }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    system = SupportPilot()

    test_ticket = (
        "My VPN is not connecting to the "
        "company network."
    )

    result = system.process_ticket(
        test_ticket,
        priority="P2"
    )

    print(
        json.dumps(
            result,
            indent=4
        )
    )
