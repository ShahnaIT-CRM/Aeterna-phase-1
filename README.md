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
│   ├── accounts/         # User, TeacherProfile, Qualification, Certification, EmploymentHistory, InstituteProfile,
│   │                       # Phase 4: UniversityProfile, TeacherMeritScore, Notification (merit.py, signals.py)
│   ├── jobs/             # JobPost, JobQuestion, JobApplication, matching.py, notifications.py
│   ├── lms/              # Phase 3: Course, Lesson, Enrollment (micro-courses)
│   └── utils/            # Phase 4: crypto.py (Ed25519 signing, SHA-256, key encryption)
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

## Phase 3 (implemented)
- *(The mock blockchain anchoring that was here was replaced by real digital signatures in Phase 4, below.)*
- **Micro-courses** (`lms` app). Create courses and lessons in `/admin` (tick *Is published*), or run
  `python manage.py seed_lms` for samples. Teachers browse at **/courses**, enroll, open lessons and mark them
  complete; finishing every lesson completes the enrollment and earns the course's badge.
  Lesson content is only sent to enrolled teachers.
- **Interview scheduler.** `JobApplication.interview_date` + `interview_details`. Institutes use
  **Schedule interview** on an applicant (choosing "Interview scheduled" in the status menu opens it too).
  The teacher is emailed and sees it under **My applications → Upcoming interviews**.
- Tests: `python manage.py test` (accounts, jobs, lms)

| Method | Path | Who |
|---|---|---|
| GET | `/api/lms/courses/`, `/api/lms/courses/{id}/` | signed in (lesson content: enrolled teachers only) |
| POST | `/api/lms/courses/{id}/enroll/` | teacher |
| GET | `/api/lms/enrollments/` | teacher (own) |
| POST | `/api/lms/enrollments/{id}/complete-lesson/` `{lesson}` | teacher |
| POST | `/api/applications/{id}/schedule-interview/` `{interview_date, interview_details?}` | institute (calling again reschedules) |
| GET | `/api/applications/interviews/` | upcoming interviews (teacher: own, institute: theirs) |

Upgrading from Phase 2: `python manage.py migrate` (adds `accounts.0002`, `jobs.0003`, `lms.0001`).

## Phase 4 (implemented): PKI, universities, merit score, prestige profile
**Setup.** `pip install -r backend/requirements.txt`, set `PKI_MASTER_KEYS` (see `.env.example`; required when `DEBUG` is off),
then `python manage.py migrate` (`accounts.0003-0005`) and `python manage.py recalculate_merit`.

**Flow.** University registers (role `university`) → admin sets it to *verified* in `/admin` (this generates its Ed25519 key pair and
sets `is_trusted_issuer`) and fills in `nirf_rank` → it appears in the teacher's searchable dropdown → teacher saves a degree with
both documents (PDF/JPG/PNG, ≤ 5 MB, content-sniffed) → the university gets a bell notification and a *Pending request* →
reviews the PDF → **Issue & Sign**: SHA-256 of the certificate, then an Ed25519 signature over a canonical message
(`{qualification, teacher, university, course, level, year, sha256}`) → green *Cryptographically Verified* badge.
Editing any signed field, or replacing the certificate, withdraws the signature and re-sends the request.

**Keys.** Public key: stored plain and published by the verify endpoint. Private key: Fernet-encrypted under `PKI_MASTER_KEYS`
(rotate by putting the new key first), never serialized, hidden in admin. Server-custodied by design; the upgrade path is a KMS/HSM behind
`utils/crypto.sign_message`.

**Merit score (TCS, 0-100)** in `accounts/merit.py`: University 50 (NIRF ≤10: 50, ≤50: 40, ≤100: 30, ≤200: 20, ranked beyond: 10, unranked: 5),
Degree level 25 (PhD 25, Master/M.Phil 20, Bachelor/Integrated 15, PG Diploma 10, Diploma 5), Certification 15 (CTET/NET 15, TEFL/TESOL 5),
Experience 10 (1/yr, cap 10). Only **university-signed** degrees and **admin-verified** certificates count; university and level points
come from the same best degree. Tiers: 90+ Aeterna Laureate, 80+ Distinguished Scholar, 70+ Merit Fellow, 60+ Associate Educator, else Emerging Educator.
Recalculated after commit by signals (degree/certificate/experience/NIRF change); `schedule_recalculation` is the one place to swap in Celery.

| Method | Path | Who |
|---|---|---|
| GET | `/api/universities/?q=` | signed in: verified universities for the dropdown |
| GET/PATCH | `/api/university/profile/` | university |
| GET | `/api/university/requests/?status=pending\|signed\|rejected` | university (own degrees only) |
| GET | `/api/university/requests/{id}/document/{degree\|marksheet}/` | the named university (token-checked file) |
| POST | `/api/university/requests/{id}/sign/` · `/reject/` | verified university |
| GET | `/api/credentials/verify/{qualification_id}/` | signed-in, or anyone if the teacher's profile is public |
| GET | `/api/notifications/` · POST `/{id}/read/` · `/read-all/` | signed in (own) |
| GET | `/api/public/teachers/{id}/` | anyone, only if visibility is Public |
| GET | `/t/{id}` | public certificate page (server adds LinkedIn/Open Graph tags) |

Upgrade note: old free-text universities become *unverified, account-less* `UniversityProfile` rows (verify or merge them in `/admin`);
Phase 3 mock "blockchain" proofs are reset to *pending* because they carried no signature.

## Still to do
OTP verification for email/phone/WhatsApp, secure non-downloadable intro video,
messaging, mentorship, gig hub, peer circles, landing-page carousels/stats, Boolean search, calendar-tool integration,
showing earned course badges on teacher profiles.
