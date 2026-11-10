"""Teacher Credential Score (TCS), 0-100.

    50  University ranking   from the best signed degree's university (NIRF rank)
    25  Degree level         PhD 25 / Master 20 / Bachelor 15 ...
    15  Certifications       CTET or NET 15 / TEFL 5   (admin-verified certificates only)
    10  Experience           1 point per year, up to 10 (self-declared on the profile)

Integrity rule: degree points count only degrees **signed by their university**, and certification
points only admin-verified certificates. Otherwise anyone could claim a famous university for 50 free points.
The university and level points come from the *same* degree (the one with the highest combined points),
so a PhD cannot borrow the ranking of an unrelated bachelor's.

`recalculate_merit(teacher)` is the single entry point. It is triggered from accounts/signals.py after the
database transaction commits. To move it to Celery/RQ later, wrap `schedule_recalculation` only.
"""
import re

from django.db import transaction

from .models import (
    Certification, Qualification, TeacherMeritScore, TeacherProfile, VerificationStatus,
)

# ---------------------------------------------------------------------------- scoring tables
UNIVERSITY_MAX, DEGREE_MAX, CERT_MAX, EXPERIENCE_MAX = 50, 25, 15, 10

# (highest rank included, points). Ranked but beyond the table = 10, unranked = 5.
NIRF_POINTS = [(10, 50), (50, 40), (100, 30), (200, 20)]
NIRF_BEYOND, NIRF_UNRANKED = 10, 5

LEVEL_POINTS = {
    "phd": 25, "masters": 20, "mphil": 20, "bachelors": 15, "integrated": 15,
    "pg_diploma": 10, "diploma": 5,
}
LEVEL_LABEL = {
    "phd": "PhD", "masters": "Master's degree", "mphil": "M.Phil.", "bachelors": "Bachelor's degree",
    "integrated": "Integrated degree", "pg_diploma": "PG Diploma", "diploma": "Diploma",
}

CERT_POINTS = {"ctet": 15, "net": 15, "ugc net": 15, "tefl": 5, "tesol": 5}

# (minimum score, key, label). Highest first.
TIERS = [
    (90, "laureate", "Aeterna Laureate"),
    (80, "distinguished", "Distinguished Scholar"),
    (70, "fellow", "Merit Fellow"),
    (60, "associate", "Associate Educator"),
    (0, "emerging", "Emerging Educator"),
]
TIER_ORDER = [t[1] for t in reversed(TIERS)]  # emerging ... laureate
TIER_DESCRIPTOR = {
    "laureate": "Elite-tier educator",
    "distinguished": "Distinguished educator",
    "fellow": "Proven, credentialed educator",
    "associate": "Verified educator",
    "emerging": "Rising educator",
}


# ---------------------------------------------------------------------------- pure helpers
def university_points(nirf_rank):
    if not nirf_rank:
        return NIRF_UNRANKED
    for limit, pts in NIRF_POINTS:
        if nirf_rank <= limit:
            return pts
    return NIRF_BEYOND


def level_points(level):
    return LEVEL_POINTS.get(level, 0)


def cert_points(name):
    return CERT_POINTS.get(re.sub(r"[^a-z ]", "", (name or "").lower().replace("-", " ")).strip(), 0)


def experience_points(years):
    return max(0, min(int(years or 0), EXPERIENCE_MAX))


def tier_for(score):
    for floor, key, name in TIERS:
        if score >= floor:
            return key, name


def _degree_total(q):
    return university_points(q.university.nirf_rank) + level_points(q.level)


def best_degree(quals):
    """The degree with the highest combined university + level points (ties: higher level)."""
    return max(quals, key=lambda q: (_degree_total(q), level_points(q.level)), default=None)


def _verified_degrees(teacher):
    return [
        q for q in teacher.qualifications.select_related("university")
        if q.cryptographically_verified and q.university.is_trusted_issuer
    ]


def _verified_cert_points(teacher):
    return max(
        (cert_points(c.name) for c in teacher.certifications.filter(verification_status=VerificationStatus.VERIFIED)),
        default=0,
    )


# ---------------------------------------------------------------------------- headline
def build_headline(tier_key, tier_name, degree):
    lead = f"{tier_name} — {TIER_DESCRIPTOR[tier_key]}."
    if not degree:
        return f"{lead} Credentials awaiting university verification."
    level = LEVEL_LABEL.get(degree.level, degree.course)
    uni = degree.university
    where = f"NIRF Rank #{uni.nirf_rank} University" if uni.nirf_rank else uni.name
    return f"{lead} {level} from {where}."


# ---------------------------------------------------------------------------- main calculation
def compute(teacher):
    """Return a dict with score, tier, headline and breakdown. Pure read, no writes."""
    degree = best_degree(_verified_degrees(teacher))
    parts = {
        "university": university_points(degree.university.nirf_rank) if degree else 0,
        "degree": level_points(degree.level) if degree else 0,
        "certification": _verified_cert_points(teacher),
        "experience": experience_points(teacher.total_experience_years),
    }
    score = min(100, sum(parts.values()))
    key, name = tier_for(score)
    return {"score": score, "tier": key, "tier_name": name, "breakdown": parts, "headline": build_headline(key, name, degree)}


def recalculate_merit(teacher):
    """Recompute and store the teacher's score. Notifies the teacher when their tier goes up."""
    from .notifications import notify_tier_up

    data = compute(teacher)
    with transaction.atomic():
        obj, created = TeacherMeritScore.objects.select_for_update().get_or_create(teacher=teacher)
        old_tier = None if created else obj.tier
        obj.score, obj.tier = data["score"], data["tier"]
        obj.headline, obj.breakdown = data["headline"], data["breakdown"]
        obj.save()
    if old_tier and TIER_ORDER.index(obj.tier) > TIER_ORDER.index(old_tier):
        notify_tier_up(teacher, data["tier_name"], data["score"])
    return obj


def schedule_recalculation(teacher_id):
    """Run after the surrounding transaction commits. Swap this body for a Celery `.delay()` to go async."""
    def run():
        t = TeacherProfile.objects.filter(pk=teacher_id).first()
        if t:
            recalculate_merit(t)
    transaction.on_commit(run)


# ---------------------------------------------------------------------------- progress / next steps
def next_tier_info(score):
    """{'next_tier', 'next_tier_name', 'next_threshold', 'points_needed'} or None at the top tier."""
    for floor, key, name in reversed(TIERS):  # ascending
        if floor > score:
            return {"next_tier": key, "next_tier_name": name, "next_threshold": floor, "points_needed": floor - score}
    return None


def next_steps(teacher, breakdown):
    """Concrete actions that would add points, biggest first. Each: {'action', 'points'}."""
    steps = []
    quals = list(teacher.qualifications.select_related("university"))
    verified = [q for q in quals if q.cryptographically_verified and q.university.is_trusted_issuer]
    current = _degree_total(best_degree(verified)) if verified else 0

    pending = [q for q in quals if q not in verified and q.verification_status != VerificationStatus.REJECTED]
    top_pending = best_degree(pending)
    if top_pending and _degree_total(top_pending) > current:
        steps.append({
            "action": f"Get your {top_pending.course} signed by {top_pending.university.name}",
            "points": _degree_total(top_pending) - current,
        })
    if not quals:
        steps.append({"action": "Add your highest degree and upload its documents", "points": 20})
    elif verified and max(level_points(q.level) for q in verified) < DEGREE_MAX:
        gap = DEGREE_MAX - max(level_points(q.level) for q in verified)
        steps.append({"action": "Add and verify a higher degree (e.g. a PhD)", "points": gap})

    cur_cert = breakdown.get("certification", 0)
    if cur_cert < CERT_MAX:
        pending_certs = [c for c in teacher.certifications.exclude(verification_status=VerificationStatus.VERIFIED)]
        gain = max((cert_points(c.name) for c in pending_certs), default=0) - cur_cert
        if gain > 0:
            steps.append({"action": "Get your pending certification verified", "points": gain})
        elif not pending_certs:
            steps.append({"action": "Add and verify a CTET or NET certificate", "points": CERT_MAX - cur_cert})

    exp = breakdown.get("experience", 0)
    if exp < EXPERIENCE_MAX:
        steps.append({"action": "Keep your total experience up to date (+1 per year, up to 10)", "points": EXPERIENCE_MAX - exp})

    return sorted(steps, key=lambda s: -s["points"])
