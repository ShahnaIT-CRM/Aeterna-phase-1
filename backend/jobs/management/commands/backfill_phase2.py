"""Score and attach documents for applications created before Phase 2.

    python manage.py backfill_phase2          # only applications with no score yet
    python manage.py backfill_phase2 --all    # recompute everything
"""
from django.core.management.base import BaseCommand

from jobs.matching import compute_match_breakdown
from jobs.models import JobApplication


class Command(BaseCommand):
    help = "Compute match scores and attach documents for existing applications."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Recompute even if already scored.")

    def handle(self, *args, **opts):
        qs = JobApplication.objects.select_related("job", "teacher")
        if not opts["all"]:
            qs = qs.filter(match_score__isnull=True)
        n = 0
        for app in qs:
            b = compute_match_breakdown(app.teacher, app.job)
            app.match_score, app.match_breakdown = b["score"], b
            app.save(update_fields=["match_score", "match_breakdown"])
            app.attach_documents()
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {n} application(s)."))
