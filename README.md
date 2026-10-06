# IOSInstitute

A registration and learning portal for students, clients, researchers, and administrators.

## Features
- Role-based registration for student, client, and researcher users
- Email confirmation after successful account creation
- SQLite-backed user storage with dashboard and profile flows
- Admin review dashboard for research requests

## Run locally

```bash
cd /Users/mac/Downloads/IOSWORK
/usr/bin/python3 app.py
```

Then open http://localhost:5000/register in your browser.

## Deploy on Render

1. Push this repository to GitHub.
2. Create a new Web Service on Render using this repository.
3. Set the build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Set the start command:
   ```bash
   gunicorn app:app
   ```
5. Add environment variables as needed, such as `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`.

## Verification

```bash
cd /Users/mac/Downloads/IOSWORK
TESTING=1 /usr/bin/python3 -m pytest -q
```
