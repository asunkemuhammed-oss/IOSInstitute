# IOS Research Management System

A Flask-based research and student management platform for the IOS Institute of Scholars. The app includes:

- public landing page
- sign up and login
- student request submission
- researcher dashboard
- admin overview dashboard
- message communication flow
- document upload support

## Tech stack

- Python 3
- Flask
- SQLite (local demo database)
- Gunicorn (for deployment)

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open:

- http://localhost:5000

## API examples

- Health check: GET /api/health
- Register: POST /api/auth/register
- Login: POST /api/auth/login
- Create request: POST /api/requests
- Request details: GET /api/requests/<id>/details
- Messages: GET/POST /api/messages
- Admin overview: GET /api/admin/overview

## Deploy to Render

1. Push this project to GitHub.
2. Create a new Web Service on Render.
3. Connect the repository.
4. Set the runtime to Python.
5. Use the default build command and the start command from the Render config or Procfile.

Recommended service config:

```bash
pip install -r requirements.txt
gunicorn app:app
```

## Environment variables

Create a `.env` file with:

```bash
SECRET_KEY=your-strong-secret-key
PORT=5000
```

## Notes

This app uses SQLite for local development. For a production multi-user deployment, move to PostgreSQL and add hashed passwords, session management, and a proper file storage layer.
