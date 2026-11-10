from django.core.management.base import BaseCommand

from accounts.merit import recalculate_merit
from accounts.models import TeacherProfile


class Command(BaseCommand):
    help = "Recompute every teacher's merit score (e.g. after Phase 4 migration or a yearly NIRF update)."

    def handle(self, *args, **opts):
        n = 0
        for t in TeacherProfile.objects.iterator():
            recalculate_merit(t)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Recalculated {n} teacher score(s)."))
