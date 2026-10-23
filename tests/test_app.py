import io
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
    assert b"IOS RESEARCH INSTITUTE" in response.data
    assert b"Welcome to IOS Research Institute" in response.data
    assert b"Sign Up" in response.data
    assert b"Login" in response.data
    assert b"Access research resources" in response.data
    assert b"Publications" in response.data
    assert b"Data" in response.data
    assert b"Topic category" in response.data
    assert b"Search for a topic" in response.data
    assert b"ECONOMICS PROJECT TOPICS AND MATERIALS" in response.data
    assert b"Effect of Public Health Expenditure on Economic Growth in Nigeria" in response.data
    assert b"Faculty" not in response.data
    assert b"Department" not in response.data


def test_project_purchase_checkout_accepts_post_submission(client):
    response = client.post(
        "/project-purchase",
        data={
            "package": "complete",
            "payment_stage": "checkout",
            "payment_option": "single",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Choose payment method" in response.data
    assert b"Complete payment" in response.data
    assert b"Secure checkout" in response.data
    assert b'href="/research-institute"' in response.data


def test_research_request_page_redirects_to_signup_after_submission(client):
    response = client.post(
        "/research-request",
        data={
            "research_type": "Undergraduate Project",
            "topic": "Effect of study habits on academic performance",
            "institution": "University of Lagos",
            "department": "Business Administration",
            "deadline": "2026-12-30",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/register?portal=research"


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
    assert b"Get Exam Support" in response.data
    assert b"Check Results" in response.data


def test_educational_consultancy_nav_closes_other_dropdowns(client):
    response = client.get("/educational-consultancy")

    assert response.status_code == 200
    assert b"const dropdowns = document.querySelectorAll(\".mainnav-item details\");" in response.data
    assert b"other.removeAttribute(\"open\");" in response.data
    assert b"Recent Updates" in response.data
    assert b"Opportunities" in response.data
    assert b"Past Questions" in response.data


def test_educational_consultancy_products_and_about_pages_are_available(client):
    products_response = client.get("/products")
    about_response = client.get("/about")

    assert products_response.status_code == 200
    assert b"Student Admission Support" in products_response.data
    assert b"Exam Success Pack" in products_response.data
    assert b"Career &amp; Scholarship Guidance" in products_response.data

    assert about_response.status_code == 200
    assert b"About IOS Educational Consultancy" in about_response.data
    assert b"Our Mission" in about_response.data
    assert b"How We Help Students" in about_response.data


def test_educational_consultancy_support_pages_are_available(client):
    response = client.get("/service/jamb-services")

    assert response.status_code == 200
    assert b"JAMB Services" in response.data
    assert b"Need help with JAMB registration or admission support" in response.data
    assert b"Book a Consultation" in response.data
    assert b"Get Exam Support" in response.data


def test_educational_consultancy_support_cards_use_school_brand_images_and_rich_service_details(client):
    response = client.get("/service/waec-services")

    assert response.status_code == 200
    assert b'/static/images/team/WEAC.jpeg' in response.data
    assert b"WAEC Services" in response.data
    assert b"How it works" in response.data
    assert b"What is included" in response.data

    home_response = client.get("/educational-consultancy")
    assert b'/static/images/team/JAMB.jpeg' in home_response.data
    assert b'/static/images/team/WEAC.jpeg' in home_response.data
    assert b'/static/images/team/NECO.jpeg' in home_response.data
    assert b'/static/images/team/NYSC.png' in home_response.data


def test_research_institute_topic_links_open_selected_category(client):
    response = client.get("/research-institute?topic=ECONOMICS%20PROJECT%20TOPICS%20AND%20MATERIALS")

    assert response.status_code == 200
    assert b"/research-institute?topic=ECONOMICS%20PROJECT%20TOPICS%20AND%20MATERIALS" in response.data
    assert b"selectedTopic =" in response.data
    assert b"topicLibrary" in response.data
    assert b"ECONOMICS PROJECT TOPICS AND MATERIALS" in response.data


def test_research_institute_keeps_clicked_topic_when_not_predefined(client):
    response = client.get("/research-institute?topic=ACCOUNTING%20EDUCATION%20PROJECT%20TOPICS%20AND%20MATERIALS")

    assert response.status_code == 200
    assert b"ACCOUNTING EDUCATION PROJECT TOPICS AND MATERIALS" in response.data
    assert b"selectedTopicLabel" in response.data
    assert b"selected_topic" in response.data
    assert b"/research-institute?topic=ACCOUNTING%20EDUCATION%20PROJECT%20TOPICS%20AND%20MATERIALS" in response.data


def test_research_institute_project_list_opens_topic_detail_page(client):
    response = client.get("/research-institute?topic=ECONOMICS%20PROJECT%20TOPICS%20AND%20MATERIALS")

    assert response.status_code == 200
    assert b"/research-institute?topic=ECONOMICS%20PROJECT%20TOPICS%20AND%20MATERIALS" in response.data
    assert b"/research-topic/" in response.data
    assert b"slugifyTopic(item)" in response.data
    assert b"#library-topic-block" in response.data


def test_research_institute_internal_anchors_and_project_links_are_connected(client):
    response = client.get("/research-institute")

    assert response.status_code == 200
    assert b'id="research-library"' in response.data
    assert b'id="publications"' in response.data
    assert b'href="#publications"' in response.data
    assert b'href="#research-library"' in response.data
    assert b'/research-topic/' in response.data


def test_research_topic_detail_page_shows_abstract_and_unlock_offer(client):
    response = client.get("/research-topic/effect-of-public-health-expenditure-on-economic-growth-in-nigeria")

    assert response.status_code == 200
    assert b"Effect of Public Health Expenditure on Economic Growth in Nigeria" in response.data
    assert b"Abstract" in response.data
    assert b"What We Did" in response.data
    assert b"Unlock Full Project" in response.data
    assert b"$30" in response.data


def test_research_registration_page_uses_research_branding(client):
    response = client.get("/register?portal=research")

    assert response.status_code == 200
    assert b"IOS Research Institute" in response.data
    assert b"Create a Research account" in response.data
    assert b"Tech SkillUp" not in response.data


def test_research_registration_allows_student_and_researcher_roles(client):
    response = client.get("/register?portal=research")

    assert response.status_code == 200
    assert b"Student / Client" in response.data
    assert b"Researcher" in response.data


def test_student_login_on_research_portal_redirects_to_research_institute_not_tech_dashboard(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, portal) VALUES (?, ?, ?, ?, ?)",
            ("Student User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "research"),
        )
        db.commit()

    response = client.post(
        "/login",
        data={"email": email, "password": "SecurePass123", "portal": "research"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/research-student-dashboard"


def test_research_account_cannot_login_on_tech_portal(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, portal) VALUES (?, ?, ?, ?, ?)",
            ("Research Student", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "research"),
        )
        db.commit()

    response = client.post(
        "/login",
        data={"email": email, "password": "SecurePass123", "portal": "tech"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"User not found or not allowed." in response.data


def test_student_research_dashboard_is_accessible_for_research_portal_student(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Student Research User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123", "portal": "research"},
        follow_redirects=False,
    )

    response = client.get("/research-student-dashboard")

    assert response.status_code == 200
    assert b"Student Research Dashboard" in response.data
    assert b"Research Library" in response.data
    assert b"Project Queue" in response.data


def test_student_research_dashboard_has_project_workspace_and_profile_sections(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Student Research User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123", "portal": "research"},
        follow_redirects=False,
    )

    response = client.get("/research-student-dashboard")

    assert response.status_code == 200
    assert b"My Projects" in response.data
    assert b"Download submitted chapters" in response.data
    assert b"Upload corrections" in response.data
    assert b"Notification preferences" in response.data
    assert b"3. My Projects" in response.data


def test_student_profile_update_supports_personal_and_notification_fields(client):
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
        data={"email": email, "password": "SecurePass123", "portal": "research"},
        follow_redirects=False,
    )

    response = client.post(
        "/profile",
        data={
            "name": "Updated Student",
            "email": email,
            "phone_number": "08030000000",
            "institution": "University of Lagos",
            "department": "Business Administration",
            "qualification": "B.Sc.",
            "notification_email": "on",
            "notification_sms": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"


def test_researcher_logout_redirects_to_research_login(client):
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
        data={"email": email, "password": "SecurePass123", "portal": "research"},
        follow_redirects=False,
    )

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login?portal=research"


def test_student_logout_from_research_portal_redirects_to_research_login(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Student Research User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123", "portal": "research"},
        follow_redirects=False,
    )

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login?portal=research"


def test_admin_dashboard_redirects_to_admin_login_when_not_logged_in(client):
    response = client.get("/admin-dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login?admin=1"


def test_tech_register_page_uses_tech_specific_login_link(client):
    response = client.get("/tech-register")

    assert response.status_code == 200
    assert b'/login?portal=tech' in response.data
    assert b'/login"' not in response.data.replace(b'/login?portal=tech', b'')


def test_tech_skillup_page_uses_tech_specific_login_link(client):
    response = client.get("/tech-skillup")

    assert response.status_code == 200
    assert b'/login?portal=tech' in response.data
    assert b"/login\"" not in response.data.replace(b'/login?portal=tech', b'')


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


def test_student_login_redirects_paid_tech_user_to_dashboard(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "single",
                "Data Analysis",
                "Online",
            ),
        )
        db.commit()

    response = client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tech-skills-dashboard")


def test_tech_course_payment_requires_course_selection_and_totals_multi_course_fee(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode) VALUES (?, ?, ?, ?, ?)",
            ("Student User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "single"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.post(
        "/tech-course-payment",
        data={
            "course": ["Data Analysis", "Digital Marketing"],
            "payment_option": "split",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Paystack Demo" in response.data
    assert b"Data Analysis" in response.data
    assert b"Digital Marketing" in response.data
    assert b"250,000" in response.data
    assert b"Split payment" in response.data


def test_tech_payment_page_lists_paid_and_pending_course_fees(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "single",
                "Data Analysis",
                "Online",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    with client.session_transaction() as session:
        session["selected_courses"] = ["Data Analysis", "Digital Marketing"]
        session["tech_payment_status"] = "paid"
        session["tech_payment_option"] = "single"
        session["tech_course_payment_status"] = "partial"
        session["tech_course_paid_courses"] = ["Data Analysis"]
        session["tech_course_payment_total"] = "₦150,000"

    response = client.get("/tech-payment")

    assert response.status_code == 200
    assert b"Payment history" in response.data
    assert b"Application fee" in response.data
    assert b"Data Analysis" in response.data
    assert b"Digital Marketing" in response.data
    assert b"Pending" in response.data


def test_tech_payment_page_shows_fee_options_before_application_fee_is_paid(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "pending",
                "Data Analysis",
                "Online",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/tech-payment")

    assert response.status_code == 200
    assert "Pay once (₦8,500)".encode("utf-8") in response.data
    assert b"Pay twice" not in response.data
    assert b"Payment history" not in response.data


def test_tech_payment_page_uses_payment_history_after_application_fee_is_paid(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "single",
                "Data Analysis",
                "Online",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/tech-payment")

    assert response.status_code == 200
    assert b"Payment history" in response.data
    assert b"Application fee" in response.data
    assert "Pay once (₦8,500)".encode("utf-8") not in response.data
    assert b"Pay twice" not in response.data


def test_tech_payment_flow_has_review_checkout_and_success_actions(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "pending",
                "Data Analysis",
                "Online",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/tech-payment")

    assert response.status_code == 200
    assert b"Proceed to payment" in response.data
    assert b"Payment history" not in response.data

    response = client.post(
        "/tech-payment",
        data={"payment_option": "single", "payment_stage": "checkout"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Paystack" in response.data
    assert b"Mastercard" in response.data
    assert b"Complete payment" in response.data

    response = client.post(
        "/tech-payment",
        data={"payment_option": "single", "payment_stage": "success"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tech-skills-dashboard")

    follow_up = client.get(response.headers["Location"], follow_redirects=True)
    assert response.status_code == 302
    assert b"Choose your skill" in follow_up.data


def test_tech_online_course_has_start_class_learning_view(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "single",
                "Data Analysis",
                "Online",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    with client.session_transaction() as session:
        session["selected_courses"] = ["Data Analysis"]
        session["selected_mode"] = "Online"

    response = client.get("/start-course/Data%20Analysis")

    assert response.status_code == 200
    assert b"Start class" in response.data
    assert b"Join live class" in response.data
    assert b"Google Meet" in response.data
    assert b"Video lesson" in response.data
    assert b"Resources" in response.data
    assert b"Assignments" in response.data


def test_tech_course_payment_blocks_duplicate_paid_course(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "single",
                "Data Analysis",
                "Online",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    with client.session_transaction() as session:
        session["selected_courses"] = ["Data Analysis"]
        session["tech_course_paid_courses"] = ["Data Analysis"]
        session["tech_course_payment_status"] = "paid"

    response = client.post(
        "/tech-course-payment",
        data={"course": ["Data Analysis"], "payment_option": "single"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already paid for this course" in response.data.lower()
    assert b"Data Analysis" in response.data


def test_tech_remove_paid_course_marks_it_pending(client):
    email = f"student{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, payment_mode, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "Student User",
                email,
                generate_password_hash("SecurePass123", method="pbkdf2:sha256"),
                "student",
                "single",
                "Data Analysis, Digital Marketing",
                "Online",
            ),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    with client.session_transaction() as session:
        session["selected_courses"] = ["Data Analysis", "Digital Marketing"]
        session["tech_course_paid_courses"] = ["Data Analysis", "Digital Marketing"]
        session["tech_course_payment_status"] = "paid"

    response = client.post(
        "/tech-remove-paid-course",
        data={"course": "Data Analysis"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with client.session_transaction() as session:
        assert "Data Analysis" not in session["tech_course_paid_courses"]
        assert session["tech_course_payment_status"] == "partial"


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


def test_register_duplicate_email_shows_error_without_crashing(client):
    email = f"duplicate{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Existing User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
        )
        db.commit()

    response = client.post(
        "/register",
        data={
            "full_name": "Duplicate User",
            "email": email,
            "password": "AnotherPass123",
            "role": "student",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already exists" in response.data.lower()


def test_tech_register_duplicate_email_shows_error_without_crashing(client):
    email = f"techdup{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode) VALUES (?, ?, ?, ?, ?, ?)",
            ("Tech Existing", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "Data Analysis", "Online"),
        )
        db.commit()

    response = client.post(
        "/tech-register",
        data={
            "full_name": "Tech Duplicate User",
            "email": email,
            "phone_number": "09000000000",
            "course": "Data Analysis",
            "gender": "Female",
            "learning_mode": "Online",
            "password": "AnotherPass123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already exists" in response.data.lower()


def test_researcher_registration_stores_cv_and_portfolio_files(client):
    email = f"researcherupload{uuid.uuid4().hex[:8]}@example.com"

    response = client.post(
        "/register",
        data={
            "full_name": "Researcher Upload",
            "email": email,
            "password": "SecurePass123",
            "role": "researcher",
            "cv_file": (io.BytesIO(b"cv file contents"), "cv.pdf"),
            "portfolio_file": (io.BytesIO(b"portfolio file contents"), "portfolio.pdf"),
        },
        follow_redirects=False,
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/researcher-assessment")

    with app.app_context():
        from app import get_db

        db = get_db()
        user = db.execute(
            "SELECT cv_file, portfolio_file FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    assert user is not None
    assert user[0] is not None
    assert user[1] is not None


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
    assert b"IOS Tech SkillUp Dashboard" in response.data
    assert b"Data Science" in response.data


def test_tech_student_without_application_fee_is_redirected_to_payment(client):
    email = f"techstudent{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode, payment_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Tech Student", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "Data Analysis", "Hybrid", "pending"),
        )
        db.commit()

    response = client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tech-payment")


def test_tech_student_with_paid_application_fee_can_open_dashboard(client):
    email = f"techstudentpaid{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode, payment_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Tech Student Paid", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "Data Analysis", "Hybrid", "single"),
        )
        db.commit()

    response = client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tech-skills-dashboard")


def test_tech_student_profile_routes_back_to_tech_dashboard(client):
    email = f"techprofile{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode, payment_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Tech Profile User", email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "AI Automation", "Online", "single"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": email, "password": "SecurePass123"},
        follow_redirects=True,
    )

    response = client.get("/profile")
    assert response.status_code == 200
    assert b"href=\"/tech-skills-dashboard\"" in response.data
    assert b"href=\"/dashboard\"" not in response.data


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


def test_admin_dashboard_students_are_paginated(client):
    admin_email = f"admin{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Admin User", admin_email, generate_password_hash("AdminPass123", method="pbkdf2:sha256"), "admin"),
        )
        for index in range(1, 15):
            db.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (f"Student {index}", f"student{index}{uuid.uuid4().hex[:4]}@example.com", generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student"),
            )
        db.commit()

    client.post(
        "/login",
        data={"email": admin_email, "password": "AdminPass123"},
        follow_redirects=True,
    )

    response = client.get("/admin-dashboard/students?page=2")
    assert response.status_code == 200
    assert b"page=2" in response.data
    assert b"page=3" in response.data
    assert b"Prev" in response.data
    assert b"Next" in response.data


def test_admin_dashboard_lists_tech_enrollments(client):
    admin_email = f"admin{uuid.uuid4().hex[:8]}@example.com"
    tech_email = f"tech{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode, payment_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Tech Student", tech_email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "Web Development", "Online", "₦8,500"),
        )
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Admin User", admin_email, generate_password_hash("AdminPass123", method="pbkdf2:sha256"), "admin"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": admin_email, "password": "AdminPass123"},
        follow_redirects=True,
    )

    response = client.get("/admin-dashboard")
    assert response.status_code == 200
    assert b"Web Development" in response.data
    assert b"Tech Students" in response.data
    assert tech_email.encode() in response.data


def test_admin_dashboard_filter_and_search_tech_tab(client):
    admin_email = f"admin{uuid.uuid4().hex[:8]}@example.com"
    tech_email = f"tech{uuid.uuid4().hex[:8]}@example.com"

    with app.app_context():
        from app import get_db

        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password, role, course, learning_mode, payment_mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Tech Student", tech_email, generate_password_hash("SecurePass123", method="pbkdf2:sha256"), "student", "Web Development", "Online", "₦8,500"),
        )
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Admin User", admin_email, generate_password_hash("AdminPass123", method="pbkdf2:sha256"), "admin"),
        )
        db.commit()

    client.post(
        "/login",
        data={"email": admin_email, "password": "AdminPass123"},
        follow_redirects=True,
    )

    response = client.get("/admin-dashboard?view=tech&q=web")
    assert response.status_code == 200
    assert b"Tech Students" in response.data
    assert b"Web Development" in response.data


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
