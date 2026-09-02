import sqlite3
from datetime import datetime


# ==========================================
# CREATE DATABASE
# ==========================================

connection = sqlite3.connect("supportpilot.db")

cursor = connection.cursor()


# ==========================================
# CREATE TICKETS TABLE
# ==========================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    category TEXT,
    severity TEXT,
    priority TEXT,
    status TEXT DEFAULT 'Open',
    created_at TEXT
)
""")


# Save changes
connection.commit()


# ==========================================
# ADD A TEST TICKET
# ==========================================

cursor.execute("""
INSERT INTO tickets
(description, category, severity, priority, status, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""", (
    "The company network is completely down",
    "Network",
    "Critical",
    "P1",
    "Open",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
))


# Save the test ticket
connection.commit()


# ==========================================
# DISPLAY SAVED TICKETS
# ==========================================

cursor.execute("SELECT * FROM tickets")

tickets = cursor.fetchall()

print("\n===================================")
print("SUPPORT PILOT - DATABASE")
print("===================================")

print("\nTickets stored in database:")

for ticket in tickets:
    print(ticket)


# ==========================================
# CLOSE DATABASE
# ==========================================

connection.close()

print("\nDatabase created successfully!")