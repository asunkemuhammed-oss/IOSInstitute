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
    assert b"Admin dashboard" in response.data
    assert b"AI in Education" in response.data
    assert b"submitted" in response.data


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
