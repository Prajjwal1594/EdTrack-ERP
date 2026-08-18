# El'Wood International University — Student Progress Tracker

A comprehensive full-stack web application for managing student grades, attendance, assignments, exams, messaging, fee management, and grade sheet generation.

---

## Features

| Module | Capabilities |
|---|---|
| **Multi-role Auth** | Admin, Faculty, Student, Parent — each with role-based dashboards |
| **Grade Management** | Percentage-based (0–100%) grading per subject/term, auto letter grades, trend charts |
| **Attendance** | Daily attendance per section (present/absent/late/excused), monthly views |
| **Assignments** | Faculty create assignments; students submit online; faculty grade with feedback |
| **Online Exams** | MCQ, True/False, and Short Answer — auto-graded with countdown timer |
| **Grade Sheets** | PDF + HTML grade sheets with grades, attendance, and faculty comments per term |
| **Digital Wallet** | Razorpay-powered parent wallet for micro-fee deductions and instant top-ups |
| **Early Warning** | Predictive algorithm identifying at-risk students based on attendance/grades |
| **Micro-Credentials** | Issue digital PDF certificates for soft skills and extracurricular achievements |
| **Fee Management** | Track fee types, payment records, and download official PDF receipts |
| **In-App Messaging** | Thread-based messaging between all user roles |
| **AI Assistant** | **Google Gemini** integration for personalized academic/holistic insights |
| **Timetable Mgmt** | Schedule subjects, sections, and faculty with weekly views and collision detection |
| **Admin Panel** | Manage users, semesters, sections, subjects, faculty assignments, academic terms |
| **Analytical Dashboards** | Rich Chart.js visualizations for Admin, Faculty, and Parent roles |
| **Parent Portal** | View all linked children's progress, grades, attendance, fees, and wallet |
| **Multi-college** | Full multi-tenant support via `College` model |
| **Mobile Responsive** | Works on phones and tablets |

---

## Quick Start (Local)

### 1. Clone / extract the project

```bash
cd elwood
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **PDF generation** requires WeasyPrint system libraries. On Ubuntu/Debian:
> ```bash
> sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0
> ```
> On macOS: `brew install pango`

### 4. Configure environment (optional)

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

```ini
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///elwood.db          # local
# DATABASE_URL=postgresql://...           # cloud/production

# Email (SMTP) — required for notifications & digests
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-app-password

# Razorpay (Required for Digital Wallet)
RAZORPAY_KEY_ID=rzp_test_xxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxx
```

### 5. Seed the database with demo data

```bash
python3 seed.py
```

### 6. Run the development server

```bash
python3 run.py
```

Visit **http://localhost:5000**

---

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@gmail.com | admin123 |
| Faculty | faculty@gmail.com | faculty123 |
| Student | student@gmail.com | student123 |
| Parent | parent@gmail.com | parent123 |

---

## Project Structure

```
elwood/
├── run.py                  # Flask entry point
├── seed.py                 # Database seeder with demo data
├── config.py               # App configuration
├── requirements.txt
├── app/
│   ├── __init__.py         # App factory
│   ├── models.py           # All SQLAlchemy models
│   ├── auth/               # Login / logout / profile
│   ├── admin/              # Admin panel (users, semesters, terms…)
│   ├── faculty/            # Grades, attendance, assignments, comments
│   ├── student/            # Student portal
│   ├── parent/             # Parent portal
│   ├── reports/            # Grade sheet generation (HTML + PDF)
│   ├── exams/              # Online exam builder and test-taker
│   ├── messages/           # In-app messaging
│   ├── fees/               # Fee tracking & Digital Wallet (Razorpay)
│   └── utils/
│       └── algorithms.py   # Early Warning & Weekly Digest logic
├── templates/
│   ├── base.html           # Shared layout (sidebar, topbar, design system)
│   └── ...                 # Per-blueprint templates
└── static/
    └── ...                 # CSS / JS (served by Flask)
```

---

## Cloud Deployment

### PostgreSQL (production)

Set `DATABASE_URL` to your PostgreSQL connection string:

```
DATABASE_URL=postgresql://user:password@host:5432/elwood_db
```

The app automatically uses PostgreSQL when this env var is set.

### Gunicorn (WSGI)

```bash
pip install gunicorn
gunicorn "app:create_app()" -w 4 -b 0.0.0.0:8000
```

### Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:create_app()", "-w", "4", "-b", "0.0.0.0:8000"]
```

---

## Multi-College / Multi-Tenant

Every record is scoped to a `College`. To add a second college:

1. Insert a new `College` row with a unique `code`
2. Create users with `college_id` pointing to the new college
3. Each college's data is fully isolated

---

## Grading Scale

| Score | Letter |
|---|---|
| 90–100% | A+ |
| 80–89% | A |
| 70–79% | B+ |
| 60–69% | B |
| 50–59% | C |
| 40–49% | D |
| < 40% | F |

Low-grade threshold (default 40%) triggers automatic student notifications. Configurable in `config.py`.

---

## LMS Integration

The architecture is LMS-ready. To integrate with an external LMS (Moodle, Canvas, Google Semesterroom):

1. Add an `/api/` blueprint with JWT auth
2. Expose `/api/students`, `/api/grades`, `/api/attendance` endpoints
3. Use the existing SQLAlchemy models — no schema changes needed

---

## Tech Stack

- **Backend**: Python 3.11, Flask 3.0
- **ORM**: Flask-SQLAlchemy (SQLite / PostgreSQL)
- **Payments**: Razorpay SDK
- **Auth**: Flask-Login
- **PDF**: WeasyPrint (Digital Receipts & Grade Sheets)
- **Charts**: Chart.js 4.4 (Radar, Bar, Line, Doughnut)
- **Email**: Flask-Mail (Background threading & Weekly Digest)
- **Frontend**: Server-rendered Jinja2, Vanilla JS
- **Fonts**: Playfair Display + DM Sans (Google Fonts)
- **Icons**: Font Awesome 6
