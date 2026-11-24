# ReturnLoop — QR Lost & Found Website

## Technology choices
- Python + Django backend
- HTML, CSS and JavaScript frontend
- SQLite for local development; PostgreSQL for production
- Django authentication and admin
- QR sticker generation and finder notifications

## Non-negotiable rules
1. At most one unique QR code per registered user, not per item.
2. Only administrators can generate, download, print, activate, deactivate or replace QR codes.
3. Never show a QR image, QR URL or downloadable QR file in the user dashboard.
4. Finders can submit a notification without registering.
5. Inactive QR codes cannot accept notifications.
6. Never reveal the owner's phone number or email to a finder.

## Proposal workflows and current limits
- Registration records whether the member is a student or staff member, their institution, and an optional student/staff ID. Registration is immediately usable; QR issuance remains administrator-controlled.
- An administrator issues the QR from a sticker order. The intended order path is Pending → Generated → Paid → Delivered → Active. Payment is manually confirmed; the admin must record the agreed order amount before marking it paid.
- Account pages do not expose QR tokens or images. Administrators can replace a QR, which invalidates the previous token and leaves the new code inactive until it is ready.
- About and Pricing are public; Member Support requires login. Support requests appear in the admin inbox.
- Pricing has intentionally not been invented: all sticker packages show “Price soon” until the owner sets rates. Placing an order is a request, not a charge.
- Finder submissions use a honeypot and a database-backed limit of five messages per QR code per ten minutes. Repeated scans from one browser session are recorded no more than once per ten minutes.
- Email alerts work when SMTP is configured. SMS, SMS credits, and online payment processing are not integrated; do not advertise them as available. SMS remains a planned feature pending provider and package decisions.
- The admin homepage shows account, order, QR, finder-message, scan, support, and recorded paid-sales totals. Sales only include paid orders with an amount entered by an administrator.

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
- Configure `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in the hosting provider's secret environment settings to deliver password-reset and finder notification emails. For Gmail, use a Google App Password, not the normal account password. When both credentials are set, Django selects SMTP automatically; `DEFAULT_FROM_EMAIL` defaults to `EMAIL_HOST_USER` and can be overridden if that sender is verified.
- Without SMTP credentials, production does not send emails; the password-reset confirmation page explains this instead of claiming an email was sent.
- Vercel's `/tmp` SQLite database is temporary and can lose accounts between function instances or restarts. Configure a persistent PostgreSQL `DATABASE_URL` before using the site for real accounts.

## Tests
Run the backend tests with `python manage.py test`.
