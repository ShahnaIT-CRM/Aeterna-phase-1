from django.core.management.base import BaseCommand

from lms.models import Course, Lesson

SAMPLES = [
    ("Flipped Classroom Basics", "Move instruction online and use class time for practice.", "beginner", "Flipped Classroom", [
        ("What is a flipped classroom?", 15, "Students meet new content before class, then apply it with you in the room.\n\nThink: video or reading at home, problem-solving at school."),
        ("Designing the pre-class task", 25, "Keep pre-class tasks under 15 minutes and end each with one question students must answer."),
        ("Running the in-class session", 20, "Open with a 5-minute check, then move to group problems while you circulate."),
    ]),
    ("Managing an Anxious Classroom", "Practical routines that lower anxiety for students and for you.", "intermediate", "Calm Classroom", [
        ("Spotting anxiety early", 20, "Look for avoidance, frequent bathroom requests and sudden drops in participation."),
        ("Predictable routines", 20, "Post the plan for the lesson and warn students before transitions."),
    ]),
    ("Gamification 101", "Add points, levels and challenges without making it a gimmick.", "beginner", "Gamification Starter", [
        ("Motivation first", 15, "Games work when they support mastery, not when they only reward compliance."),
        ("Your first game loop", 30, "Pick one skill, set three levels, and give feedback within a minute of each attempt."),
    ]),
]


class Command(BaseCommand):
    help = "Create a few sample micro-courses for development. Safe to run more than once."

    def handle(self, *args, **opts):
        for title, summary, level, badge, lessons in SAMPLES:
            course, created = Course.objects.get_or_create(
                title=title, defaults=dict(summary=summary, level=level, badge_name=badge, is_published=True)
            )
            if created:
                for i, (t, mins, text) in enumerate(lessons, start=1):
                    Lesson.objects.create(course=course, order=i, title=t, duration_minutes=mins, content=text)
            self.stdout.write(f"{'Created' if created else 'Exists '}: {title}")
