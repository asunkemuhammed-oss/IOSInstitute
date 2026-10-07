import os
import sqlite3
from email.message import EmailMessage
from smtplib import SMTP

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["DATABASE"] = os.environ.get("DATABASE_PATH", os.path.join(os.getcwd(), "ios.db"))
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True").lower() in {"1", "true", "yes"}

ROLE_LABELS = {
    "student": "Student – project assistance",
    "client": "Tech learner / applicant",
    "admin": "Admin (internal access)",
    "researcher": "Researcher",
}
VALID_ROLES = tuple(ROLE_LABELS.keys())
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@iosinstitute.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@12345")


def role_label(role):
    return ROLE_LABELS.get(role, role.replace("_", " ").title())


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            institution TEXT,
            department TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS research_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            research_type TEXT NOT NULL,
            topic TEXT NOT NULL,
            institution TEXT,
            department TEXT,
            deadline TEXT,
            assistance_needed TEXT,
            status TEXT NOT NULL DEFAULT 'submitted',
            assigned_researcher_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    db.execute(
        "INSERT OR IGNORE INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        ("Administrator", ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD, method="pbkdf2:sha256"), "admin"),
    )
    db.commit()


def send_confirmation_email(email, full_name, role):
    subject = "Account created successfully"
    body = (
        f"Hi {full_name},\n\n"
        "Your account has been created successfully.\n"
        f"Role: {role}\n\n"
        "You can now sign in and continue using the platform."
    )

    if os.environ.get("TESTING") == "1":
        print(f"EMAIL SENT TO {email}: {subject} | {body}")
        return True

    username = app.config["MAIL_USERNAME"]
    password = app.config["MAIL_PASSWORD"]
    if not username or not password:
        print(f"EMAIL SIMULATION: {email}: {subject} | {body}")
        return True

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = username
    message["To"] = email
    message.set_content(body)

    with SMTP(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]) as smtp:
        if app.config["MAIL_USE_TLS"]:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
    return True


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    admin_mode = request.args.get("admin") == "1"
    default_email = "admin@iosinstitute.com" if admin_mode else ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter your email and password.")
            return render_template("login.html", prefill_email=default_email, admin_mode=admin_mode)

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password")
            return render_template("login.html", prefill_email=email, admin_mode=admin_mode)

        session["user_id"] = user["id"]
        session["role"] = user["role"]
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        if user["role"] in {"student", "client", "researcher"}:
            return redirect(url_for("dashboard"))
        return redirect(url_for("register"))

    return render_template("login.html", prefill_email=default_email, admin_mode=admin_mode)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter your email address.")
            return render_template("forgot_password.html")

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            reset_message = f"A reset link has been sent to {email}."
        else:
            reset_message = "If an account exists for that email, a reset link has been sent."

        return render_template("forgot_password.html", reset_message=reset_message)

    return render_template("forgot_password.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    requests = []
    if user["role"] == "student":
        requests = get_db().execute(
            "SELECT * FROM research_requests WHERE user_id = ? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()

    return render_template("profile.html", user=user, requests=requests)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    if user["role"] == "admin":
        return redirect(url_for("admin_dashboard"))

    requests = []
    if user["role"] == "student":
        requests = get_db().execute(
            "SELECT * FROM research_requests WHERE user_id = ? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()

    if request.method == "POST":
        research_type = request.form.get("research_type", "").strip()
        topic = request.form.get("topic", "").strip()
        institution = request.form.get("institution", "").strip()
        department = request.form.get("department", "").strip()
        deadline = request.form.get("deadline", "").strip()

        if not research_type or not topic or not institution or not department:
            flash("Please complete the required research request fields.")
            return render_template("dashboard.html", user=user, requests=requests)

        db = get_db()
        db.execute(
            "INSERT INTO research_requests (user_id, research_type, topic, institution, department, deadline, status) VALUES (?, ?, ?, ?, ?, ?, 'submitted')",
            (user["id"], research_type, topic, institution, department, deadline or None),
        )
        db.commit()
        flash("Your research request has been submitted successfully.")
        return redirect(url_for("dashboard"))

    if user["role"] not in {"student", "client", "researcher"}:
        return redirect(url_for("login"))

    return render_template("dashboard.html", user=user, requests=requests)


@app.route("/admin-dashboard", methods=["GET", "POST"])
def admin_dashboard():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        request_id = request.form.get("request_id")
        status = request.form.get("status", "submitted")
        if request_id:
            get_db().execute(
                "UPDATE research_requests SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, int(request_id)),
            )
            get_db().commit()
            flash("Request status updated successfully.")

    rows = get_db().execute(
        """
        SELECT rr.id, rr.research_type, rr.topic, rr.institution, rr.department, rr.deadline, rr.status, u.name AS student_name
        FROM research_requests rr
        JOIN users u ON u.id = rr.user_id
        ORDER BY rr.id DESC
        """
    ).fetchall()

    return render_template("admin_dashboard.html", user=user, requests=rows)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        if not full_name or not email or not password:
            flash("Please complete all required fields.")
            return render_template("register.html")

        if role not in VALID_ROLES:
            flash("Please select a valid role.")
            return render_template("register.html")

        if role == "admin":
            flash("Admin access is restricted to internal staff. Please use the admin login credentials instead.")
            return render_template("register.html")

        db = get_db()
        existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("An account with this email already exists.")
            return render_template("register.html")

        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (full_name, email, generate_password_hash(password, method="pbkdf2:sha256"), role),
        )
        db.commit()

        send_confirmation_email(email, full_name, role_label(role))

        return render_template(
            "success.html",
            full_name=full_name,
            email=email,
            role=role_label(role),
            role_key=role,
        )

    return render_template("register.html")


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
