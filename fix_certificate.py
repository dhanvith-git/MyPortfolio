
import sqlite3
import shutil

# Create database backup
shutil.copy2("portfolio.db", "portfolio_backup.db")

connection = sqlite3.connect("portfolio.db")
cursor = connection.cursor()

# Remove duplicate certificate
cursor.execute("DELETE FROM certifications WHERE id = 1")

# Fix the issue date
cursor.execute("""
UPDATE certifications
SET date = '2026-01-27'
WHERE id = 2
""")
# Update Cybersecurity certificate date
cursor.execute("""
UPDATE certifications
SET date = '2026-10-31'
WHERE id = 3
""")

connection.commit()
connection.close()

print("Duplicate removed and date updated successfully!")
