"""Keep every teacher's merit score fresh. Each handler only schedules work for after the commit."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .merit import schedule_recalculation
from .models import Certification, Qualification, TeacherProfile, UniversityProfile


@receiver([post_save, post_delete], sender=Qualification)
@receiver([post_save, post_delete], sender=Certification)
def _recalc_for_child(sender, instance, **kwargs):
    schedule_recalculation(instance.teacher_id)


@receiver(post_save, sender=TeacherProfile)
def _recalc_for_profile(sender, instance, created, update_fields=None, **kwargs):
    if created or update_fields is None or "total_experience_years" in update_fields:
        schedule_recalculation(instance.pk)


@receiver(post_save, sender=UniversityProfile)
def _recalc_for_university(sender, instance, created, **kwargs):
    """NIRF rank or trusted status changed: refresh everyone holding a degree signed by this university."""
    if created:
        return
    for tid in instance.signed_credentials.values_list("teacher_id", flat=True).distinct():
        schedule_recalculation(tid)
