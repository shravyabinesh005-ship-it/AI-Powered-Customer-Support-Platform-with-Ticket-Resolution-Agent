class MetricsTracker:

    def __init__(self):

        # --------------------------------------
        # LIVE TICKET METRICS
        # --------------------------------------

        self.total_tickets = 0

        self.total_response_time = 0.0

        # --------------------------------------
        # ACTUAL USER FEEDBACK
        # --------------------------------------

        self.feedback_count = 0

        self.resolved_tickets = 0


    # ==========================================
    # RECORD TICKET PROCESSING
    # ==========================================

    def record_ticket(
        self,
        response_time
    ):

        self.total_tickets += 1

        self.total_response_time += response_time


    # ==========================================
    # RECORD USER RESOLUTION FEEDBACK
    # ==========================================

    def record_feedback(
        self,
        resolved
    ):

        self.feedback_count += 1

        if resolved:

            self.resolved_tickets += 1


    # ==========================================
    # GET METRICS
    # ==========================================

    def get_metrics(
        self,
        retrieval_accuracy=0
    ):

        # --------------------------------------
        # RESOLUTION RATE
        # --------------------------------------

        if self.feedback_count > 0:

            resolution_rate = (
                self.resolved_tickets /
                self.feedback_count
            ) * 100

        else:

            resolution_rate = 0


        # --------------------------------------
        # AVERAGE RESPONSE TIME
        # --------------------------------------

        if self.total_tickets > 0:

            average_response_time = (
                self.total_response_time /
                self.total_tickets
            )

        else:

            average_response_time = 0


        return {

            "retrieval_accuracy":
                round(
                    retrieval_accuracy,
                    1
                ),

            "resolution_rate":
                round(
                    resolution_rate,
                    1
                ),

            "average_response_time":
                round(
                    average_response_time,
                    2
                ),

            "total_tickets":
                self.total_tickets,

            "feedback_count":
                self.feedback_count,

            "resolved_tickets":
                self.resolved_tickets

        }