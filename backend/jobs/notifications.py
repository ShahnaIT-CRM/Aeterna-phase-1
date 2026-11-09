"""Email notifications for ATS status changes (Phase 2).

Uses Django's email framework, so the transport is purely a settings concern. For now
settings.EMAIL_BACKEND defaults to the console backend: emails are printed to the server log.
Switch to SMTP in production by setting EMAIL_BACKEND and the EMAIL_* env vars.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Only candidate-facing milestones send email. "viewed" fires automatically when an institute
# opens a profile and "bookmarked" is an internal note, so neither notifies the teacher.
_TEMPLATES = {
    "shortlisted": (
        "You've been shortlisted for {job} at {institute}",
        "Good news! {institute} has shortlisted your application for {job}.\n"
        "They may contact you soon about the next steps.",
    ),
    "interview": (
        "Interview stage: {job} at {institute}",
        "{institute} has moved your application for {job} to the interview stage.\n"
        "Keep an eye on your email and phone for scheduling details.",
    ),
    "offered": (
        "You have an offer from {institute}",
        "Congratulations! {institute} has sent an offer for the {job} position.\n"
        "Please check with the institute for the offer letter and joining details.",
    ),
    "hired": (
        "Welcome aboard: {job} at {institute}",
        "Congratulations! {institute} has marked you as hired for {job}.",
    ),
    "rejected": (
        "Update on your application for {job}",
        "Thank you for applying for {job} at {institute}. After review, the institute has decided "
        "not to move forward with your application this time.\n"
        "We encourage you to keep exploring other open roles on Aeterna.",
    ),
}


def build_status_email(application):
    """Return (subject, body) for the application's current status, or None if no email applies."""
    template = _TEMPLATES.get(application.status)
    if not template:
        return None
    subject_t, body_t = template
    ctx = {"job": application.job.title, "institute": application.job.institute.name}
    link = f"{settings.SITE_URL.rstrip('/')}/applications"
    body = (
        f"Hi {application.teacher.first_name},\n\n{body_t.format(**ctx)}\n\n"
        f"Track your application: {link}\n\n- The Aeterna team"
    )
    return subject_t.format(**ctx), body


def _send(application_id):
    # Imported lazily: models import nothing from here, but this keeps module load order simple.
    from .models import JobApplication

    try:
        app = JobApplication.objects.select_related("job__institute", "teacher__user").get(pk=application_id)
        email = build_status_email(app)
        if email:
            send_mail(email[0], email[1], settings.DEFAULT_FROM_EMAIL, [app.teacher.user.email])
    except Exception:  # never let a mail problem surface as a failed status update
        logger.exception("Could not send status email for application %s", application_id)


def notify_status_change(application, old_status=None):
    """Email the teacher about a status change.

    Pass `old_status` so nothing is sent when the status didn't actually change. The email is
    sent after the surrounding transaction commits, and failures are logged, never raised.
    """
    if old_status is not None and old_status == application.status:
        return
    transaction.on_commit(lambda: _send(application.pk))


def build_interview_email(application, rescheduled=False):
    """(subject, body) for an interview invitation. The time is shown in the server timezone (IST)."""
    when = timezone.localtime(application.interview_date).strftime("%A, %d %B %Y at %I:%M %p %Z")
    job, inst = application.job.title, application.job.institute.name
    verb = "rescheduled" if rescheduled else "scheduled"
    lines = [
        f"Hi {application.teacher.first_name},",
        "",
        f"{inst} has {verb} your interview for {job}.",
        f"When: {when}",
    ]
    if application.interview_details:
        lines.append(f"Where / how: {application.interview_details}")
    lines += ["", f"See all your interviews: {settings.SITE_URL.rstrip('/')}/applications", "", "- The Aeterna team"]
    return f"Interview {verb}: {job} at {inst}", "\n".join(lines)


def _send_interview(application_id, rescheduled):
    from .models import JobApplication

    try:
        app = JobApplication.objects.select_related("job__institute", "teacher__user").get(pk=application_id)
        subject, body = build_interview_email(app, rescheduled)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [app.teacher.user.email])
    except Exception:
        logger.exception("Could not send interview email for application %s", application_id)


def notify_interview_scheduled(application, rescheduled=False):
    """Email the teacher the interview time. Sent after commit; failures are logged, never raised."""
    transaction.on_commit(lambda: _send_interview(application.pk, rescheduled))
