def determine_severity(description):
    """
    Determine ticket severity using simple keyword-based rules.
    """

    description = description.lower()

    # Critical severity
    critical_keywords = [
    "complete outage",
    "system down",
    "entire company",
    "data breach",
    "security breach",
    "data loss",
    "ransomware",
    "cannot access entire system"
]

    # High severity
    high_keywords = [
        "urgent",
        "critical",
        "multiple users",
        "business stopped",
        "cannot work",
        "major issue",
        "server down",
        "network down"
    ]

    # Medium severity
    medium_keywords = [
        "error",
        "problem",
        "issue",
        "not working",
        "slow",
        "failed",
        "failure"
    ]

    # Check Critical
    for keyword in critical_keywords:
        if keyword in description:
            return "Critical"

    # Check High
    for keyword in high_keywords:
        if keyword in description:
            return "High"

    # Check Medium
    for keyword in medium_keywords:
        if keyword in description:
            return "Medium"

    # If no important keyword is found
    return "Low"


# ==========================================
# TEST THE SEVERITY ENGINE
# ==========================================

test_tickets = [
    "The entire company system is down",
    "The network is down and multiple users cannot work",
    "My computer is not working properly",
    "Can someone tell me how to change my software settings?"
]

print("\n===================================")
print("SUPPORT PILOT - SEVERITY ENGINE")
print("===================================")

for ticket in test_tickets:

    severity = determine_severity(ticket)

    print("\nTicket:", ticket)
    print("Severity:", severity)