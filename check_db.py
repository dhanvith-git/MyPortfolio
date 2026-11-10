
import sqlite3

connection = sqlite3.connect("portfolio.db")
cursor = connection.cursor()

cursor.execute("PRAGMA table_info(certifications)")
print("Columns:", cursor.fetchall())

cursor.execute("SELECT * FROM certifications")
print("Certificates:", cursor.fetchall())

connection.close()
