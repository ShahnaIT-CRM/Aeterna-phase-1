# Project Aeterna – Phase 1 MVP

Job board for educators. Monorepo: Django REST API + React (Vite, Tailwind) frontend.
In production, Django serves the built React app, so Railway runs a **single service** plus PostgreSQL.

```
aeterna/
├── Dockerfile            # multi-stage: builds React, then runs Django + gunicorn
├── railway.json
├── backend/
│   ├── manage.py, requirements.txt
│   ├── aeterna/          # settings, urls, wsgi
│   ├── accounts/         # User, TeacherProfile, Qualification, Certification, EmploymentHistory, InstituteProfile
│   └── jobs/             # JobPost, JobQuestion, JobApplication (+ matching.py / notifications.py Phase 2 stubs)
└── frontend/
    └── src/              # pages: AuthPage, TeacherProfile, JobFeed, MyApplications, InstituteDashboard
```

## Run locally
```bash
# Backend (terminal 1)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=1
python manage.py migrate
python manage.py createsuperuser      # for /admin (verify institutes & qualifications)
python manage.py runserver            # http://localhost:8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                           # http://localhost:5173 (proxies /api to :8000)
```

## Deploy to Railway
1. Push this repo to GitHub.
2. Railway → **New Project → Deploy from GitHub repo** (it detects `railway.json` and the Dockerfile).
3. In the project, **+ New → Database → PostgreSQL**.
4. Open your app service → **Variables** and add:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`   (reference variable)
   - `SECRET_KEY` = a long random string (`python -c "import secrets;print(secrets.token_urlsafe(50))"`)
5. Service → **Settings → Networking → Generate Domain**. `RAILWAY_PUBLIC_DOMAIN` is set automatically and used for CSRF.
6. **Uploads (photos, certificates):** Railway's disk is wiped on each deploy. Add a **Volume** to the app service mounted at `/data`, and set `MEDIA_ROOT=/data/media`. (Later, move to S3/R2 via django-storages.)
7. Create your admin user: Railway service shell → `python manage.py createsuperuser`, then visit `/admin/`.
   Set an institute's `verification_status` to *verified* there.

Migrations run automatically on every deploy.

## API summary
| Method | Path | Who |
|---|---|---|
| POST | `/api/auth/register/`, `/api/auth/login/`, `/api/auth/refresh/` | public |
| GET | `/api/auth/me/` | any |
| GET/PATCH | `/api/teacher/profile/` | teacher |
| CRUD | `/api/teacher/qualifications/`, `/employment/`, `/certifications/` | teacher |
| GET/PATCH | `/api/institute/profile/` | institute |
| GET | `/api/jobs/?q=&city=&employment_type=&work_mode=&max_experience=&page=` | teacher (open jobs) / institute (own jobs) |
| POST/PATCH/DELETE | `/api/jobs/` , `/api/jobs/{id}/` | institute |
| POST | `/api/jobs/{id}/apply/` | teacher |
| GET | `/api/applications/?job=` | teacher (own) / institute (received) |
| PATCH | `/api/applications/{id}/` `{status}` | institute (ATS status) |

## Deliberately left for Phase 2 (stubs in place)
AI matching & culture fit (`jobs/matching.py`, `JobApplication.match_score`), blockchain certificate
verification (`Qualification.blockchain_tx_hash`, `verification_status`), OTP verification for email/phone/WhatsApp,
status notifications (`jobs/notifications.py`), secure non-downloadable intro video, auto-attach documents on apply,
messaging, interview scheduler, micro-courses, mentorship, gig hub, landing-page carousels/stats, Boolean search.
