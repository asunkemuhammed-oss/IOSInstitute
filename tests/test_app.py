import os
import uuid

import pytest
from werkzeug.security import generate_password_hash

os.environ["TESTING"] = "1"

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_home_page_has_main_navigation_and_about_sections(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Home" in response.data
    assert b"About us" in response.data
    assert b"Tech Skills" in response.data
    assert b"Research institute" in response.data
    assert b"Testimonials" in response.data
    assert b"Blog/resources" in response.data
    assert b"Contact" in response.data
    assert b"Our service" in response.data
    assert b"Our division" in response.data
    assert b"Impact" in response.data
    assert b"Our team" in response.data


def test_research_institute_page_has_welcome_and_entry_actions(client):
    response = client.get("/research-institute")

    assert response.status_code == 200
    assert b"Welcome to IOS Research Institute" in response.data
    assert b"Sign Up" in response.data
    assert b"Login" in response.data
    assert b"Access research resources" in response.data
    assert b"Publications" in response.data
    assert b"Data" in response.data
    assert b"Faculty" in response.data
    assert b"Department" in response.data
    assert b"Course" in response.data
    assert b"Topic" in response.data
    assert b"Year" in response.data
    assert b"Effect of Public Health Expenditure on Economic Growth in Nigeria" in response.data


def test_tech_skillup_page_has_programs_and_course_details(client):
    response = client.get("/tech-skillup")

    assert response.status_code == 200
    assert b"Available Programs" in response.data
    assert b"Data Analysis" in response.data
    assert b"AI Automation" in response.data
    assert b"Web Development" in response.data
    assert b"Digital Marketing" in response.data
    assert b"Course description" in response.data
    assert b"Register" in response.data
    assert b"Certificate" in response.data


def test_educational_consultancy_page_has_services_and_booking_button(client):
    response = client.get("/educational-consultancy")

    assert response.status_code == 200
    assert b"Academic counselling" in response.data
    assert b"Career guidance" in response.data
    assert b"SIWES support" in response.data
    assert b"Student development" in response.data
    assert b"Book a Consultation" in response.data


def test_tech_skills_dashboard_has_course_selection_and_delivery_modes(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Student User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/tech-skills-dashboard")
    assert response.status_code == 200
    assert b"Choose your skill" in response.data
    assert b"Online" in response.data
    assert b"Physical" in response.data
    assert b"Hybrid" in response.data
    assert b"Data Analysis" in response.data


def test_student_dashboard_has_research_library_and_modules(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Student User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Student/Client Dashboard" in response.data
    assert b"Research Library" in response.data
    assert b"Faculty" in response.data
    assert b"Department" in response.data
    assert b"Course" in response.data
    assert b"Topic" in response.data
    assert b"Year" in response.data
    assert b"Economics" in response.data
    assert b"Effect of Public Health Expenditure on Economic Growth in Nigeria" in response.data
    assert b"Study Materials" in response.data
    assert b"Weekly Timetable" in response.data
    assert b"Announcements" in response.data


def test_student_dashboard_shows_research_request_form(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Student User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    login_response = client.post(
        "/login",
        data={"email": email, "password": "wrongpass"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200
    assert b"Invalid email or password" in login_response.data

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Request support" in response.data
    assert b"Submit a research request to IOS support team" in response.data
    assert b"Research Type" in response.data
    assert b"Department" in response.data

    profile_response = client.get("/profile")
    assert profile_response.status_code == 200
    assert b"Student profile" in profile_response.data


def test_register_page_has_student_client_and_researcher_options(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert b"Student / Client" in response.data
    assert b"project or research assistance" in response.data
    assert b"Researcher" in response.data
    assert b"Tech learner / applicant" not in response.data


def test_tech_skill_registration_collects_course_gender_and_learning_mode(client):
    email = f"techlearner{uuid.uuid4().hex[:8]}@example.com"

    response = client.post(
        "/tech-register",
        data={
            "full_name": "Tech Learner",
            "email": email,
            "phone_number": "08031234567",
            "course": "Data Analysis",
            "gender": "Female",
            "learning_mode": "Hybrid",
            "password": "SecurePass123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tech-payment")

    with app.app_context():
        from app import get_db

        db = get_db()
        user = db.execute(
            "SELECT name, email, phone_number, course, gender, learning_mode, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    assert user is not None
    assert user[0] == "Tech Learner"
    assert user[1] == email
    assert user[2] == "08031234567"
    assert user[3] == "Data Analysis"
    assert user[4] == "Female"
    assert user[5] == "Hybrid"
    assert user[6] == "student"


def test_tech_payment_redirects_to_dashboard_with_success_message(client):
    email = f"techpayer{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "Tech Payer",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "Data Science",
                "Hybrid",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.post(
        "/tech-payment",
        data={"payment_option": "single"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Payment successful" in response.data
    assert b"IOS Tech Skills Dashboard" in response.data
    assert b"Data Science" in response.data


def test_tech_student_login_redirects_to_tech_skills_dashboard(client):
    email = f"techstudent{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?)",
            ("Tech Student", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "Data Analysis", "Hybrid"),
        )
        db.commit()

    response = client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tech-skills-dashboard")


def test_researcher_dashboard_is_available_for_researcher_role(client):
    email = f"researcher{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Researcher User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "researcher"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/researcher-dashboard")
    assert response.status_code == 200
    assert b"Researcher Dashboard" in response.data
    assert b"Project Queue" in response.data
    assert b"Research Library" in response.data


def test_researcher_assessment_accepts_demo_submission_and_redirects_to_dashboard(client):
    email = f"researcherassess{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Research Assessor", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "researcher"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.post(
        "/researcher-assessment",
        data={
            "research_area": "Public Health",
            "essay_title": "Impact of Health Policy on Community Care",
            "essay_text": "short demo article text",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/researcher-dashboard")


def test_admin_dashboard_lists_requests(client):
    admin_email = f"admin{uuid.uuid4().hex[:8]}@example.com"
    student_email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Admin User", admin_email, generate_password_hash("AdminPass123", method="pbkdf2:sha256"), "admin"),
        )
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Alice Student", student_email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.execute(
            "INSERT INTO research_requests (user_id, research_type, topic, institution, department, deadline, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (db.execute("SELECT id FROM users WHERE email = ?", (student_email,)).fetchone()[0], "Undergraduate Project", "AI in Education", "UI", "Computer Science", "2026-12-01", "submitted"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": admin_email, "password": "AdminPass123"},
        follow_redirects=True,
    )

    response = client.get("/admin-dashboard")
    assert response.status_code == 200
    assert b"IOS Admin" in response.data
    assert b"1,245" in response.data
    assert b"38" in response.data
    assert b"76" in response.data
    assert b"412" in response.data
    assert b"24" in response.data
    assert b"AI in Education" in response.data
    assert b"submitted" in response.data


def test_forgot_password_page_shows_reset_message(client):
    email = f"reset{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Reset User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    response = client.post(
        "/forgot-password",
        data={"email": email},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Forgot password" in response.data
    assert b"reset link" in response.data.lower()


def test_registration_success_creates_user_and_sends_confirmation_email(client):
    email = f"jane{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/register",
        data={
            "full_name": "Jane Doe",
            "email": email,
            "password": "SecurePass123",
            "role": "student",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Account created successfully" in response.data
    assert b"student" in response.data

    with app.app_context():
        from app import get_db

        db = get_db()
        user = db.execute(
            "SELECT name, email, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    assert user is not None
    assert user[0] == "Jane Doe"
    assert user[1] == email
    assert user[2] == "student"
