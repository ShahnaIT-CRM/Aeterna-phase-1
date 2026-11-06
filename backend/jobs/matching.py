"""AI-influenced matching engine (Phase 2).

Scores how well a teacher fits a job on a 0-100 scale using four weighted factors:

    subject     40   teacher subjects/skills  vs  job specialization/title/skills
    experience  25   total years of experience vs  job minimum experience
    location    20   city / state / relocation vs  job city, state, work mode
    salary      15   teacher expectation       vs  job salary range

Design notes
------------
* Deterministic and explainable on purpose: every factor returns a 0-1 value plus a
  human-readable reason, so an institute can see *why* a candidate scored 82.
* When one side hasn't provided the data needed to judge a factor (e.g. the teacher
  left salary blank), the factor gets a NEUTRAL value instead of 0 or 1. Missing data
  should neither reward nor punish a candidate.
* No external services and no ML dependency. The public API below is the seam where a
  learned model or an embedding-based subject matcher can be dropped in later without
  touching views or serializers.

Public API
----------
compute_match_breakdown(teacher, job) -> {"score": float, "factors": {...}}
compute_match_score(teacher, job)     -> float in [0, 100]
"""
import re

WEIGHTS = {"subject": 40, "experience": 25, "location": 20, "salary": 15}
NEUTRAL = 0.5  # used when a factor can't be judged because data is missing

# Words that describe the *role*, not the *subject*. Stripped before subject matching so
# "PGT Physics Teacher" and "Physics" compare as equal.
_ROLE_WORDS = {
    "pgt", "tgt", "prt", "teacher", "teachers", "faculty", "lecturer", "professor", "assistant",
    "associate", "senior", "junior", "guest", "visiting", "tutor", "instructor", "trainer",
    "head", "hod", "coordinator", "department", "of", "and", "the", "for", "in", "a", "an",
    "primary", "secondary", "class", "classes", "grade", "grades", "school", "college",
    "wanted", "required", "urgent", "full", "time", "part",
}

# Abbreviations / spellings common on Indian job boards. A value may expand to several words.
_SYNONYMS = {
    "maths": "mathematics", "math": "mathematics",
    "phy": "physics", "chem": "chemistry", "bio": "biology", "eng": "english",
    "cs": "computer science", "comp": "computer", "computers": "computer",
    "evs": "environmental studies", "sst": "social science",
    "eco": "economics", "econ": "economics",
    "accounts": "accountancy", "accounting": "accountancy",
    "pe": "physical education", "pt": "physical education",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_GRADE_RE = re.compile(r"^\d+(st|nd|rd|th)?$")  # "6", "10th" -> grade numbers, not subjects


def _tokens(text):
    """Content words of a string: lower-cased, synonyms expanded, role/grade words removed."""
    out = set()
    for raw in _TOKEN_RE.findall((text or "").lower()):
        for tok in _SYNONYMS.get(raw, raw).split():
            if tok not in _ROLE_WORDS and len(tok) > 1 and not _GRADE_RE.match(tok):
                out.add(tok)
    return out


def _phrase_tokens(items):
    """List of strings -> list of non-empty token sets (one per phrase)."""
    return [t for t in (_tokens(i) for i in (items or []) if isinstance(i, str)) if t]


def _norm(text):
    return (text or "").strip().lower()


def _num(value):
    return None if value is None else float(value)


# --------------------------------------------------------------------------------------
# Factor 1: subject
# --------------------------------------------------------------------------------------
def _subject_factor(teacher, job):
    # What the job is asking for. Specialization is the clearest signal; fall back to the
    # title ("PGT Physics") and then the department.
    target = _tokens(job.specialization) or _tokens(job.title) or _tokens(job.department)
    if not target:
        return NEUTRAL, "The job doesn't name a subject, so subject fit can't be judged."

    # What the teacher teaches: declared subjects plus subjects from past roles.
    subject_sets = _phrase_tokens(teacher.subjects)
    for role in teacher.employment.all():
        subject_sets += _phrase_tokens(role.subjects)
    if not subject_sets:
        return NEUTRAL, "The teacher hasn't listed any subjects."

    # Best single subject. Full coverage of the job's subject = 1.0; partial overlap scales
    # with how much of the job's subject is covered, nudged by how focused the teacher's is.
    best = 0.0
    for ts in subject_sets:
        overlap = len(ts & target)
        if not overlap:
            continue
        coverage = overlap / len(target)
        score = 1.0 if coverage == 1.0 else 0.75 * coverage + 0.25 * (overlap / len(ts))
        best = max(best, score)

    # Secondary signal: skills overlap (only when the job lists skills AND the teacher has some).
    job_skills = _phrase_tokens(job.skills)
    teacher_skill_tokens = set().union(*_phrase_tokens(teacher.skills)) if teacher.skills else set()
    extra = ""
    value = best
    if job_skills and teacher_skill_tokens:
        matched = sum(1 for js in job_skills if js & teacher_skill_tokens)
        value = 0.8 * best + 0.2 * (matched / len(job_skills))
        extra = f" Matches {matched} of {len(job_skills)} listed skills."

    if best >= 0.99:
        reason = "Teaches the subject this job needs."
    elif best > 0:
        reason = "Partly overlaps with the subject this job needs."
    else:
        reason = "None of the teacher's subjects match this job's subject."
    return value, reason + extra


# --------------------------------------------------------------------------------------
# Factor 2: experience
# --------------------------------------------------------------------------------------
def _experience_factor(teacher, job):
    need = job.min_experience_years or 0
    have = teacher.total_experience_years or 0
    if need == 0:
        return 1.0, "No minimum experience required."
    if have >= need:
        return 1.0, f"{have} years of experience meets the {need}-year minimum."
    # Linear shortfall: 4 of 5 years -> 0.8, half the requirement -> 0.5, none -> 0.
    return have / need, f"{have} years of experience; the job asks for at least {need}."


# --------------------------------------------------------------------------------------
# Factor 3: location
# --------------------------------------------------------------------------------------
def _location_factor(teacher, job):
    if job.work_mode == "remote":
        return 1.0, "Remote role, so location doesn't matter."

    job_city, job_state = _norm(job.city), _norm(job.state)
    t_city, t_state = _norm(teacher.city), _norm(teacher.state)
    if not job_city and not job_state:
        return NEUTRAL, "The job doesn't specify a location."
    if not t_city and not t_state:
        return NEUTRAL, "The teacher hasn't added their location."

    if job_city and job_city == t_city:
        return 1.0, f"Already based in {job.city}."

    preferred = {_norm(c) for c in (teacher.preferred_cities or []) if isinstance(c, str)}
    if (job_city and job_city in preferred) or (job_state and job_state in preferred):
        return 0.9, "The job is in one of the teacher's preferred locations."

    same_state = bool(job_state) and job_state == t_state
    if teacher.willing_to_relocate:
        return (0.7 if same_state else 0.6), "Willing to relocate."
    if same_state:
        return 0.4, f"In the same state ({job.state}) but a different city, and not willing to relocate."
    return 0.0, "In a different city and state, and not willing to relocate."


# --------------------------------------------------------------------------------------
# Factor 4: salary
# --------------------------------------------------------------------------------------
def _salary_factor(teacher, job):
    expected = _num(teacher.salary_expectation)
    lo, hi = _num(job.salary_min), _num(job.salary_max)
    if expected is None:
        return NEUTRAL, "The teacher hasn't set a salary expectation."
    if lo is None and hi is None:
        return NEUTRAL, "The job doesn't list a salary range."
    if hi is None or expected <= hi:
        return 1.0, "Salary expectation is within the job's range."

    # Expectation is above the top of the range. Negotiability softens the penalty.
    ceiling = hi * (1.10 if job.salary_negotiable else 1.0)
    if expected <= ceiling:
        return 0.85, "Slightly above the range, but the institute says salary is negotiable."
    over = (expected - ceiling) / ceiling
    slope = 2.0 if teacher.salary_negotiable else 3.0  # hits 0 at ~+50% / ~+33% over budget
    pct = round(100 * (expected - hi) / hi)
    return max(0.0, 1 - over * slope), f"Salary expectation is about {pct}% above the top of the range."


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
_FACTORS = {
    "subject": _subject_factor,
    "experience": _experience_factor,
    "location": _location_factor,
    "salary": _salary_factor,
}


def compute_match_breakdown(teacher, job):
    """Return the overall score and a per-factor explanation (JSON-serialisable)."""
    factors, total = {}, 0.0
    for name, fn in _FACTORS.items():
        value, reason = fn(teacher, job)
        value = min(1.0, max(0.0, value))
        points = WEIGHTS[name] * value
        total += points
        factors[name] = {
            "score": round(100 * value),   # how well this factor fits, 0-100
            "weight": WEIGHTS[name],
            "points": round(points, 1),    # contribution to the overall score
            "reason": reason,
        }
    return {"score": round(total, 1), "factors": factors}


def compute_match_score(teacher, job):
    """Overall 0-100 match score for `teacher` applying to `job`."""
    return compute_match_breakdown(teacher, job)["score"]
