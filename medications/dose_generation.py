"""
Dose-log generation — Reminder Engine & Scheduling (Vhulenda's workstream).

Turns each active MedicationSchedule into DoseLog rows for a given day,
respecting frequency and scheduled_time_1/2, in the project's local timezone
(Africa/Johannesburg).

Everyone downstream (notification sending, escalation, reporting) depends on
this producing correct, non-duplicate DoseLog rows, so this module is
deliberately idempotent: running it twice for the same day never creates
duplicate doses.

Known limitation: MedicationSchedule only has scheduled_time_1 and
scheduled_time_2. 'three_daily' and 'weekly' frequencies are accepted by the
model but have no field for a 3rd time or a chosen weekday. For now:
  - three_daily generates from time_1 and time_2 only (2 of the 3 doses),
    flagged in the result so this is visible rather than silently wrong.
  - weekly generates every day using time_1, same as once_daily, since there's
    no day-of-week field to restrict it. Also flagged.
This should be raised with the group — ideally scheduled_time_3 and a
weekday field get added to MedicationSchedule.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.utils import timezone

from .models import MedicationSchedule, DoseLog


@dataclass
class GenerationResult:
    created: int = 0
    already_existed: int = 0
    schedules_processed: int = 0
    schedules_skipped_inactive_or_dated: int = 0
    incomplete_frequency_schedules: list = field(default_factory=list)  # [(schedule_id, frequency)]


def _times_for(schedule):
    """Which TimeField(s) to generate a dose for, given the schedule's frequency."""
    times = [schedule.scheduled_time_1]
    if schedule.frequency in ('twice_daily', 'three_daily') and schedule.scheduled_time_2:
        times.append(schedule.scheduled_time_2)
    return times


def _is_due_today(schedule, target_date):
    """Active, started, and not past its end_date."""
    if not schedule.is_active:
        return False
    if schedule.start_date > target_date:
        return False
    if schedule.end_date and schedule.end_date < target_date:
        return False
    return True


def generate_doses_for_date(target_date=None, result=None):
    """
    Create today's (or target_date's) DoseLog rows from every active
    MedicationSchedule that is due. Safe to re-run: existing rows for the
    same schedule + scheduled_datetime are left untouched, not duplicated.
    """
    target_date = target_date or timezone.localdate()
    result = result or GenerationResult()
    current_tz = timezone.get_current_timezone()

    # Fetch all schedules (not just is_active=True) so inactive ones are counted as
    # skipped rather than silently invisible.
    schedules = MedicationSchedule.objects.select_related('patient', 'medication')

    for schedule in schedules:
        if not _is_due_today(schedule, target_date):
            result.schedules_skipped_inactive_or_dated += 1
            continue

        result.schedules_processed += 1
        if schedule.frequency in ('three_daily', 'weekly'):
            result.incomplete_frequency_schedules.append((schedule.pk, schedule.frequency))

        for t in _times_for(schedule):
            naive_dt = datetime.combine(target_date, t)
            scheduled_dt = timezone.make_aware(naive_dt, current_tz)

            _, was_created = DoseLog.objects.get_or_create(
                schedule=schedule,
                scheduled_datetime=scheduled_dt,
                defaults={
                    'patient': schedule.patient,
                    'status': 'pending',
                },
            )
            if was_created:
                result.created += 1
            else:
                result.already_existed += 1

    return result


def generate_doses_for_range(start_date, end_date):
    """Convenience for backfilling / demos: generate for each day in [start_date, end_date]."""
    result = GenerationResult()
    d = start_date
    while d <= end_date:
        generate_doses_for_date(d, result)
        d += timedelta(days=1)
    return result
