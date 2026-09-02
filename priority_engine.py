def determine_priority(severity, impact):
    """
    Determine ticket priority using severity and business impact.
    """

    severity = severity.lower()
    impact = impact.lower()

    # P1 - Critical + organization-wide impact
    if severity == "critical" and impact == "organization-wide":
        return "P1"

    # P2 - High severity or multiple-user impact
    elif severity == "high" or impact == "multiple users":
        return "P2"

    # P3 - Medium severity or limited-user impact
    elif severity == "medium" or impact == "limited users":
        return "P3"

    # P4 - Low severity / minor impact
    else:
        return "P4"


# ==========================================
# TEST THE PRIORITY ENGINE
# ==========================================

test_cases = [
    ("Critical", "Organization-wide"),
    ("High", "Multiple users"),
    ("Medium", "Limited users"),
    ("Low", "Single user")
]

print("\n===================================")
print("SUPPORT PILOT - PRIORITY ENGINE")
print("===================================")

for severity, impact in test_cases:

    priority = determine_priority(severity, impact)

    print("\nSeverity:", severity)
    print("Business Impact:", impact)
    print("Priority:", priority)