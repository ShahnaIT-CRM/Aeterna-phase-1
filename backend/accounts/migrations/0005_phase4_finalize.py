"""Phase 4, step 3 of 3: drop the free-text university and every blockchain column, make documents mandatory."""
import django.db.models.deletion
from django.db import migrations, models

import accounts.validators


class Migration(migrations.Migration):

    dependencies = [("accounts", "0004_phase4_convert_data")]

    operations = [
        migrations.RemoveField(model_name="qualification", name="university"),
        migrations.RenameField(model_name="qualification", old_name="university_ref", new_name="university"),
        migrations.AlterField(
            model_name="qualification", name="university",
            field=models.ForeignKey(
                help_text="Awarding university. Only admin-verified universities can be chosen.",
                on_delete=django.db.models.deletion.PROTECT, related_name="degrees", to="accounts.universityprofile"),
        ),
        migrations.RemoveField(model_name="qualification", name="blockchain_tx_hash"),
        migrations.RemoveField(model_name="qualification", name="blockchain_block"),
        migrations.RemoveField(model_name="qualification", name="issuer_document"),
        migrations.RemoveField(model_name="qualification", name="verified_by"),
        migrations.AlterField(
            model_name="qualification", name="marksheet",
            field=models.FileField(
                upload_to="qualification_docs/", validators=[accounts.validators.validate_credential_file]),
        ),
        migrations.AlterField(
            model_name="qualification", name="degree_certificate",
            field=models.FileField(
                upload_to="qualification_docs/", validators=[accounts.validators.validate_credential_file]),
        ),
    ]
