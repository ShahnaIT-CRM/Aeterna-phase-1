"""Phase 4, step 2 of 3: carry existing data across.

* Every distinct free-text university name becomes an UNVERIFIED, account-less UniversityProfile, and the
  degree points at it. An admin can later verify/claim it (which mints its keys) or merge duplicates.
* Phase 3 "blockchain" proofs were mock transactions with no signature, so those degrees go back to
  Pending until their university signs them for real.
* NULL document columns become empty strings so the files can be made mandatory in step 3.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Qualification = apps.get_model("accounts", "Qualification")
    University = apps.get_model("accounts", "UniversityProfile")

    by_key = {}
    for q in Qualification.objects.all().iterator():
        raw = " ".join((q.university or "").split()) or "Unknown university"
        key = raw.lower()
        if key not in by_key:
            by_key[key], _ = University.objects.get_or_create(name=raw)
        q.university_ref = by_key[key]
        q.marksheet = q.marksheet or ""
        q.degree_certificate = q.degree_certificate or ""
        if q.blockchain_tx_hash or q.verification_status == "verified":
            q.verification_status = "pending"
            q.document_sha256 = ""
            q.signed_at = None
        q.save()


class Migration(migrations.Migration):

    dependencies = [("accounts", "0003_phase4_pki_schema")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
