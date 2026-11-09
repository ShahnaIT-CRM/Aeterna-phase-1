from django.db import models

from accounts.models import (
    Certification, EmploymentType, InstituteProfile, Qualification, TeacherProfile,
)


class JobPost(models.Model):
    class WorkMode(models.TextChoices):
        ONSITE = "onsite", "Onsite"
        HYBRID = "hybrid", "Hybrid / Guest Lecturer"
        REMOTE = "remote", "Remote"

    class SalaryDisplay(models.TextChoices):
        RANGE = "range", "Show salary range"
        INDUSTRY = "industry", "As per industry standards"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    institute = models.ForeignKey(InstituteProfile, on_delete=models.CASCADE, related_name="jobs")
    title = models.CharField(max_length=200)  # e.g. "PGT Physics"
    description = models.TextField()
    employment_type = models.CharField(max_length=10, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    work_mode = models.CharField(max_length=10, choices=WorkMode.choices, default=WorkMode.ONSITE)

    # Education & experience requirements
    mandatory_qualification = models.CharField(max_length=200, blank=True)  # "MSc + B.Ed"
    preferred_qualification = models.CharField(max_length=200, blank=True)  # "PhD preferred"
    min_experience_years = models.PositiveSmallIntegerField(default=0)
    specialization = models.CharField(max_length=200, blank=True)
    mandatory_certifications = models.JSONField(default=list, blank=True)  # CTET, NET...
    preferred_certifications = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)

    # Position & compensation
    designation = models.CharField(max_length=100, blank=True)  # PGT, TGT...
    department = models.CharField(max_length=100, blank=True)
    grade_level = models.CharField(max_length=100, blank=True)
    curriculum = models.CharField(max_length=100, blank=True)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_display = models.CharField(max_length=10, choices=SalaryDisplay.choices, default=SalaryDisplay.RANGE)
    salary_negotiable = models.BooleanField(default=True)
    key_benefits = models.JSONField(default=list, blank=True)  # Health insurance, PF...
    other_benefits = models.TextField(blank=True)

    # Location
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)

    # Recruitment process
    application_deadline = models.DateField(null=True, blank=True)
    selection_process = models.TextField(blank=True)
    joining_date = models.DateField(null=True, blank=True)
    vacancies = models.PositiveSmallIntegerField(default=1)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.institute.name}"


class JobQuestion(models.Model):
    """Pre-set application questions (2-3 per job)."""

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=300)

    class Meta:
        ordering = ["id"]


class JobApplication(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        VIEWED = "viewed", "Viewed"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview scheduled"
        REJECTED = "rejected", "Rejected"
        OFFERED = "offered", "Offer letter sent"
        HIRED = "hired", "Hired"
        BOOKMARKED = "bookmarked", "Bookmarked for later"

    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="applications")
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="applications")
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.APPLIED)
    # Phase 2: filled by the matching engine (see jobs/matching.py) when the teacher applies.
    # match_breakdown stores the per-factor explanation so the institute can see why.
    match_score = models.FloatField(null=True, blank=True)
    match_breakdown = models.JSONField(default=dict, blank=True)
    # Phase 2 document auto-fill: the teacher's uploaded degrees/certificates, linked at apply time.
    attached_qualifications = models.ManyToManyField(
        Qualification, blank=True, related_name="job_applications"
    )
    attached_certifications = models.ManyToManyField(
        Certification, blank=True, related_name="job_applications"
    )
    # Phase 3: interview scheduler. Set through POST /api/applications/{id}/schedule-interview/.
    # `interview_details` is where to go: a meeting link, room number or address.
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_details = models.CharField(max_length=300, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [models.UniqueConstraint(fields=["job", "teacher"], name="one_application_per_job")]

    def attach_documents(self):
        """Document auto-fill: link the teacher's degrees and certificates that have an uploaded file.

        Entries with no file are skipped (nothing for the institute to open); they still appear in
        the candidate's profile summary. Links are to the live records, so if the teacher later
        deletes an entry it disappears from this application too.
        """
        t = self.teacher
        quals = [
            q for q in t.qualifications.all() if q.degree_certificate or q.marksheet
        ]
        certs = [c for c in t.certifications.all() if c.document]
        self.attached_qualifications.set(quals)
        self.attached_certifications.set(certs)
        return len(quals), len(certs)


class ApplicationAnswer(models.Model):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(JobQuestion, on_delete=models.CASCADE)
    answer = models.TextField()
