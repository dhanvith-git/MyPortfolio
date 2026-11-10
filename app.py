import json
from email.mime import image
import os
import sqlite3
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)

from werkzeug.security import (
    check_password_hash, generate_password_hash
)

from werkzeug.utils import secure_filename


app = Flask(__name__)

# Local development settings.
# Change these before deploying publicly.
app.secret_key = os.environ.get(
    "SECRET_KEY", "local-development-secret-change-before-deploy"
)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

DATABASE = "portfolio.db"

UPLOAD_FOLDER = os.path.join("static", "uploads")

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
VIDEO_EXTENSIONS = {"mp4", "webm"}


# Admin credentials from environment variables
ADMIN_USERNAME = "dhanvith"
ADMIN_PASSWORD_HASH = generate_password_hash("Dhanvith@123")
print("Admin username:", ADMIN_USERNAME)
print("Password hash loaded:", bool(ADMIN_PASSWORD_HASH))


# Database connection
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# Create and update database tables
def create_tables():
    connection = get_db_connection()
    connection.execute("""

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            technologies TEXT,
            image TEXT,
            github_link TEXT,
            demo_link TEXT,
            video TEXT
        )
    """)
        # Paste certifications table here
    connection.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organization TEXT,
            issue_date TEXT,
            certificate_file TEXT
        )
    """)
    cert_columns = [
        row[1] for row in connection.execute(
            "PRAGMA table_info(certifications)"
        ).fetchall()
  ]

    if "issue_date" not in cert_columns:
        connection.execute(
            "ALTER TABLE certifications ADD COLUMN issue_date TEXT"
        )
    if "certificate_file" not in cert_columns:
        connection.execute(
            "ALTER TABLE certifications ADD COLUMN certificate_file TEXT"
        )

    # Add video column to an older database if necessary
    columns = [
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(projects)"
        ).fetchall()
    ]

    if "video" not in columns:
        connection.execute(
            "ALTER TABLE projects ADD COLUMN video TEXT"
        )
    if "screenshots" not in columns:
        connection.execute(
        "ALTER TABLE projects ADD COLUMN screenshots TEXT"
    )

    connection.commit()
    connection.close()
    


# Admin login protection
def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))

        return function(*args, **kwargs)

    return wrapper


# File validation
def allowed_file(filename, extensions):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in extensions
    )



# Homepage
@app.route("/")
def home():
    connection = get_db_connection()

    # Get all projects
    projects = connection.execute(
        "SELECT * FROM projects ORDER BY id DESC"
    ).fetchall()

    # Get all certifications
    certifications = connection.execute(
        "SELECT * FROM certifications ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        projects=projects,
        certifications=certifications
    )



# Admin login
@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        print("Username matches:", username == ADMIN_USERNAME)
        print("Password matches:", check_password_hash(ADMIN_PASSWORD_HASH, password))

        if username == ADMIN_USERNAME and ADMIN_PASSWORD_HASH and check_password_hash(ADMIN_PASSWORD_HASH, password):
         
         session["admin_logged_in"] = True            
         return redirect(url_for("admin_dashboard"))

        else:
            flash("Invalid username or password")

    return render_template("admin_login.html")

# Admin dashboard
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    connection = get_db_connection()

    projects = connection.execute(
        "SELECT * FROM projects ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template(
        "admin_dashboard.html",
        projects=projects
    )
@app.route("/admin/delete-project/<int:project_id>", methods=["POST"])
@admin_required
def delete_project(project_id):

    connection = get_db_connection()

    connection.execute(
        "DELETE FROM projects WHERE id = ?",
        (project_id,)
    )

    connection.commit()
    connection.close()

    flash("Project deleted successfully!")
    return redirect(url_for("admin_dashboard"))

# Add new project

@app.route("/admin/add-project", methods=["GET", "POST"])
@admin_required

def add_project():

    if request.method == "POST":

        # 1. Get project details
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        technologies = request.form.get("technologies", "").strip()
        github_link = request.form.get("github_link", "").strip()
        demo_link = request.form.get("demo_link", "").strip()

        # 2. Get uploaded files
        screenshots = request.files.getlist("screenshots")
        video = request.files.get("video")

        # 3. Check project title
        if not title:
            flash("Project title is required.")
            return render_template("add_project.html")

        # 4. Create upload folders
        os.makedirs("static/uploads/images", exist_ok=True)
        os.makedirs("static/uploads/videos", exist_ok=True)

        # 5. Initialize file paths
        screenshot_paths = []
        video_path = None

        # 6. Save multiple screenshots
        for screenshot in screenshots:

            if screenshot and screenshot.filename:

                if not allowed_file(screenshot.filename, IMAGE_EXTENSIONS):
                    flash("Please upload PNG, JPG, JPEG, or WEBP images.")
                    return render_template("add_project.html")

                filename = secure_filename(screenshot.filename)

                screenshot_path = "uploads/images/" + filename

                screenshot.save(
                    os.path.join("static", screenshot_path)
                )
                screenshot_paths.append(screenshot_path)

        # 7. Save project video
        if video and video.filename:
            if not allowed_file(video.filename, VIDEO_EXTENSIONS):
                flash("Please upload an MP4 or WEBM video.")
                return render_template("add_project.html")

            filename = secure_filename(video.filename)

            video_path = "uploads/videos/" + filename

            video.save(
                os.path.join("static", video_path)
            )

        # 8. Save project details in database
        connection = get_db_connection()

        connection.execute("""
            INSERT INTO projects
            (title, description, technologies,
             image, github_link, demo_link, video, screenshots)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            description,
            technologies,
            screenshot_paths[0] if screenshot_paths else None,
            github_link,
            demo_link,
            video_path,
            json.dumps(screenshot_paths)
        ))

        connection.commit()
        connection.close()

        # 9. Show success message
        flash("Project added successfully!")

        return redirect(url_for("admin_dashboard"))

    return render_template("add_project.html")

# Add Certification
@app.route("/admin/add_certification", methods=["GET", "POST"])
@admin_required
def add_certification():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        organization = request.form.get("organization", "").strip()
        issue_date = request.form.get("issue_date", "").strip()

        certificate = request.files.get("certificate_file")

        if not title:
            flash("Certificate title is required.")
            return render_template("add_certification.html")

        certificate_path = None

        if certificate and certificate.filename:

            allowed_extensions = {"pdf", "png", "jpg", "jpeg", "webp"}

            extension = certificate.filename.rsplit(".", 1)[-1].lower()

            if "." not in certificate.filename or extension not in allowed_extensions:
                flash("Upload PDF, PNG, JPG, JPEG or WEBP only.")
                return render_template("add_certification.html")

            filename = secure_filename(certificate.filename)

            upload_folder = os.path.join("static", "certifications")
            os.makedirs(upload_folder, exist_ok=True)

            name, ext = os.path.splitext(filename)
            counter = 1

            while os.path.exists(os.path.join(upload_folder, filename)):
                filename = f"{name}_{counter}{ext}"
                counter += 1

            certificate.save(os.path.join(upload_folder, filename))

            certificate_path = "certifications/" + filename

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO certifications
            (title, organization, issue_date, certificate_file)
            VALUES (?, ?, ?, ?)
            """,
            (title, organization, issue_date, certificate_path)
        )

        connection.commit()
        connection.close()

        flash("Certification added successfully!")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_certification.html")

# Admin logout
@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


create_tables()
if __name__ == "__main__":
    app.run(debug=True)
    