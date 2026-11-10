"""Phase 4, step 1 of 3: new tables and nullable/new columns. Nothing is removed yet."""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_phase3_blockchain_credentials"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("teacher", "Teacher"), ("institute", "Institute"), ("university", "University"), ("admin", "Admin")],
                default="teacher", max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="UniversityProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, unique=True)),
                ("city", models.CharField(blank=True, max_length=80)),
                ("state", models.CharField(blank=True, max_length=80)),
                ("website", models.URLField(blank=True)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="university_logos/")),
                ("verification_status", models.CharField(
                    choices=[("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")],
                    default="pending", max_length=10)),
                ("is_trusted_issuer", models.BooleanField(
                    default=False, help_text="Switched on at first verification. Untick to revoke signing rights.")),
                ("nirf_rank", models.PositiveIntegerField(
                    blank=True, null=True,
                    help_text="Latest NIRF overall/university rank. Blank = unranked. Admin-controlled.")),
                ("public_key", models.TextField(blank=True, editable=False)),
                ("encrypted_private_key", models.TextField(blank=True, editable=False)),
                ("keys_generated_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="university_profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(
                    choices=[("degree_request", "Degree request"), ("degree_signed", "Degree signed"),
                             ("degree_rejected", "Degree rejected"), ("tier_up", "Tier reached")],
                    max_length=20)),
                ("title", models.CharField(max_length=160)),
                ("body", models.CharField(blank=True, max_length=300)),
                ("link", models.CharField(blank=True, max_length=200)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("recipient", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name="notifications",
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "is_read", "-created_at"], name="accounts_no_recipie_646219_idx"),
        ),
        migrations.CreateModel(
            name="TeacherMeritScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("tier", models.CharField(
                    choices=[("laureate", "Aeterna Laureate"), ("distinguished", "Distinguished Scholar"),
                             ("fellow", "Merit Fellow"), ("associate", "Associate Educator"),
                             ("emerging", "Emerging Educator")],
                    default="emerging", max_length=15)),
                ("headline", models.CharField(blank=True, max_length=255)),
                ("breakdown", models.JSONField(blank=True, default=dict)),
                ("calculated_at", models.DateTimeField(auto_now=True)),
                ("teacher", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name="merit", to="accounts.teacherprofile")),
            ],
        ),
        # New qualification columns. `university_ref` becomes `university` in step 3.
        migrations.AddField(
            model_name="qualification", name="university_ref",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="degrees",
                to="accounts.universityprofile"),
        ),
        migrations.AddField(
            model_name="qualification", name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="qualification", name="signature",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="qualification", name="signed_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="signed_credentials", to="accounts.universityprofile"),
        ),
        migrations.RenameField(model_name="qualification", old_name="verified_at", new_name="signed_at"),
    ]
