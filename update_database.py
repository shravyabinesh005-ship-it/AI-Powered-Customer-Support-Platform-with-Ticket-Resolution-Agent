import sqlite3

connection = sqlite3.connect("supportpilot.db")
cursor = connection.cursor()

cursor.execute("""
ALTER TABLE tickets ADD COLUMN employee_name TEXT
""")

cursor.execute("""
ALTER TABLE tickets ADD COLUMN department TEXT
""")

connection.commit()
connection.close()

print("Database updated successfully!")