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
| PATCH | `/api/applications/{id}/` `{status}` | institute (ATS status; emails the teacher on key changes) |
| GET | `/api/applications/?job=&ordering=-match_score` | sort applicants by match score (or `applied_at`) |
| GET | `/api/institute/analytics/` | institute: active jobs, total applications, breakdown by status, per-job table |

## Phase 2 (implemented)
- **Matching** (`jobs/matching.py`): 0-100 score on apply = subject 40 + experience 25 + location 20 + salary 15.
  Missing data scores neutral, not zero. The per-factor explanation is stored in `JobApplication.match_breakdown`
  and shown to institutes only; teachers see the overall score.
- **Notifications** (`jobs/notifications.py`): emails the teacher on shortlisted / interview / offered / hired / rejected.
  Console backend by default; set `EMAIL_BACKEND` + `EMAIL_*` for SMTP. `viewed` and `bookmarked` never email.
- **Analytics**: `GET /api/institute/analytics/` and the Analytics tab on the institute dashboard.
- **Document auto-fill**: on apply, the teacher's degrees/mark sheets and certificates that have an uploaded file are
  linked to the application (`attached_qualifications`, `attached_certifications`).
- Existing Phase 1 applications: `python manage.py backfill_phase2`
- Tests: `python manage.py test jobs`

## Still to do
Blockchain certificate verification, OTP verification for email/phone/WhatsApp, secure non-downloadable intro video,
messaging, interview scheduler, micro-courses, mentorship, gig hub, landing-page carousels/stats, Boolean search.
