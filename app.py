from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
import os

# =========================
# APP CONFIG
# =========================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"pdf"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DATABASE CONFIG
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# =========================
# HELPER
# =========================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        return f"Template error: {e}"

@app.route("/health")
def health():
    return "OK"

@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")

            if username == "admin" and password == "1234":
                session["admin"] = True
                return redirect(url_for("admin_dashboard"))
            else:
                return render_template("login.html", error="Invalid credentials")

        return render_template("login.html")
    except Exception as e:
        return f"Login error: {e}"

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))

    try:
        conn = get_db_connection()
        if not conn:
            return "DATABASE_URL not set"

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM notices")
        total = cur.fetchone()["total"]

        cur.close()
        conn.close()

        return render_template("admin_dashboard.html", total=total)

    except Exception as e:
        return f"Dashboard error: {e}"

@app.route("/admin/upload", methods=["GET", "POST"])
def upload_notice():
    if "admin" not in session:
        return redirect(url_for("login"))

    try:
        if request.method == "POST":
            title = request.form.get("title")
            file = request.files.get("file")

            if not title or not file or file.filename == "":
                return render_template("upload_notice.html", error="All fields required")

            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))

                conn = get_db_connection()
                if not conn:
                    return "DATABASE_URL not set"

                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO notices (title, filename) VALUES (%s, %s)",
                    (title, filename)
                )
                conn.commit()

                cur.close()
                conn.close()

                return redirect(url_for("notices"))

        return render_template("upload_notice.html")

    except Exception as e:
        return f"Upload error: {e}"

@app.route("/notices")
def notices():
    try:
        conn = get_db_connection()
        if not conn:
            return "DATABASE_URL not set"

        cur = conn.cursor()
        cur.execute("SELECT * FROM notices ORDER BY upload_date DESC")
        notices = cur.fetchall()

        cur.close()
        conn.close()

        return render_template("notices.html", notices=notices)

    except Exception as e:
        return f"Notices error: {e}"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
