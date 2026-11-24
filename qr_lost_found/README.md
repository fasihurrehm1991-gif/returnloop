# ReturnLoop — QR Lost & Found Website

## Technology choices
- Python + Django backend
- HTML, CSS and JavaScript frontend
- SQLite for local development; PostgreSQL for production
- Django authentication and admin
- QR sticker generation and finder notifications

## Non-negotiable rules
1. One unique QR code per registered user, not per item.
2. Only administrators can generate, download, print, activate, deactivate or replace QR codes.
3. Never show a QR image, QR URL or downloadable QR file in the user dashboard.
4. Finders can submit a notification without registering.
5. Inactive QR codes cannot accept notifications.
6. Never reveal the owner's phone number or email to a finder.

## Run on Windows
1. Install Python 3.11 or newer and enable **Add Python to PATH**.
2. Extract this ZIP and open the `qr_lost_found` folder in VS Code.
3. Open Terminal in VS Code and run:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

4. Open http://127.0.0.1:8000/ for the website.
5. Open http://127.0.0.1:8000/admin/ for the administrator panel.

## Deploy on Render with a free domain
1. Push this project to GitHub.
2. In Render, choose **New > Blueprint** and select the repository.
3. Render will read `render.yaml`, create the web service and a free PostgreSQL database, and assign a free `*.onrender.com` address.
4. Set real SMTP values in the service Environment tab:
   - `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
   - `EMAIL_USE_TLS=True`
   - `DEFAULT_FROM_EMAIL`
5. After deployment, open the service shell and create the administrator:
   `python manage.py createsuperuser`

Render's free database/service limits can change. The free domain is HTTPS and is sufficient for testing.

## Production email and database
- Configure `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` in the hosting provider's secret environment settings to deliver password-reset and finder notification emails. For Gmail, use a Google App Password, not the normal account password.
- Without SMTP credentials, production does not send emails; the password-reset confirmation page explains this instead of claiming an email was sent.
- Vercel's `/tmp` SQLite database is temporary and can lose accounts between function instances or restarts. Configure a persistent PostgreSQL `DATABASE_URL` before using the site for real accounts.

## Tests
Run the backend tests with `python manage.py test`.
