"""In-app notifications (the bell dropdown). Email notices for job applications live in jobs/notifications.py."""
from .models import Notification


def _create(user, kind, title, body="", link=""):
    if user is None:
        return None
    return Notification.objects.create(recipient=user, kind=kind, title=title[:160], body=body[:300], link=link)


def notify_degree_request(q):
    """A teacher named this university on a degree: tell the university it has a request waiting."""
    teacher = q.teacher.full_name
    return _create(
        q.university.user, Notification.Kind.DEGREE_REQUEST,
        "New degree verification request",
        f"{teacher} has asked you to verify {q.course} ({q.year_of_passing}).",
        "/university",
    )


def notify_degree_signed(q):
    return _create(
        q.teacher.user, Notification.Kind.DEGREE_SIGNED,
        "Your degree is now cryptographically verified",
        f"{q.university.name} signed your {q.course}. Your merit score has been updated.",
        "/profile",
    )


def notify_degree_rejected(q):
    return _create(
        q.teacher.user, Notification.Kind.DEGREE_REJECTED,
        "A degree could not be verified",
        f"{q.university.name} could not verify your {q.course}. Check the details and documents, then save again.",
        "/profile",
    )


def notify_tier_up(teacher, tier_name, score):
    return _create(
        teacher.user, Notification.Kind.TIER_UP,
        f"You reached {tier_name}",
        f"Your merit score is now {score}/100.",
        "/profile",
    )
