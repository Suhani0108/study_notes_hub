#!/usr/bin/env bash
# Render runs this script on every deploy (the "Build Command").
# Stop at the first error, so a failed step fails the deploy.
set -o errexit

# 1. Install Python packages
pip install -r requirements.txt

# 2. Gather all static files (Bootstrap is on a CDN; this is our CSS + the admin's)
python manage.py collectstatic --no-input

# 3. Create/update the database tables
python manage.py migrate

# 4. Create an admin account from environment variables, if they're set.
#    (Render's free plan has no shell, so this is the easiest way.)
#    "|| true" means: if the user already exists, carry on instead of failing.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    python manage.py createsuperuser --no-input || true
fi
