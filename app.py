import os
import re
import sqlite3
from email.message import EmailMessage
from math import ceil
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


def save_uploaded_researcher_document(user_id, file, document_type):
    if not file or not getattr(file, "filename", None):
        return

    upload_dir = os.path.join(app.static_folder, "uploads", "researchers")
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(file.filename)
    unique_name = f"{user_id}_{document_type}_{safe_name}"
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)
    get_db().execute(
        f"UPDATE users SET {document_type} = ? WHERE id = ?",
        (unique_name, user_id),
    )
    get_db().commit()


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


def tech_application_fee_paid(user):
    if user is None:
        return False
    payment_state = str(row_value(user, "payment_mode", "pending") or "pending").strip().lower()
    return payment_state in {"single", "split", "paid", "approved", "complete", "monthly"}


def parse_money(value):
    if value is None:
        return 0
    cleaned = re.sub(r"[^0-9]", "", str(value))
    if not cleaned:
        return 0
    return int(cleaned)


def normalize_course_names(raw_value):
    items = []
    if raw_value is None:
        return items
    if isinstance(raw_value, (list, tuple)):
        raw_value = ",".join(str(item) for item in raw_value)
    for part in str(raw_value).split(","):
        cleaned = part.strip()
        if cleaned:
            items.append(cleaned)
    return items


def course_payment_summary(course_names):
    normalized = normalize_course_names(course_names)
    if not normalized:
        return {"items": [], "total": 0, "display": "₦0"}

    program_map = {program["name"]: program for program in skill_programs()}
    breakdown = []
    total = 0
    for name in normalized:
        program = program_map.get(name)
        if not program:
            continue
        amount = parse_money(program.get("fee", 0))
        total += amount
        breakdown.append({"name": name, "amount": amount, "display": program.get("fee", "₦0")})

    return {
        "items": breakdown,
        "total": total,
        "display": f"₦{total:,}",
    }


def skill_programs():
    return [
        {
            "name": "Data Analysis",
            "description": "Learn how to turn raw data into business decisions using Excel, Power BI, SQL, and Python.",
            "tools": ["Excel", "Power BI", "SQL", "Python"],
            "instructor": "Dr. Amina Yusuf",
            "duration": "3 months",
            "curriculum": [
                "SQL For Data Analysis",
                "Introduction to Python Programming",
                "Microsoft Excel",
                "Statistics for Data Analysis with python",
                "Business Intelligence with PowerBI",
            ],
            "fee": "₦150,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Industry-recognized certificate upon completion",
            "image": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Data Science",
            "description": "Understand data science fundamentals, model building, and evidence-based decision making for real-world problems.",
            "tools": ["Python", "Pandas", "NumPy", "Machine Learning"],
            "instructor": "Prof. Ijeoma Eze",
            "duration": "4 months",
            "curriculum": [
                "SQL For Data Science",
                "Introduction to Python Programming",
                "Statistics for Data Science",
                "iPython",
                "Machine Learning",
                "Deep Learning Frameworks & Architectures",
            ],
            "fee": "₦200,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Certificate and capstone project assessment",
            "image": "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Web Development",
            "description": "Learn how to design and build responsive, user-friendly websites and digital products.",
            "tools": ["HTML", "CSS", "JavaScript", "React"],
            "instructor": "Mrs. Grace Okafor",
            "duration": "12 weeks",
            "curriculum": "Front-end design, interactivity, APIs, deployment, project building",
            "fee": "₦150,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Certificate + live project submission",
            "image": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Financial Analysis",
            "description": "Understand budgeting, reporting, forecasting, and performance analysis for smarter financial decisions.",
            "tools": ["Excel", "Forecasting", "Budgeting", "Reporting"],
            "instructor": "Mr. Adebayo Oladipo",
            "duration": "3 months",
            "curriculum": [
                "Linear analysis",
                "Ratio analysis",
                "Budget planning",
                "Scenario analysis",
                "Interpretation",
            ],
            "fee": "₦150,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Certificate in financial analysis and decision support",
            "image": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Digital Marketing",
            "description": "Master modern digital marketing strategies, content planning, performance measurement, and social media growth.",
            "tools": ["SEO", "Content Strategy", "Ads", "Analytics"],
            "instructor": "Miss. Eniola Nehemotallah",
            "duration": "2 months",
            "curriculum": [
                "Content Marketing",
                "Email Marketing",
                "SEO",
                "SMM",
                "Ads",
                "Copywriting",
                "WordPress",
            ],
            "fee": "₦100,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Certificate with digital marketing workflows",
            "image": "/static/images/DIGITAL.jpg",
        },
        {
            "name": "Cyber Security",
            "description": "Build practical skills in digital defense, network protection, threat analysis, and security best practices for safer systems and online environments.",
            "tools": ["Networking", "Security Tools", "Linux", "Ethical Hacking", "SIEM"],
            "instructor": "Mr. Chidi Okoye",
            "duration": "4 months",
            "curriculum": [
                "Introduction to Cybersecurity",
                "Networking Fundamentals and Security",
                "Operating System and Security (Windows & Linux)",
                "Web Application Security",
                "Introduction to Ethical Hacking",
                "Basic Security Tools and Techniques",
                "Cybersecurity Best Practices and Legal Considerations",
                "Log Monitoring and Analysis using SIEM tools",
            ],
            "fee": "₦290,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Cybersecurity awareness and practical defense certificate",
            "image": "/static/images/CYBERjpg",
        },
        {
            "name": "AI Automation & Advanced Digital Marketing",
            "description": "Build practical automations that save time, improve workflows, and create smarter business processes.",
            "tools": ["AI", "Marketing Automation", "AI Copywriting", "Funnels"],
            "instructor": "Mr. Samuel Adeyemi",
            "duration": "3 months",
            "curriculum": [
                "Generative AI for Marketing",
                "AI Copywriting & Content Automation",
                "AI Video Creation & Graphic Design",
                "AI Landing Pages & Funnel Building",
                "AI Vibe Coding (No-Code Product Creation)",
                "Monetization",
                "Marketing Automation (Make & Zapier)",
                "AI-Powered Paid Advertising",
                "CPA & Performance Marketing",
                "Advanced Email Marketing & AI Automation",
                "AI Analytics, Tracking & Optimization",
                "AI-Powered Social Media Growth Systems",
                "Agency Systems & Client Acquisition",
            ],
            "fee": "₦200,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Completion certificate + project portfolio",
            "image": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Content Writing and Video Editing",
            "description": "Create compelling written content and polished video stories that engage audiences across digital channels.",
            "tools": ["Writing", "Storytelling", "Video Editing", "Content Strategy"],
            "instructor": "Ms. Tolu Akinwumi",
            "duration": "2 months",
            "curriculum": [
                "Introduction to Content Creation and Digital Media",
                "Idea Generation and Storytelling",
                "Content Writing, Copywriting and Scriptwriting",
                "Social Media Content Creation and Content Strategy",
                "Video Editing Techniques: Cutting, Transitions and Effects",
                "Audio Editing, Subtitles, Colour Correction and Branding",
                "AI Tools, Content Publishing, Portfolio Development and Freelancing",
                "Recommended Tools: CapCut, Canva, VN Video Editor",
            ],
            "fee": "₦100,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Certificate in content creation and video storytelling",
            "image": "https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Web Development",
            "description": "A full-stack engineering career path involves becoming skilled in both front-end and back-end development for websites and applications. This means you'll learn how to create the user interface that people see and interact with (front-end) as well as the behind-the-scenes logic, databases, and servers (back-end).",
            "tools": ["HTML", "CSS", "JavaScript", "React", "Node.js", "MongoDB"],
            "instructor": "Mrs. Grace Okafor",
            "duration": "5 months",
            "curriculum": [
                "Front-end Engineering",
                "Back-end Engineering",
            ],
            "fee": "₦300,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Certificate + live project submission",
            "image": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Graphics Design",
            "description": "Create impactful visuals, brand identities, and digital creatives that communicate effectively.",
            "tools": ["Canva", "Photoshop", "Illustrator", "Brand Design"],
            "instructor": "Mr. Daniel Kalu",
            "duration": "2 months",
            "curriculum": [
                "Graphic design basics",
                "Adobe Photoshop",
                "Photo Manipulations",
                "Adobe illustrator",
                "Brands Identity",
            ],
            "fee": "₦80,000",
            "discount": "50% OFF",
            "schedule": "3 days/week · 2 hours/day",
            "start_date": "03 Jan 2027",
            "certificate": "Certificate and portfolio showcase",
            "image": "/static/images/GRAPHICS.jpg",
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

    if user["role"] in {"student", "client"} and row_value(user, "course") and row_value(user, "learning_mode") and not tech_application_fee_paid(user):
        flash("Please complete the ₦8,500 application fee before you can access your dashboard.")
        return redirect(url_for("tech_payment"))

    programs = skill_programs()
    selected_skill = session.get("selected_skill") or user["course"] or ""
    selected_courses = normalize_course_names(session.get("selected_courses") or user["course"] or selected_skill)
    selected_mode = session.get("selected_mode") or user["learning_mode"] or ""
    selected_schedule = session.get("selected_schedule") or "Flexible"
    course_payment_status = session.get("tech_course_payment_status") == "paid"
    course_summary = course_payment_summary(selected_courses)

    if request.method == "POST":
        selected_skill = request.form.get("preferred_skill", selected_skill)
        selected_mode = request.form.get("learning_mode", selected_mode)
        selected_schedule = request.form.get("schedule", selected_schedule)
        selected_courses = normalize_course_names(request.form.getlist("course") or selected_skill)

        session["selected_skill"] = selected_skill
        session["selected_mode"] = selected_mode
        session["selected_schedule"] = selected_schedule
        session["selected_courses"] = selected_courses

        if not course_payment_status and selected_courses:
            flash("Select your course(s) and complete the tuition checkout before your skill plan is activated.")
            return redirect(url_for("tech_course_payment"))

        get_db().execute(
            "UPDATE users SET course = ?, learning_mode = ? WHERE id = ?",
            (", ".join(selected_courses) if selected_courses else selected_skill, selected_mode, user["id"]),
        )
        get_db().commit()

        if selected_skill and selected_mode:
            flash(f"Your {selected_skill} preference has been saved for the {selected_mode} delivery format.")

    return render_template(
        "tech_skill_dashboard.html",
        user=user,
        programs=programs,
        selected_skill=selected_skill,
        selected_courses=selected_courses,
        selected_mode=selected_mode,
        selected_schedule=selected_schedule,
        course_payment_status=course_payment_status,
        course_payment_total=course_summary["display"],
    )


@app.route("/tech-course-payment", methods=["GET", "POST"])
def tech_course_payment():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    if not tech_application_fee_paid(user):
        flash("Please complete the ₦8,500 application fee before selecting your course(s).")
        return redirect(url_for("tech_payment"))

    programs = skill_programs()
    chosen_courses = normalize_course_names(
        request.form.getlist("course")
        or request.form.get("course")
        or request.form.get("preferred_skill")
        or session.get("selected_courses")
        or user["course"]
    )
    summary = course_payment_summary(chosen_courses)

    if request.method == "POST":
        chosen_courses = normalize_course_names(request.form.getlist("course") or request.form.get("course") or request.form.get("preferred_skill"))
        if not chosen_courses:
            flash("Please select at least one course before making payment.")
            return redirect(url_for("tech_skills_dashboard"))

        payment_option = request.form.get("payment_option", "single")
        summary = course_payment_summary(chosen_courses)
        session["selected_courses"] = chosen_courses
        session["selected_skill"] = chosen_courses[0]
        session["tech_course_payment_status"] = "paid"
        session["tech_course_payment_option"] = payment_option
        session["tech_course_payment_total"] = summary["display"]

        get_db().execute(
            "UPDATE users SET course = ?, learning_mode = ? WHERE id = ?",
            (", ".join(chosen_courses), session.get("selected_mode") or user["learning_mode"] or "Hybrid", user["id"]),
        )
        get_db().commit()

        flash(f"Paystack Demo: course payment of {summary['display']} was successfully received for {', '.join(chosen_courses)}.")
        return redirect(url_for("tech_skills_dashboard"))

    payment_options = [
        {"label": f"Pay once ({summary['display']})", "value": "single"},
        {"label": f"Pay twice ({summary['display']} total, split into two instalments)", "value": "split"},
    ]

    return render_template(
        "payment.html",
        portal="tech-course",
        title="Course tuition payment",
        description="Choose your course(s), review the tuition total, and complete a demo Paystack checkout before your final enrolment is activated.",
        fee=summary["display"],
        payment_options=payment_options,
        selected_courses=summary["items"],
        total_amount=summary["display"],
        demo_note="Demo checkout: this is a sample Paystack-style payment flow for tech course tuition.",
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
            session["tech_payment_amount"] = "₦8,500 total (₦4,250 + ₦4,250)"
            get_db().execute("UPDATE users SET payment_mode = ? WHERE id = ?", ("split", user["id"]))
            get_db().commit()
            flash("Payment successful! Your split plan is now active on your IOS Tech SkillUp dashboard.")
        else:
            session["tech_payment_status"] = "paid"
            session["tech_payment_option"] = "single"
            session["tech_payment_amount"] = "₦8,500"
            get_db().execute("UPDATE users SET payment_mode = ? WHERE id = ?", ("single", user["id"]))
            get_db().commit()
            flash("Payment successful! Welcome to your IOS Tech SkillUp dashboard.")
        return redirect(url_for("tech_skills_dashboard"))

    payment_options = [
        {"label": "Pay once (₦8,500)", "value": "single"},
        {"label": "Pay every month (₦4,250/month)", "value": "split"},
    ]
    return render_template(
        "payment.html",
        portal="tech",
        title="IOS Tech SkillUp",
        description="After the application form, you will be redirected to your portal to pay the one-time application fee of ₦8,500. Once this is completed, you will have access to your dashboard and can continue with your tuition plan.",
        fee="₦8,500",
        payment_options=payment_options,
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
    tech_mode = request.args.get("portal") == "tech"
    default_email = "admin@iosinstitute.com" if admin_mode else ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter your email and password.")
            return render_template("login.html", prefill_email=default_email, admin_mode=admin_mode, portal="tech" if tech_mode else "institute")

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password")
            return render_template("login.html", prefill_email=email, admin_mode=admin_mode, portal="tech" if tech_mode else "institute")

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
                if not tech_application_fee_paid(user):
                    return redirect(url_for("tech_payment"))
                return redirect(url_for("tech_skills_dashboard"))
            return redirect(url_for("dashboard"))
        return redirect(url_for("register"))

    return render_template("login.html", prefill_email=default_email, admin_mode=admin_mode, portal="tech" if tech_mode else "institute")


@app.route("/tech-login")
def tech_login():
    return redirect(url_for("login", portal="tech"))


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


def paginate_items(items, page, per_page=10):
    page = max(1, int(page or 1))
    total_items = len(items)
    total_pages = max(1, ceil(total_items / per_page)) if total_items else 1
    page = min(page, total_pages)
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total_pages


def admin_dashboard_data(active_view="overview", search_query="", page=1):
    user = current_user()
    if not user or user["role"] != "admin":
        return None

    search_query = (search_query or "").strip().lower()

    rows = get_db().execute(
        """
        SELECT rr.id, rr.research_type, rr.topic, rr.institution, rr.department, rr.deadline, rr.status, u.name AS student_name
        FROM research_requests rr
        JOIN users u ON u.id = rr.user_id
        ORDER BY rr.id DESC
        """
    ).fetchall()

    student_rows = get_db().execute(
        """
        SELECT id, name, email, role, course, learning_mode, payment_mode, created_at
        FROM users
        WHERE role IN ('student', 'client')
        ORDER BY created_at DESC
        """
    ).fetchall()

    tech_rows = get_db().execute(
        """
        SELECT name, email, course, learning_mode, payment_mode, created_at
        FROM users
        WHERE role IN ('student', 'client')
          AND (course IS NOT NULL OR learning_mode IS NOT NULL OR payment_mode IS NOT NULL)
        ORDER BY created_at DESC
        """
    ).fetchall()

    courses = skill_programs()

    def matches_search(row_dict):
        if not search_query:
            return True
        haystack = " ".join(str((row_dict.get(key) or "")).lower() for key in row_dict)
        return search_query in haystack

    filtered_requests = [
        row for row in rows
        if matches_search({
            "student_name": row["student_name"],
            "research_type": row["research_type"],
            "topic": row["topic"],
            "institution": row["institution"],
            "department": row["department"],
            "status": row["status"],
        })
    ]
    filtered_students = [
        row for row in student_rows
        if matches_search({
            "name": row["name"],
            "email": row["email"],
            "role": row["role"],
            "course": row["course"],
            "learning_mode": row["learning_mode"],
            "payment_mode": row["payment_mode"],
        })
    ]
    filtered_tech = [
        row for row in tech_rows
        if matches_search({
            "name": row["name"],
            "email": row["email"],
            "course": row["course"],
            "learning_mode": row["learning_mode"],
            "payment_mode": row["payment_mode"],
        })
    ]
    filtered_courses = [
        program for program in courses
        if not search_query or search_query in " ".join([
            program.get("name", ""),
            program.get("description", ""),
            program.get("instructor", ""),
            " ".join(program.get("tools", [])),
        ]).lower()
    ]

    page = max(1, int(page or 1))
    if active_view == "students":
        current_view_items = filtered_students
    elif active_view == "tech":
        current_view_items = filtered_tech
    elif active_view == "courses":
        current_view_items = filtered_courses
    else:
        current_view_items = filtered_requests

    paginated_requests, _, _ = paginate_items(filtered_requests, page)
    paginated_students, _, _ = paginate_items(filtered_students, page)
    paginated_tech, _, _ = paginate_items(filtered_tech, page)
    paginated_courses, _, _ = paginate_items(filtered_courses, page)
    current_view_page_items, current_page, total_pages = paginate_items(current_view_items, page)

    if active_view == "students":
        paginated_students = current_view_page_items
    elif active_view == "tech":
        paginated_tech = current_view_page_items
    elif active_view == "courses":
        paginated_courses = current_view_page_items
    elif active_view == "research":
        paginated_requests = current_view_page_items

    pending_research = sum(1 for row in rows if str(row["status"]).lower() in {"submitted", "in review"})
    approved_research = sum(1 for row in rows if str(row["status"]).lower() == "approved")
    completed_research = sum(1 for row in rows if str(row["status"]).lower() == "completed")

    metrics = {
        "users": 1245,
        "researchers": 38,
        "active_projects": 76,
        "completed_projects": 412,
        "courses": 24,
        "revenue": "₦12.4M",
        "pending_research": pending_research,
        "approved_research": approved_research,
        "completed_research": completed_research,
        "student_count": len(student_rows),
        "tech_count": len(tech_rows),
    }

    return {
        "user": user,
        "requests": paginated_requests,
        "students": paginated_students,
        "tech_enrollments": paginated_tech,
        "courses": paginated_courses,
        "metrics": metrics,
        "active_view": active_view,
        "search_query": search_query,
        "page": current_page,
        "total_pages": total_pages,
        "per_page": 10,
    }


@app.route("/admin-dashboard", methods=["GET", "POST"])
@app.route("/admin-dashboard/overview", methods=["GET", "POST"])
def admin_dashboard():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))

    active_view = request.args.get("view", "overview") or "overview"
    search_query = (request.args.get("q", "") or "").strip().lower()
    page = request.args.get("page", 1, type=int) or 1

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

    context = admin_dashboard_data(active_view=active_view, search_query=search_query, page=page)
    if context is None:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", **context)


@app.route("/admin-dashboard/students", methods=["GET", "POST"])
def admin_students():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))
    if request.method == "POST":
        return redirect(url_for("admin_students", q=request.args.get("q", "")))
    context = admin_dashboard_data(active_view="students", search_query=request.args.get("q", ""), page=request.args.get("page", 1, type=int) or 1)
    if context is None:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", **context)


@app.route("/admin-dashboard/research", methods=["GET", "POST"])
def admin_research():
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
    context = admin_dashboard_data(active_view="research", search_query=request.args.get("q", ""), page=request.args.get("page", 1, type=int) or 1)
    if context is None:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", **context)


@app.route("/admin-dashboard/tech", methods=["GET", "POST"])
def admin_tech():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))
    context = admin_dashboard_data(active_view="tech", search_query=request.args.get("q", ""), page=request.args.get("page", 1, type=int) or 1)
    if context is None:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", **context)


@app.route("/admin-dashboard/courses", methods=["GET", "POST"])
def admin_courses():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))
    context = admin_dashboard_data(active_view="courses", search_query=request.args.get("q", ""), page=request.args.get("page", 1, type=int) or 1)
    if context is None:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", **context)


@app.route("/admin-dashboard/settings", methods=["GET", "POST"])
def admin_settings():
    user = current_user()
    if not user or user["role"] != "admin":
        return redirect(url_for("login"))
    context = admin_dashboard_data(active_view="settings", search_query=request.args.get("q", ""), page=request.args.get("page", 1, type=int) or 1)
    if context is None:
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", **context)


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

        try:
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
        except sqlite3.IntegrityError:
            db.rollback()
            flash("An account with this email already exists. Please log in or use another email address.")
            return render_template("tech_register.html", courses=courses, form=request.form)

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

        try:
            db.execute(
                "INSERT INTO users (name, email, password, role, researcher_assessment_status) VALUES (?, ?, ?, ?, ?)",
                (full_name, email, generate_password_hash(password, method="pbkdf2:sha256"), role, "not_started" if role == "researcher" else None),
            )
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            flash("An account with this email already exists. Please log in or use a different email.")
            return render_template("register.html", form=request.form)

        if role == "researcher":
            user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            session["user_id"] = user["id"]
            session["role"] = role

            cv_file = request.files.get("cv_file")
            portfolio_file = request.files.get("portfolio_file")
            save_uploaded_researcher_document(user["id"], cv_file, "cv_file")
            save_uploaded_researcher_document(user["id"], portfolio_file, "portfolio_file")

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
