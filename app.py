import os
import sqlite3
from email.message import EmailMessage
from smtplib import SMTP

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["DATABASE"] = os.environ.get("DATABASE_PATH", os.path.join(os.getcwd(), "ios.db"))
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD", "")
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True").lower() in {"1", "true", "yes"}

ROLE_LABELS = {
    "student": "Student / Client – project or research assistance",
    "client": "Student / Client – project or research assistance",
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


def ensure_user_profile_columns():
    db = get_db()
    columns = [row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()]
    for field_name, field_sql in {
        "phone_number": "ALTER TABLE users ADD COLUMN phone_number TEXT",
        "gender": "ALTER TABLE users ADD COLUMN gender TEXT",
        "course": "ALTER TABLE users ADD COLUMN course TEXT",
        "learning_mode": "ALTER TABLE users ADD COLUMN learning_mode TEXT",
        "payment_mode": "ALTER TABLE users ADD COLUMN payment_mode TEXT",
        "portfolio_status": "ALTER TABLE users ADD COLUMN portfolio_status TEXT DEFAULT 'not_started'",
        "researcher_assessment_title": "ALTER TABLE users ADD COLUMN researcher_assessment_title TEXT",
        "researcher_assessment_area": "ALTER TABLE users ADD COLUMN researcher_assessment_area TEXT",
        "researcher_assessment_text": "ALTER TABLE users ADD COLUMN researcher_assessment_text TEXT",
        "researcher_assessment_status": "ALTER TABLE users ADD COLUMN researcher_assessment_status TEXT DEFAULT 'not_started'",
        "researcher_assessment_word_count": "ALTER TABLE users ADD COLUMN researcher_assessment_word_count INTEGER DEFAULT 0",
        "cv_file": "ALTER TABLE users ADD COLUMN cv_file TEXT",
        "portfolio_file": "ALTER TABLE users ADD COLUMN portfolio_file TEXT",
        "profile_photo": "ALTER TABLE users ADD COLUMN profile_photo TEXT",
    }.items():
        if field_name not in columns:
            db.execute(field_sql)
    db.commit()


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
            phone_number TEXT,
            gender TEXT,
            course TEXT,
            learning_mode TEXT,
            payment_mode TEXT,
            portfolio_status TEXT DEFAULT 'not_started',
            researcher_assessment_title TEXT,
            researcher_assessment_area TEXT,
            researcher_assessment_text TEXT,
            researcher_assessment_status TEXT DEFAULT 'not_started',
            researcher_assessment_word_count INTEGER DEFAULT 0,
            cv_file TEXT,
            portfolio_file TEXT,
            profile_photo TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_user_profile_columns()
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


def row_value(row, key, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return default


def skill_programs():
    return [
        {
            "name": "Data Analysis",
            "description": "Learn how to turn raw data into business decisions using Excel, Power BI, SQL, and Python.",
            "tools": ["Excel", "Power BI", "SQL", "Python"],
            "instructor": "Dr. Amina Yusuf",
            "duration": "8 weeks",
            "curriculum": "Data cleaning, dashboarding, SQL queries, Python analysis, data storytelling",
            "fee": "₦85,000",
            "start_date": "18 Nov 2026",
            "certificate": "Industry-recognized certificate upon completion",
        },
        {
            "name": "Data Science",
            "description": "Understand data science fundamentals, model building, and evidence-based decision making for real-world problems.",
            "tools": ["Python", "Pandas", "NumPy", "Machine Learning"],
            "instructor": "Prof. Ijeoma Eze",
            "duration": "10 weeks",
            "curriculum": "Statistics, data wrangling, modeling, evaluation, insight presentation",
            "fee": "₦120,000",
            "start_date": "09 Nov 2026",
            "certificate": "Certificate and capstone project assessment",
        },
        {
            "name": "Web Development",
            "description": "Learn how to design and build responsive, user-friendly websites and digital products.",
            "tools": ["HTML", "CSS", "JavaScript", "React"],
            "instructor": "Mrs. Grace Okafor",
            "duration": "12 weeks",
            "curriculum": "Front-end design, interactivity, APIs, deployment, project building",
            "fee": "₦150,000",
            "start_date": "20 Nov 2026",
            "certificate": "Certificate + live project submission",
        },
        {
            "name": "Financial Analysis",
            "description": "Understand budgeting, reporting, forecasting, and performance analysis for smarter financial decisions.",
            "tools": ["Excel", "Forecasting", "Budgeting", "Reporting"],
            "instructor": "Mr. Adebayo Oladipo",
            "duration": "7 weeks",
            "curriculum": "Financial modeling, ratio analysis, budget planning, scenario analysis, interpretation",
            "fee": "₦70,000",
            "start_date": "26 Nov 2026",
            "certificate": "Certificate in financial analysis and decision support",
        },
        {
            "name": "Digital Marketing",
            "description": "Master modern digital marketing strategies, content planning, performance measurement, and social media growth.",
            "tools": ["SEO", "Content Strategy", "Ads", "Analytics"],
            "instructor": "Miss. Eniola Nehemotallah",
            "duration": "8 weeks",
            "curriculum": "Brand strategy, SEO, paid media, analytics, campaign planning",
            "fee": "₦65,000",
            "start_date": "30 Nov 2026",
            "certificate": "Certificate with digital marketing workflows",
        },
        {
            "name": "Cyber Security",
            "description": "Learn the foundations of cyber defense, threat analysis, system protection, and digital risk awareness.",
            "tools": ["Networking", "Security Tools", "Risk Analysis", "Threat Intelligence"],
            "instructor": "Mr. Chidi Okoye",
            "duration": "9 weeks",
            "curriculum": "Cyber hygiene, vulnerability analysis, security monitoring, incident response basics",
            "fee": "₦95,000",
            "start_date": "16 Nov 2026",
            "certificate": "Cybersecurity awareness and practical defense certificate",
        },
        {
            "name": "AI Automation",
            "description": "Build practical automations that save time, improve workflows, and create smarter business processes.",
            "tools": ["Python", "Zapier", "AI Tools", "Workflow Design"],
            "instructor": "Mr. Samuel Adeyemi",
            "duration": "6 weeks",
            "curriculum": "Prompt design, automation logic, no-code productivity, AI workflow implementation",
            "fee": "₦75,000",
            "start_date": "02 Dec 2026",
            "certificate": "Completion certificate + project portfolio",
        },
        {
            "name": "Content Writing and Video Editing",
            "description": "Create compelling written content and polished video stories that engage audiences across digital channels.",
            "tools": ["Writing", "Storytelling", "Video Editing", "Content Strategy"],
            "instructor": "Ms. Tolu Akinwumi",
            "duration": "6 weeks",
            "curriculum": "Content planning, script writing, video production, editing workflows, publishing strategy",
            "fee": "₦60,000",
            "start_date": "08 Dec 2026",
            "certificate": "Certificate in content creation and video storytelling",
        },
        {
            "name": "Graphics Design",
            "description": "Create impactful visuals, brand identities, and digital creatives that communicate effectively.",
            "tools": ["Canva", "Photoshop", "Illustrator", "Brand Design"],
            "instructor": "Mr. Daniel Kalu",
            "duration": "6 weeks",
            "curriculum": "Design systems, typography, layouts, branding, design presentation",
            "fee": "₦60,000",
            "start_date": "14 Dec 2026",
            "certificate": "Certificate and portfolio showcase",
        },
    ]


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/research-institute")
def research_institute():
    return render_template("research_institute.html")


@app.route("/tech-skillup")
def tech_skillup():
    return render_template("tech_skillup.html", programs=skill_programs())


@app.route("/tech-skills-dashboard", methods=["GET", "POST"])
def tech_skills_dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    programs = skill_programs()
    selected_skill = session.get("selected_skill") or user["course"] or ""
    selected_mode = session.get("selected_mode") or user["learning_mode"] or ""
    selected_schedule = session.get("selected_schedule") or "Flexible"

    if request.method == "POST":
        selected_skill = request.form.get("preferred_skill", selected_skill)
        selected_mode = request.form.get("learning_mode", selected_mode)
        selected_schedule = request.form.get("schedule", selected_schedule)

        session["selected_skill"] = selected_skill
        session["selected_mode"] = selected_mode
        session["selected_schedule"] = selected_schedule

        get_db().execute(
            "UPDATE users SET course = ?, learning_mode = ? WHERE id = ?",
            (selected_skill, selected_mode, user["id"]),
        )
        get_db().commit()

        if selected_skill and selected_mode:
            flash(f"Your {selected_skill} preference has been saved for the {selected_mode} delivery format.")

    return render_template(
        "tech_skill_dashboard.html",
        user=user,
        programs=programs,
        selected_skill=selected_skill,
        selected_mode=selected_mode,
        selected_schedule=selected_schedule,
    )


@app.route("/research-payment", methods=["GET", "POST"])
def research_payment():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        session["research_payment_status"] = "paid"
        session["research_payment_option"] = "one-time"
        session["research_payment_amount"] = "₦25,000"
        flash("Research payment recorded successfully. You can now proceed to your dashboard.")
        return redirect(url_for("dashboard"))

    return render_template(
        "payment.html",
        portal="research",
        title="IOS Research Institute",
        description="A one-time registration and project support fee secures your research placement and onboarding.",
        fee="₦25,000",
        payment_options=["One-time payment (₦25,000)"],
        demo_note="Demo checkout: this is a sample payment flow for onboarding and project support.",
    )


@app.route("/tech-payment", methods=["GET", "POST"])
def tech_payment():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        payment_option = request.form.get("payment_option", "single")
        if payment_option == "split":
            session["tech_payment_status"] = "paid"
            session["tech_payment_option"] = "split"
            session["tech_payment_amount"] = "₦50,000 total (₦25,000 + ₦25,000)"
            get_db().execute("UPDATE users SET payment_mode = ? WHERE id = ?", ("split", user["id"]))
            get_db().commit()
            flash("Payment successful! Your split plan is now active on your IOS Tech Skills dashboard.")
        else:
            session["tech_payment_status"] = "paid"
            session["tech_payment_option"] = "single"
            session["tech_payment_amount"] = "₦50,000"
            get_db().execute("UPDATE users SET payment_mode = ? WHERE id = ?", ("single", user["id"]))
            get_db().commit()
            flash("Payment successful! Welcome to your IOS Tech Skills dashboard.")
        return redirect(url_for("tech_skills_dashboard"))

    return render_template(
        "payment.html",
        portal="tech",
        title="IOS Tech SkillUp",
        description="The skill program has a ₦50,000 total fee. You may pay it once or split it into two installments as a demo payment plan.",
        fee="₦50,000",
        payment_options=["Pay once (₦50,000)", "Pay twice (₦25,000 + ₦25,000)"],
        demo_note="Demo checkout: this is a sample onboarding payment flow for the Tech Skills portal.",
    )


@app.route("/educational-consultancy")
def educational_consultancy():
    services = [
        "Academic counselling",
        "Career guidance",
        "SIWES support",
        "Student development",
        "Educational advisory",
        "Tutorials",
        "Examination preparation",
        "Institutional services",
    ]
    return render_template("educational_consultancy.html", services=services)


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
        if user["role"] == "researcher":
            status = row_value(user, "researcher_assessment_status", "not_started") or "not_started"
            if status in {"not_started", ""}:
                return redirect(url_for("researcher_assessment"))
            return redirect(url_for("researcher_dashboard"))
        if user["role"] in {"student", "client"}:
            course = row_value(user, "course")
            learning_mode = row_value(user, "learning_mode")
            if course and learning_mode:
                return redirect(url_for("tech_skills_dashboard"))
            return redirect(url_for("dashboard"))
        return redirect(url_for("register"))


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


@app.route("/researcher-assessment", methods=["GET", "POST"])
def researcher_assessment():
    user = current_user()
    if not user or user["role"] != "researcher":
        return redirect(url_for("login"))

    if request.method == "POST":
        research_area = request.form.get("research_area", "").strip()
        essay_title = request.form.get("essay_title", "").strip()
        essay_text = request.form.get("essay_text", "").strip()
        word_count = len(essay_text.split()) if essay_text else 0

        if not research_area or not essay_title or not essay_text:
            flash("Please complete the research assessment form before submitting.")
            return render_template("researcher_assessment.html", user=user, form=request.form)

        if word_count < 1500:
            flash("Your article must be at least 1500 words for researcher assessment review.")
            return render_template("researcher_assessment.html", user=user, form=request.form)

        get_db().execute(
            "UPDATE users SET researcher_assessment_area = ?, researcher_assessment_title = ?, researcher_assessment_text = ?, researcher_assessment_status = ?, researcher_assessment_word_count = ? WHERE id = ?",
            (research_area, essay_title, essay_text, "submitted", word_count, user["id"]),
        )
        get_db().commit()
        flash("Your research assessment has been submitted and is now under admin review.")
        return redirect(url_for("researcher_dashboard"))

    return render_template("researcher_assessment.html", user=user, form={})


@app.route("/researcher-dashboard")
def researcher_dashboard():
    user = current_user()
    if not user or user["role"] != "researcher":
        return redirect(url_for("login"))

    assessment_status = row_value(user, "researcher_assessment_status", "not_started") or "not_started"
    assigned_queue = [
        {"id": 1, "topic": "Impact of renewable energy financing on industrial growth", "status": "In review", "student": "Ada Okafor"},
        {"id": 2, "topic": "Public health expenditure and economic growth in Nigeria", "status": "Ready for review", "student": "Tunde Lawal"},
        {"id": 3, "topic": "Digital inclusion and education outcomes in urban schools", "status": "Awaiting data", "student": "Kemi Adebayo"},
    ]

    cv_file = row_value(user, "cv_file")
    portfolio_file = row_value(user, "portfolio_file")
    cv_url = "/static/uploads/researchers/" + (cv_file or "") if cv_file else None
    portfolio_url = "/static/uploads/researchers/" + (portfolio_file or "") if portfolio_file else None

    return render_template(
        "researcher_dashboard.html",
        user=user,
        queue=assigned_queue,
        assessment_status=assessment_status,
        cv_url=cv_url,
        portfolio_url=portfolio_url,
    )


@app.route("/researcher-upload-documents", methods=["POST"])
def researcher_upload_documents():
    user = current_user()
    if not user or user["role"] != "researcher":
        return redirect(url_for("login"))

    upload_dir = os.path.join(app.static_folder, "uploads", "researchers")
    os.makedirs(upload_dir, exist_ok=True)

    for document_type in ["cv_file", "portfolio_file"]:
        file = request.files.get(document_type)
        if not file or file.filename == "":
            continue

        safe_name = secure_filename(file.filename)
        unique_name = f"{user['id']}_{document_type}_{safe_name}"
        file_path = os.path.join(upload_dir, unique_name)
        file.save(file_path)
        get_db().execute(
            f"UPDATE users SET {document_type} = ? WHERE id = ?",
            (unique_name, user["id"]),
        )
        get_db().commit()
        flash(f"{document_type.replace('_', ' ').title()} uploaded successfully.")

    return redirect(url_for("researcher_dashboard"))


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

    metrics = {
        "users": 1245,
        "researchers": 38,
        "active_projects": 76,
        "completed_projects": 412,
        "courses": 24,
        "revenue": "₦12.4M",
    }

    return render_template("admin_dashboard.html", user=user, requests=rows, metrics=metrics)


@app.route("/tech-register", methods=["GET", "POST"])
def tech_register():
    courses = [program["name"] for program in skill_programs()]

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_number = request.form.get("phone_number", "").strip()
        course = request.form.get("course", "").strip()
        gender = request.form.get("gender", "").strip()
        learning_mode = request.form.get("learning_mode", "").strip()
        password = request.form.get("password", "")

        if not full_name or not email or not phone_number or not course or not gender or not learning_mode or not password:
            flash("Please complete all Tech Skills registration fields.")
            return render_template("tech_register.html", courses=courses, form=request.form)

        db = get_db()
        existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("An account with this email already exists.")
            return render_template("tech_register.html", courses=courses, form=request.form)

        db.execute(
            "INSERT INTO users (name, email, password, phone_number, gender, course, learning_mode, role, payment_mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                full_name,
                email,
                generate_password_hash(password, method="pbkdf2:sha256"),
                phone_number,
                gender,
                course,
                learning_mode,
                "student",
                "pending",
            ),
        )
        db.commit()

        user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        session["user_id"] = user["id"]
        session["role"] = "student"
        session["selected_skill"] = course
        session["selected_mode"] = learning_mode
        session["selected_schedule"] = request.form.get("schedule", "") or "Flexible"

        send_confirmation_email(email, full_name, "Student")
        return redirect(url_for("tech_payment"))

    return render_template("tech_register.html", courses=courses, form={})


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
            "INSERT INTO users (name, email, password, role, researcher_assessment_status) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, generate_password_hash(password, method="pbkdf2:sha256"), role, "not_started" if role == "researcher" else None),
        )
        db.commit()

        if role == "researcher":
            user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            session["user_id"] = user["id"]
            session["role"] = role
            send_confirmation_email(email, full_name, role_label(role))
            flash("Your researcher account has been created. Please complete the research assessment before your dashboard access is approved.")
            return redirect(url_for("researcher_assessment"))

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
