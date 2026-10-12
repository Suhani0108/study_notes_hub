# 📚 Study Notes Hub

A web app for students to organise study notes by subject. Write notes, attach lecture PDFs, and find anything quickly with search and filters. Every user has a private space: you can only ever see and edit your own subjects, notes and files.

![Dashboard](docs/dashboard.png)

---

## Features

- **Accounts:** sign up, log in and log out using Django's built-in authentication
- **Subjects:** create, view, edit and delete subjects to group your notes
- **Notes:** full create/read/update/delete, with optional text content and an optional PDF attachment
- **PDF uploads:**
  - Only real PDFs up to 10 MB are accepted (checks the size, the extension *and* the file contents)
  - PDFs display inline on the note page
  - Replaced or deleted PDFs are removed from disk automatically
- **Privacy by design:**
  - Every query is limited to the logged-in user, so other users' pages return 404
  - PDFs are served through a permission-checked view, not a public URL
- **Search and filter:** search notes by title and content, filter by subject, 10 notes per page
- **Dashboard:** subject and note counts, recent notes, quick search
- **Clean, responsive UI:** Bootstrap 5 with automatic dark mode and a manual light/dark toggle
- **Safe deletes:** a confirmation page that warns what else will be removed
- **Tested:** 51 automated tests covering permissions, CRUD, uploads, search and auth

## Tech stack

| Area | Tools |
|---|---|
| Backend | Python 3.12, Django 5.2 (class-based views, ModelForms, signals) |
| Database | SQLite (local), PostgreSQL (production) |
| Frontend | Django templates, Bootstrap 5.3, Bootstrap Icons |
| Production | Gunicorn, WhiteNoise, dj-database-url, Render |
| Config | python-dotenv, environment variables |

## Screenshots

**Search notes by title and content, combined with a subject filter**

![Notes search](docs/notes.png)

**Subjects, each with its own note count**

![Subjects](docs/subjects.png)

**Responsive on phones, with automatic dark mode**

![Mobile and dark mode](docs/mobile.png)

## Running it locally

**Requirements:** Python 3.10+ (3.12 recommended) and git.

```bash
# 1. Get the code
git clone https://github.com/Suhani0108/study_notes_hub.git
cd study_notes_hub

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file and add a secret key
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
#    → paste the output as SECRET_KEY in .env

# 5. Set up the database and an admin account
python manage.py migrate
python manage.py createsuperuser

# 6. Start the server
python manage.py runserver
```

Open http://127.0.0.1:8000. The admin site is at http://127.0.0.1:8000/admin/.

### Running the tests

```bash
python manage.py test
```

## Environment variables

| Variable | Required | Example | Purpose |
|---|---|---|---|
| `SECRET_KEY` | ✅ | `a-long-random-string` | Django's cryptographic key |
| `DEBUG` | | `True` locally, `False` in production | Shows detailed error pages |
| `ALLOWED_HOSTS` | | `localhost,127.0.0.1` | Domains the site can be served from |
| `DATABASE_URL` | | `postgresql://user:pass@host/db` | Uses SQLite if not set |
| `CSRF_TRUSTED_ORIGINS` | | `https://notes.example.com` | Only needed for a custom domain |
| `MEDIA_ROOT` | | `/var/data/media` | Where uploaded PDFs are stored |

On Render, the app's own `.onrender.com` address is added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically.

## Deployment (Render)

The repo is ready for [Render](https://render.com):

- **Build command:** `./build.sh`. It installs packages, collects static files, runs migrations and optionally creates an admin user.
- **Start command:** `gunicorn study_notes_hub.wsgi`
- **Database:** a Render PostgreSQL instance, connected through `DATABASE_URL`

> **Uploaded files:** Render's filesystem is wiped on every deploy and restart. To keep PDFs, attach a Render Persistent Disk and set `MEDIA_ROOT` to a folder on it, or move uploads to cloud storage such as S3.

## Project structure

```
study_notes_hub/   Project settings and root URLs
accounts/          Sign-up view and login/signup forms
notes/             Models, views, forms, signals, tests and templates for subjects and notes
templates/         Base layout, auth pages and reusable partials
static/css/        Custom styles on top of Bootstrap
docs/              README screenshots
build.sh           Render build script
```
