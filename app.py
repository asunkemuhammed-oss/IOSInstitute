import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'ios.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ios-secret-key-change-me')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def sync_admin_metrics(conn=None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    user_total = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    researcher_total = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'researcher'").fetchone()['count']
    active = conn.execute("SELECT COUNT(*) as count FROM research_requests WHERE status IN ('submitted', 'active', 'review')").fetchone()['count']
    completed = conn.execute("SELECT COUNT(*) as count FROM research_requests WHERE status = 'completed'").fetchone()['count']
    request_total = conn.execute('SELECT COUNT(*) as count FROM research_requests').fetchone()['count']
    course_total = 24

    metrics = [
        ('users', str(user_total)),
        ('researchers', str(researcher_total)),
        ('active_projects', str(active)),
        ('completed_projects', str(completed)),
        ('request_count', str(request_total)),
        ('courses', str(course_total)),
        ('revenue', '₦*****'),
    ]

    for metric_name, metric_value in metrics:
        conn.execute(
            '''
            INSERT INTO admin_metrics (metric_name, metric_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(metric_name) DO UPDATE SET metric_value = excluded.metric_value, updated_at = CURRENT_TIMESTAMP
            ''',
            (metric_name, metric_value)
        )

    conn.commit()
    if close_conn:
        conn.close()


def init_db():
    conn = get_db_connection()
    conn.execute('''
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
    ''')

    conn.execute('''
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
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            uploaded_by INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS admin_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT UNIQUE NOT NULL,
            metric_value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES ('IOS Admin', 'admin@iosresearch.org', 'admin123', 'admin')")
    conn.execute("INSERT OR IGNORE INTO users (name, email, password, role) VALUES ('Dr. Aisha Bello', 'researcher@iosresearch.org', 'research123', 'researcher')")

    conn.execute("INSERT OR IGNORE INTO admin_metrics (metric_name, metric_value) VALUES ('users', '1245')")
    conn.execute("INSERT OR IGNORE INTO admin_metrics (metric_name, metric_value) VALUES ('researchers', '38')")
    conn.execute("INSERT OR IGNORE INTO admin_metrics (metric_name, metric_value) VALUES ('active_projects', '76')")
    conn.execute("INSERT OR IGNORE INTO admin_metrics (metric_name, metric_value) VALUES ('completed_projects', '412')")
    conn.execute("INSERT OR IGNORE INTO admin_metrics (metric_name, metric_value) VALUES ('courses', '24')")
    conn.execute("INSERT OR IGNORE INTO admin_metrics (metric_name, metric_value) VALUES ('revenue', '₦*****')")

    sync_admin_metrics(conn)
    conn.commit()
    conn.close()


init_db()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "service": "IOS Research Management System"})


@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    role = data.get('role') or 'student'

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400

    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
            (name, email, password, role)
        )
        conn.commit()
        user_id = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()['id']
    except sqlite3.IntegrityError:
        return jsonify({"error": "This email is already registered."}), 409
    finally:
        conn.close()

    return jsonify({"message": "User registered successfully.", "user_id": user_id, "role": role})


@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    conn = get_db_connection()
    user = conn.execute(
        'SELECT id, name, email, role FROM users WHERE email = ? AND password = ?',
        (email, password)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    return jsonify({
        "message": "Login successful.",
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "role": user['role']
        }
    })


@app.route('/api/requests', methods=['GET', 'POST'])
def handle_requests():
    if request.method == 'GET':
        conn = get_db_connection()
        rows = conn.execute('''
            SELECT r.*, u.name as user_name
            FROM research_requests r
            JOIN users u ON u.id = r.user_id
            ORDER BY r.created_at DESC
        ''').fetchall()
        conn.close()
        return jsonify({"requests": [dict(row) for row in rows]})

    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    research_type = (data.get('research_type') or '').strip()
    topic = (data.get('topic') or '').strip()
    institution = (data.get('institution') or '').strip()
    department = (data.get('department') or '').strip()
    deadline = (data.get('deadline') or '').strip()
    assistance_needed = (data.get('assistance_needed') or '').strip()

    if not user_id or not research_type or not topic:
        return jsonify({"error": "User ID, research type and topic are required."}), 400

    conn = get_db_connection()
    now = datetime.utcnow().isoformat()
    cursor = conn.execute(
        '''
        INSERT INTO research_requests (
            user_id, research_type, topic, institution, department,
            deadline, assistance_needed, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', ?, ?)
        ''',
        (user_id, research_type, topic, institution, department, deadline, assistance_needed, now, now)
    )
    conn.commit()
    request_id = cursor.lastrowid
    sync_admin_metrics(conn)
    conn.close()

    return jsonify({
        "message": "Request submitted to IOS Research Management System.",
        "request_id": request_id,
        "status": "submitted"
    })


@app.route('/api/requests/<int:request_id>/status', methods=['PATCH'])
def update_request_status(request_id):
    data = request.get_json(silent=True) or {}
    status = (data.get('status') or '').strip()
    assigned_researcher_id = data.get('assigned_researcher_id')

    if not status:
        return jsonify({"error": "Status is required."}), 400

    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM research_requests WHERE id = ?', (request_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Request not found."}), 404

    conn.execute(
        '''
        UPDATE research_requests
        SET status = ?, assigned_researcher_id = COALESCE(?, assigned_researcher_id), updated_at = ?
        WHERE id = ?
        ''',
        (status, assigned_researcher_id, datetime.utcnow().isoformat(), request_id)
    )
    conn.commit()
    sync_admin_metrics(conn)
    record = conn.execute('SELECT * FROM research_requests WHERE id = ?', (request_id,)).fetchone()
    conn.close()

    return jsonify({"message": "Request status updated.", "request": dict(record)})


@app.route('/api/messages', methods=['GET', 'POST'])
def handle_messages():
    if request.method == 'GET':
        request_id = request.args.get('request_id')
        if not request_id:
            return jsonify({"error": "request_id is required."}), 400
        conn = get_db_connection()
        rows = conn.execute(
            '''
            SELECT m.*, u.name as sender_name
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.request_id = ?
            ORDER BY m.created_at ASC
            ''',
            (request_id,)
        ).fetchall()
        conn.close()
        return jsonify({"messages": [dict(row) for row in rows]})

    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    message = (data.get('message') or '').strip()

    if not request_id or not sender_id or not message:
        return jsonify({"error": "request_id, sender_id and message are required."}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO messages (request_id, sender_id, receiver_id, message) VALUES (?, ?, ?, ?)',
        (request_id, sender_id, receiver_id, message)
    )
    conn.commit()
    message_id = cursor.lastrowid
    row = conn.execute('SELECT * FROM messages WHERE id = ?', (message_id,)).fetchone()
    conn.close()
    return jsonify({"message": "Message sent.", "data": dict(row)})


@app.route('/api/requests/<int:request_id>/details')
def request_details(request_id):
    conn = get_db_connection()
    request_row = conn.execute('''
        SELECT r.*, u.name as user_name
        FROM research_requests r
        JOIN users u ON u.id = r.user_id
        WHERE r.id = ?
    ''', (request_id,)).fetchone()

    if not request_row:
        conn.close()
        return jsonify({"error": "Request not found."}), 404

    message_rows = conn.execute('''
        SELECT m.*, u.name as sender_name
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE m.request_id = ?
        ORDER BY m.created_at ASC
    ''', (request_id,)).fetchall()

    document_rows = conn.execute('''
        SELECT d.*, u.name as uploaded_by_name
        FROM documents d
        JOIN users u ON u.id = d.uploaded_by
        WHERE d.request_id = ?
        ORDER BY d.uploaded_at DESC
    ''', (request_id,)).fetchall()
    conn.close()

    return jsonify({
        "request": dict(request_row),
        "messages": [dict(row) for row in message_rows],
        "documents": [dict(row) for row in document_rows],
    })


@app.route('/api/documents/upload', methods=['POST'])
def upload_documents():
    request_id = request.form.get('request_id')
    uploaded_by = request.form.get('uploaded_by')

    if not request_id or not uploaded_by:
        return jsonify({"error": "request_id and uploaded_by are required."}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "No files uploaded."}), 400

    saved = []
    conn = get_db_connection()
    for file in files:
        if file.filename == '':
            continue
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        cursor = conn.execute(
            'INSERT INTO documents (request_id, uploaded_by, file_name, file_path) VALUES (?, ?, ?, ?)',
            (request_id, uploaded_by, filename, file_path)
        )
        conn.commit()
        saved.append({
            "id": cursor.lastrowid,
            "file_name": filename,
            "file_path": file_path,
        })
    conn.close()

    return jsonify({"message": "Files uploaded successfully.", "files": saved})


@app.route('/api/researchers')
def researcher_list():
    conn = get_db_connection()
    rows = conn.execute("SELECT id, name, email, role FROM users WHERE role = 'researcher' ORDER BY name").fetchall()
    conn.close()
    return jsonify({"researchers": [dict(r) for r in rows]})


@app.route('/api/admin/overview')
def admin_overview():
    conn = get_db_connection()
    metrics = {}
    for row in conn.execute('SELECT metric_name, metric_value FROM admin_metrics'):
        metrics[row['metric_name']] = row['metric_value']

    request_count = conn.execute('SELECT COUNT(*) as count FROM research_requests').fetchone()['count']
    users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    researchers = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'researcher'").fetchone()['count']
    active = conn.execute("SELECT COUNT(*) as count FROM research_requests WHERE status IN ('submitted', 'active', 'review')").fetchone()['count']
    completed = conn.execute("SELECT COUNT(*) as count FROM research_requests WHERE status = 'completed'").fetchone()['count']
    conn.close()

    return jsonify({
        "users": str(metrics.get('users', users)),
        "researchers": str(metrics.get('researchers', researchers)),
        "active_projects": str(metrics.get('active_projects', active)),
        "completed_projects": str(metrics.get('completed_projects', completed)),
        "courses": str(metrics.get('courses', '24')),
        "revenue": metrics.get('revenue', '₦*****'),
        "request_count": request_count,
        "status": "ok"
    })


@app.route('/api/admin/users')
def admin_users():
    conn = get_db_connection()
    rows = conn.execute('SELECT id, name, email, role, institution, department FROM users ORDER BY created_at DESC LIMIT 10').fetchall()
    conn.close()
    return jsonify({"users": [dict(row) for row in rows]})


@app.route('/api/admin/requests')
def admin_requests():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT r.id, r.topic, r.status, r.research_type, r.deadline, r.user_id, u.name as user_name
        FROM research_requests r
        JOIN users u ON u.id = r.user_id
        ORDER BY r.created_at DESC
        LIMIT 8
    ''').fetchall()
    conn.close()
    return jsonify({"requests": [dict(row) for row in rows]})


@app.route('/api/student/dashboard/<int:user_id>')
def student_dashboard(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT id, name, email, role FROM users WHERE id = ?', (user_id,)).fetchone()
    requests = conn.execute(
        'SELECT id, research_type, topic, status, deadline FROM research_requests WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    messages = conn.execute(
        'SELECT COUNT(*) as count FROM messages WHERE request_id IN (SELECT id FROM research_requests WHERE user_id = ?) OR sender_id = ?',
        (user_id, user_id)
    ).fetchone()['count']
    conn.close()

    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "user": dict(user),
        "requests": [dict(r) for r in requests],
        "summary": {
            "active_requests": len([r for r in requests if r['status'] in ('submitted', 'active', 'review')]),
            "progress": 72 if requests else 0,
            "resources": 12,
            "messages": messages,
        }
    })


@app.route('/api/researcher/dashboard/<int:user_id>')
def researcher_dashboard(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT id, name, email, role FROM users WHERE id = ?', (user_id,)).fetchone()
    assigned = conn.execute(
        '''
        SELECT r.*, u.name as user_name
        FROM research_requests r
        JOIN users u ON u.id = r.user_id
        WHERE r.assigned_researcher_id = ? OR r.user_id = ?
        ORDER BY r.created_at DESC
        ''',
        (user_id, user_id)
    ).fetchall()
    conn.close()

    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "user": dict(user),
        "requests": [dict(r) for r in assigned],
        "summary": {
            "assigned": len(assigned),
            "active": len([r for r in assigned if r['status'] in ('submitted', 'active', 'review')]),
            "completed": len([r for r in assigned if r['status'] == 'completed'])
        }
    })


@app.route('/api/dashboard/<int:user_id>')
def role_dashboard(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT id, name, email, role FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "User not found."}), 404

    role = user['role']
    if role == 'admin':
        overview = admin_overview()
        conn.close()
        return overview

    if role == 'researcher':
        data = researcher_dashboard(user_id)
        conn.close()
        return data

    data = student_dashboard(user_id)
    conn.close()
    return data


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
