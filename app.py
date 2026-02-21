from flask import Flask, render_template, request, redirect, url_for, session, abort
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os, uuid

# =========================
# APP CONFIG
# =========================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

# =========================
# DATABASE
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# =========================
# AUTO INIT DB
# =========================
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id SERIAL PRIMARY KEY,
        title TEXT,
        filename TEXT,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("SELECT * FROM admins WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO admins (username, password) VALUES (%s, %s)",
            ("admin", generate_password_hash("1234"))
        )

    conn.commit()
    cur.close()
    conn.close()

# =========================
# HELPERS
# =========================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required():
    if "admin_id" not in session:
        abort(403)

# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices ORDER BY upload_date DESC")
    notices = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("index.html", notices=notices)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE username=%s", (username,))
        admin = cur.fetchone()
        cur.close()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin_id"] = admin["id"]
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin/dashboard")
def dashboard():
    login_required()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM notices")
    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return render_template("admin_dashboard.html", total=total)

@app.route("/admin/upload", methods=["GET", "POST"])
def upload():
    login_required()

    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("file")

        if not title or not file or not allowed_file(file.filename):
            return render_template("upload.html", error="Invalid file")

        filename = f"{uuid.uuid4().hex}.pdf"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notices (title, filename) VALUES (%s, %s)",
            (title, filename)
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("upload.html")

@app.route("/admin/delete/<int:id>")
def delete_notice(id):
    login_required()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT filename FROM notices WHERE id=%s", (id,))
    row = cur.fetchone()

    if row:
        path = os.path.join(app.config["UPLOAD_FOLDER"], row["filename"])
        if os.path.exists(path):
            os.remove(path)
        cur.execute("DELETE FROM notices WHERE id=%s", (id,))
        conn.commit()

    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/health")
def health():
    return "OK"

# =========================
# START
# =========================
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
