from django.test import TestCase
from rest_framework.test import APIClient

from jobs.tests import make_institute, make_teacher

from .models import Course, Enrollment, Lesson


def auth(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


class LmsTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Flipped Classroom", summary="s", is_published=True)
        self.l1 = Lesson.objects.create(course=self.course, order=1, title="Intro", duration_minutes=20, content="SECRET-1")
        self.l2 = Lesson.objects.create(course=self.course, order=2, title="Practice", duration_minutes=30, content="SECRET-2")
        Course.objects.create(title="Hidden draft", summary="s", is_published=False)
        self.t = make_teacher()
        self.c = auth(self.t.user)

    def test_list_shows_only_published_with_counts(self):
        rows = self.c.get("/api/lms/courses/").data
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["lesson_count"], rows[0]["total_minutes"]), (2, 50))
        self.assertIsNone(rows[0]["enrollment_id"])

    def test_content_hidden_until_enrolled(self):
        before = self.c.get(f"/api/lms/courses/{self.course.pk}/").data
        self.assertNotIn("SECRET", str(before))
        self.c.post(f"/api/lms/courses/{self.course.pk}/enroll/")
        after = self.c.get(f"/api/lms/courses/{self.course.pk}/").data
        self.assertIn("SECRET-1", str(after))

    def test_enroll_once_only(self):
        self.assertEqual(self.c.post(f"/api/lms/courses/{self.course.pk}/enroll/").status_code, 201)
        self.assertEqual(self.c.post(f"/api/lms/courses/{self.course.pk}/enroll/").status_code, 400)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_institutes_cannot_enroll_but_can_browse(self):
        i = auth(make_institute().user)
        self.assertEqual(i.post(f"/api/lms/courses/{self.course.pk}/enroll/").status_code, 403)
        self.assertEqual(i.get("/api/lms/courses/").status_code, 200)

    def test_cannot_enroll_in_empty_or_unpublished_course(self):
        empty = Course.objects.create(title="Empty", summary="s", is_published=True)
        self.assertEqual(self.c.post(f"/api/lms/courses/{empty.pk}/enroll/").status_code, 400)
        draft = Course.objects.get(title="Hidden draft")
        self.assertEqual(self.c.post(f"/api/lms/courses/{draft.pk}/enroll/").status_code, 404)

    def test_progress_and_completion(self):
        eid = self.c.post(f"/api/lms/courses/{self.course.pk}/enroll/").data["id"]
        r = self.c.post(f"/api/lms/enrollments/{eid}/complete-lesson/", {"lesson": self.l1.pk}, format="json")
        self.assertEqual((r.data["progress"], r.data["status"]), (50, "enrolled"))
        self.c.post(f"/api/lms/enrollments/{eid}/complete-lesson/", {"lesson": self.l1.pk}, format="json")  # idempotent
        r = self.c.post(f"/api/lms/enrollments/{eid}/complete-lesson/", {"lesson": self.l2.pk}, format="json")
        self.assertEqual((r.data["progress"], r.data["status"]), (100, "completed"))
        self.assertIsNotNone(r.data["completed_at"])
        self.assertEqual(r.data["badge"], "Flipped Classroom")

    def test_lesson_from_another_course_rejected(self):
        other = Course.objects.create(title="Other", summary="s", is_published=True)
        foreign = Lesson.objects.create(course=other, order=1, title="x")
        eid = self.c.post(f"/api/lms/courses/{self.course.pk}/enroll/").data["id"]
        r = self.c.post(f"/api/lms/enrollments/{eid}/complete-lesson/", {"lesson": foreign.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cannot_touch_another_teachers_enrollment(self):
        eid = self.c.post(f"/api/lms/courses/{self.course.pk}/enroll/").data["id"]
        other = auth(make_teacher(email="t2@x.com").user)
        r = other.post(f"/api/lms/enrollments/{eid}/complete-lesson/", {"lesson": self.l1.pk}, format="json")
        self.assertEqual(r.status_code, 404)
