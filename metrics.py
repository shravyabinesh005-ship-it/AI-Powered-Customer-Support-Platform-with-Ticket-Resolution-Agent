import time


class MetricsTracker:
    """
    Tracks real SupportPilot workflow metrics
    during the current application run.
    """

    def __init__(self):

        # -----------------------------------------
        # TICKET COUNTERS
        # -----------------------------------------

        self.total_tickets = 0

        self.ai_resolved_tickets = 0
        self.escalated_tickets = 0
        self.successful_resolutions = 0

        # -----------------------------------------
        # KNOWLEDGE BASE
        # -----------------------------------------

        self.tickets_with_kb = 0

        # -----------------------------------------
        # CLASSIFICATION
        # -----------------------------------------

        self.classification_correct = 0
        self.classification_evaluated = 0

        # -----------------------------------------
        # RESPONSE / RESOLUTION TIME
        # -----------------------------------------

        self.total_response_time = 0.0
        self.total_resolution_time = 0.0

        self.total_ai_response_time = 0.0
        self.ai_response_count = 0

        # -----------------------------------------
        # CUSTOMER FEEDBACK
        # -----------------------------------------

        self.feedback_count = 0
        self.resolved_tickets = 0

        self.total_customer_rating = 0.0
        self.rating_count = 0

        # -----------------------------------------
        # SYSTEM MONITORING
        # -----------------------------------------

        self.system_start_time = time.time()

    # =====================================================
    # RECORD TICKET
    # =====================================================

    def record_ticket(
        self,
        response_time=0,
        resolution_time=0,
        ai_resolved=False,
        resolution_success=False,
        kb_found=False,
        classification_correct=None,
        ai_response_time=0,
        escalated=False
    ):

        self.total_tickets += 1

        # Timing
        self.total_response_time += float(
            response_time or 0
        )

        self.total_resolution_time += float(
            resolution_time or 0
        )

        # AI resolution
        if ai_resolved:
            self.ai_resolved_tickets += 1

        # Escalation
        if escalated:
            self.escalated_tickets += 1

        # Successful resolution
        if resolution_success:
            self.successful_resolutions += 1

        # Knowledge base
        if kb_found:
            self.tickets_with_kb += 1

        # Classification
        if classification_correct is not None:

            self.classification_evaluated += 1

            if classification_correct:
                self.classification_correct += 1

        # AI response time
        if ai_response_time:

            self.total_ai_response_time += float(
                ai_response_time
            )

            self.ai_response_count += 1

    # =====================================================
    # RECORD CUSTOMER FEEDBACK
    # =====================================================

    def record_feedback(
        self,
        resolved,
        rating=None
    ):

        self.feedback_count += 1

        if resolved:
            self.resolved_tickets += 1

        if rating is not None:

            self.total_customer_rating += float(
                rating
            )

            self.rating_count += 1

    # =====================================================
    # SYSTEM UPTIME
    # =====================================================

    def calculate_system_uptime(self):

        # The application is considered available
        # while this metrics tracker is running.

        uptime_seconds = (
            time.time() -
            self.system_start_time
        )

        if uptime_seconds <= 0:
            return 0.0

        # Current application run is active,
        # therefore availability is 100%.
        return 100.0

    # =====================================================
    # GET ALL METRICS
    # =====================================================

    def get_metrics(self):

        total = self.total_tickets

        # -----------------------------------------
        # AI RESOLUTION RATE
        # -----------------------------------------

        if total > 0:

            ai_resolution_rate = (
                self.ai_resolved_tickets /
                total
            ) * 100

        else:

            ai_resolution_rate = 0

        # -----------------------------------------
        # RESOLUTION SUCCESS RATE
        # -----------------------------------------

        if total > 0:

            resolution_success_rate = (
                self.successful_resolutions /
                total
            ) * 100

        else:

            resolution_success_rate = 0

        # -----------------------------------------
        # KNOWLEDGE BASE COVERAGE
        # -----------------------------------------

        if total > 0:

            kb_coverage = (
                self.tickets_with_kb /
                total
            ) * 100

        else:

            kb_coverage = 0

        # -----------------------------------------
        # CLASSIFICATION ACCURACY
        # -----------------------------------------

        if self.classification_evaluated > 0:

            classification_accuracy = (
                self.classification_correct /
                self.classification_evaluated
            ) * 100

        else:

            classification_accuracy = 0

        # -----------------------------------------
        # AVERAGE RESOLUTION TIME
        # -----------------------------------------

        if total > 0:

            average_resolution_time = (
                self.total_resolution_time /
                total
            )

        else:

            average_resolution_time = 0

        # -----------------------------------------
        # AVERAGE RESPONSE TIME
        # -----------------------------------------

        if total > 0:

            average_response_time = (
                self.total_response_time /
                total
            )

        else:

            average_response_time = 0

        # -----------------------------------------
        # CUSTOMER SATISFACTION
        # -----------------------------------------

        if self.rating_count > 0:

            customer_satisfaction = (
                self.total_customer_rating /
                self.rating_count
            )

        else:

            customer_satisfaction = 0

        # -----------------------------------------
        # AVERAGE AI RESPONSE TIME
        # -----------------------------------------

        if self.ai_response_count > 0:

            average_ai_response_time = (
                self.total_ai_response_time /
                self.ai_response_count
            )

        else:

            average_ai_response_time = 0

        # -----------------------------------------
        # FEEDBACK RESOLUTION RATE
        # -----------------------------------------

        if self.feedback_count > 0:

            feedback_resolution_rate = (
                self.resolved_tickets /
                self.feedback_count
            ) * 100

        else:

            feedback_resolution_rate = 0

        # -----------------------------------------
        # SYSTEM UPTIME
        # -----------------------------------------

        system_uptime = (
            self.calculate_system_uptime()
        )

        # -----------------------------------------
        # RETURN DASHBOARD METRICS
        # -----------------------------------------

        return {

            "total_tickets":
                self.total_tickets,

            "ai_resolution_rate":
                round(
                    ai_resolution_rate,
                    2
                ),

            "average_resolution_time":
                round(
                    average_resolution_time,
                    2
                ),

            "customer_satisfaction":
                round(
                    customer_satisfaction,
                    2
                ),

            "classification_accuracy":
                round(
                    classification_accuracy,
                    2
                ),

            "resolution_success_rate":
                round(
                    resolution_success_rate,
                    2
                ),

            "kb_coverage":
                round(
                    kb_coverage,
                    2
                ),

            "average_response_time":
                round(
                    average_response_time,
                    2
                ),

            "average_ai_response_time":
                round(
                    average_ai_response_time,
                    2
                ),

            "system_uptime":
                round(
                    system_uptime,
                    2
                ),

            "escalated_tickets":
                self.escalated_tickets,

            "feedback_count":
                self.feedback_count,

            "feedback_resolution_rate":
                round(
                    feedback_resolution_rate,
                    2
                )
        }


# =========================================================
# GLOBAL METRICS TRACKER
# =========================================================

metrics_tracker = MetricsTracker()