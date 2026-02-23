import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# =========================
# BASIC APP SETUP
# =========================
app = Flask(__name__)
app.secret_key = "supersecretkey"

# =========================
# DATABASE CONFIG
# =========================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# UPLOAD CONFIG
# =========================
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =========================
# DATABASE MODEL
# =========================
class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)

# =========================
# ADMIN LOGIN (Dummy)
# =========================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

# =========================
# ROUTES
# =========================

# Home Page
@app.route("/")
def index():
    return render_template("index.html")


# Notices Page (With Search)
@app.route("/notices")
def notices():
    search = request.args.get("search", "")
    
    if search:
        notices = Notice.query.filter(Notice.title.contains(search)).all()
    else:
        notices = Notice.query.all()

    return render_template("notices.html", notices=notices)


# Admin Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Credentials"

    return render_template("login.html")


# Admin Dashboard
@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("login"))

    notices = Notice.query.all()
    return render_template("admin_dashboard.html", notices=notices)


# Upload Notice
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        file = request.files["file"]

        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            new_notice = Notice(title=title, filename=filename)
            db.session.add(new_notice)
            db.session.commit()

            return redirect(url_for("admin_dashboard"))

    return render_template("upload_notice.html")


# Delete Notice
@app.route("/delete/<int:id>")
def delete_notice(id):
    if not session.get("admin"):
        return redirect(url_for("login"))

    notice = Notice.query.get(id)

    if notice:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], notice.filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(notice)
        db.session.commit()

    return redirect(url_for("admin_dashboard"))


# Logout
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(debug=True)
