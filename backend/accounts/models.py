from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from utils import crypto

from .validators import validate_credential_file


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role="admin")
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        TEACHER = "teacher", "Teacher"
        INSTITUTE = "institute", "Institute"
        UNIVERSITY = "university", "University"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.TEACHER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    # Phase 2: email/phone OTP verification
    email_verified = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class VerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", "Full-Time"
    PART_TIME = "part_time", "Part-Time"
    CONTRACT = "contract", "Contract"
    FREELANCE = "freelance", "Freelance / Visiting"
    ADHOC = "adhoc", "Adhoc"


class InstituteType(models.TextChoices):
    PRESCHOOL = "preschool", "Pre-School / Nursery"
    PRIMARY = "primary", "Primary School (Grades 1-5)"
    SECONDARY = "secondary", "Secondary School (Grades 6-10)"
    SENIOR_SECONDARY = "senior_secondary", "Senior Secondary School (Grades 11-12)"
    UNDERGRAD = "undergrad", "Undergraduate College"
    POSTGRAD = "postgrad", "Postgraduate College / University"
    DEEMED = "deemed_university", "Deemed University"
    COACHING = "coaching", "Coaching Institute / Test Prep"
    EDTECH = "edtech", "Ed-Tech / Online Teaching"
    VOCATIONAL = "vocational", "Vocational Training Institute"
    SPECIAL_ED = "special_ed", "Special Education School"


def validate_bio(value):
    if len(value.split()) > 500:
        raise ValidationError("Bio must be 500 words or fewer.")


class TeacherProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT = "prefer_not", "Prefer not to say"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        SELECTIVE = "selective", "Selective (visible only to recruiters you apply to)"
        PRIVATE = "private", "Private"

    class WorkStatus(models.TextChoices):
        EMPLOYED = "employed", "Employed (Not Looking)"
        OPEN = "open", "Open to opportunities"
        ACTIVE = "active", "Actively Looking"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    photo = models.ImageField(upload_to="teacher_photos/", blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=12, choices=Gender.choices, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)

    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    pin_code = models.CharField(max_length=10, blank=True)
    willing_to_relocate = models.BooleanField(default=False)
    preferred_cities = models.JSONField(default=list, blank=True)
    relocation_notice_days = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=[(7, "7 days"), (15, "15 days"), (30, "30 days"), (60, "2 months")]
    )

    salary_expectation = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_negotiable = models.BooleanField(default=True)

    headline = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True, validators=[validate_bio])
    employment_status = models.CharField(max_length=10, choices=WorkStatus.choices, default=WorkStatus.OPEN)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.SELECTIVE)
    # Phase 2: replace with secure, non-downloadable streaming upload
    intro_video_url = models.URLField(blank=True)

    total_experience_years = models.PositiveSmallIntegerField(default=0)
    subjects = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)

    linkedin_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    # Job preferences
    preferred_job_types = models.JSONField(default=list, blank=True)
    preferred_grades = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return " ".join(p for p in [self.first_name, self.middle_name, self.last_name] if p)

    @property
    def completeness(self):
        checks = [
            self.first_name, self.last_name, self.photo, self.date_of_birth, self.phone,
            self.city, self.state, self.headline, self.bio, self.subjects, self.skills,
            self.intro_video_url, self.total_experience_years,
            self.pk and self.qualifications.exists(),
            self.pk and self.employment.exists(),
        ]
        return round(100 * sum(1 for c in checks if c) / len(checks))


class Qualification(models.Model):
    class Level(models.TextChoices):
        HIGH_SCHOOL = "high_school", "High School (10th)"
        INTERMEDIATE = "intermediate", "Intermediate (12th)"
        DIPLOMA = "diploma", "Diploma"
        BACHELORS = "bachelors", "Bachelor's Degree"
        MASTERS = "masters", "Master's Degree"
        MPHIL = "mphil", "M.Phil."
        PHD = "phd", "Ph.D. / Doctorate"
        PG_DIPLOMA = "pg_diploma", "PG Diploma"
        CERTIFICATE = "certificate", "Certificate"
        INTEGRATED = "integrated", "Integrated Degree"

    class CourseType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        DISTANCE = "distance", "Distance / Correspondence"

    class Grading(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        CGPA = "cgpa", "CGPA"
        GRADE = "grade", "Grade"

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="qualifications")
    level = models.CharField(max_length=15, choices=Level.choices)
    course = models.CharField(max_length=120)  # e.g. B.Ed., M.Sc.
    specialization = models.CharField(max_length=120, blank=True)
    university = models.ForeignKey(
        "UniversityProfile", on_delete=models.PROTECT, related_name="degrees",
        help_text="Awarding university. Only admin-verified universities can be chosen.",
    )
    year_of_passing = models.PositiveSmallIntegerField()
    course_type = models.CharField(max_length=10, choices=CourseType.choices, default=CourseType.FULL_TIME)
    grading_system = models.CharField(max_length=10, choices=Grading.choices, default=Grading.PERCENTAGE)
    marks = models.CharField(max_length=20, blank=True)
    # Both documents are mandatory: PDF / JPG / PNG, at most 5 MB.
    marksheet = models.FileField(upload_to="qualification_docs/", validators=[validate_credential_file])
    degree_certificate = models.FileField(upload_to="qualification_docs/", validators=[validate_credential_file])
    created_at = models.DateTimeField(auto_now_add=True)

    # Verification. A degree is "cryptographically verified" only when its university has signed it
    # (see UniversityProfile and utils/crypto.py). Setting verification_status by hand does not count.
    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    document_sha256 = models.CharField(max_length=64, blank=True)  # SHA-256 of degree_certificate when signed
    signature = models.CharField(max_length=128, blank=True)  # base64 Ed25519 signature
    signed_by = models.ForeignKey(
        "UniversityProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="signed_credentials"
    )
    signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year_of_passing"]

    def __str__(self):
        return f"{self.course} ({self.year_of_passing})"

    @property
    def cryptographically_verified(self):
        """True only for degrees signed by the university. An admin ticking 'verified' in the Django admin
        sets verification_status but no signature, so it does not earn the badge."""
        return bool(self.signature) and self.verification_status == VerificationStatus.VERIFIED

    def signing_message(self):
        return crypto.build_credential_message(
            qualification_id=self.pk, teacher_id=self.teacher_id, university_id=self.university_id,
            course=self.course, level=self.level, year_of_passing=self.year_of_passing,
            document_sha256=self.document_sha256,
        )

    def clear_signature(self, status=VerificationStatus.PENDING):
        self.verification_status = status
        self.document_sha256 = ""
        self.signature = ""
        self.signed_by = None
        self.signed_at = None


class Certification(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=150)  # CTET, NET, TEFL...
    issuing_organization = models.CharField(max_length=150, blank=True)
    date_of_issue = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    document = models.FileField(upload_to="certifications/", blank=True, null=True)
    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )

    def __str__(self):
        return self.name


class EmploymentHistory(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="employment")
    is_current = models.BooleanField(default=False)
    institute_name = models.CharField(max_length=200)
    institute_type = models.CharField(max_length=20, choices=InstituteType.choices, blank=True)
    boards = models.JSONField(default=list, blank=True)
    designation = models.CharField(max_length=100)  # PGT, TGT, PRT, Assistant Professor...
    subjects = models.JSONField(default=list, blank=True)
    grades = models.JSONField(default=list, blank=True)
    employment_type = models.CharField(max_length=10, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    achievements = models.TextField(blank=True)

    class Meta:
        ordering = ["-is_current", "-start_date"]
        verbose_name_plural = "employment history"

    def __str__(self):
        return f"{self.designation} at {self.institute_name}"


class InstituteProfile(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        UNLISTED = "unlisted", "Unlisted"
        PRIVATE = "private", "Private / Draft"

    class Plan(models.TextChoices):
        FREE = "free", "Free"
        PREMIUM = "premium", "Premium"
        ENTERPRISE = "enterprise", "Enterprise"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="institute_profile")
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="institute_logos/", blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True)
    registration_document = models.FileField(upload_to="institute_docs/", blank=True, null=True)
    institute_type = models.CharField(max_length=20, choices=InstituteType.choices, blank=True)
    affiliations = models.JSONField(default=list, blank=True)  # CBSE, CISCE, IB...
    year_established = models.PositiveSmallIntegerField(null=True, blank=True)

    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    pin_code = models.CharField(max_length=10, blank=True)

    tagline = models.CharField(max_length=160, blank=True)
    about = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    core_values = models.JSONField(default=list, blank=True)

    total_students = models.PositiveIntegerField(null=True, blank=True)
    total_teaching_staff = models.PositiveIntegerField(null=True, blank=True)

    # Admin-controlled
    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    subscription_plan = models.CharField(max_length=12, choices=Plan.choices, default=Plan.FREE)
    job_post_quota = models.PositiveIntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UniversityProfile(models.Model):
    """An awarding university. Created at registration (pending); an admin verifies it, which also
    generates its Ed25519 signing key pair. `user` is empty for universities pre-loaded by an admin
    (or migrated from old free-text entries) that have not claimed an account yet."""

    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE, related_name="university_profile")
    name = models.CharField(max_length=200, unique=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="university_logos/", blank=True, null=True)

    verification_status = models.CharField(
        max_length=10, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    is_trusted_issuer = models.BooleanField(
        default=False, help_text="Switched on at first verification. Untick to revoke signing rights."
    )
    nirf_rank = models.PositiveIntegerField(
        null=True, blank=True, help_text="Latest NIRF overall/university rank. Blank = unranked. Admin-controlled."
    )
    public_key = models.TextField(blank=True, editable=False)  # base64 Ed25519 public key
    encrypted_private_key = models.TextField(blank=True, editable=False)  # Fernet-encrypted; never serialized
    keys_generated_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def can_issue(self):
        return (
            self.verification_status == VerificationStatus.VERIFIED
            and self.is_trusted_issuer and bool(self.public_key) and bool(self.encrypted_private_key)
        )

    @property
    def key_fingerprint(self):
        return crypto.public_key_fingerprint(self.public_key) if self.public_key else ""

    def save(self, *args, **kwargs):
        # Verification is the moment the key pair is minted, whichever way the status was changed.
        if self.verification_status == VerificationStatus.VERIFIED and not self.public_key:
            self.public_key, self.encrypted_private_key = crypto.generate_keypair()
            self.keys_generated_at = timezone.now()
            self.is_trusted_issuer = True
        super().save(*args, **kwargs)


class Notification(models.Model):
    """In-app notification shown in the bell dropdown."""

    class Kind(models.TextChoices):
        DEGREE_REQUEST = "degree_request", "Degree request"
        DEGREE_SIGNED = "degree_signed", "Degree signed"
        DEGREE_REJECTED = "degree_rejected", "Degree rejected"
        TIER_UP = "tier_up", "Tier reached"

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=300, blank=True)
    link = models.CharField(max_length=200, blank=True)  # front-end route to open on click
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]

    def __str__(self):
        return f"{self.recipient_id}: {self.title}"


class TeacherMeritScore(models.Model):
    """Teacher Credential Score (TCS), 0-100. Recomputed by accounts.merit.recalculate_merit."""

    class Tier(models.TextChoices):
        LAUREATE = "laureate", "Aeterna Laureate"
        DISTINGUISHED = "distinguished", "Distinguished Scholar"
        FELLOW = "fellow", "Merit Fellow"
        ASSOCIATE = "associate", "Associate Educator"
        EMERGING = "emerging", "Emerging Educator"

    teacher = models.OneToOneField(TeacherProfile, on_delete=models.CASCADE, related_name="merit")
    score = models.PositiveSmallIntegerField(default=0)
    tier = models.CharField(max_length=15, choices=Tier.choices, default=Tier.EMERGING)
    headline = models.CharField(max_length=255, blank=True)
    # {"university": 40, "degree": 25, "certification": 15, "experience": 8}
    breakdown = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.teacher} {self.score} ({self.tier})"
