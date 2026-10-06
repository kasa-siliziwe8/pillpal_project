"""
Escalation protocol for missed doses.

This module is deliberately independent of *how* DoseLog rows get created
(Vhulenda's generate_daily_doses) and of *how* messages are physically sent
(Mbuzeni's notification service). It only relies on the DoseLog contract:

    status, scheduled_datetime, confirmed_at, escalated

Rule
----
    scheduled time + MISSED_AFTER      -> pending dose is marked 'missed'
                                          and a LEVEL 1 escalation goes to the
                                          patient's approved caregiver(s)
    scheduled time + LEVEL2_AFTER      -> if still not confirmed, a LEVEL 2
                                          escalation goes to the CHW(s) and
                                          clinic admin(s) at the patient's clinic

Both thresholds can be overridden in settings.py:

    ESCALATION_MISSED_AFTER_MINUTES = 60
    ESCALATION_LEVEL2_AFTER_MINUTES = 240
    ESCALATION_MAX_AGE_HOURS = 48

Everything here is idempotent: running it every minute or once a day never
creates duplicate escalations for the same dose and level.
"""
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import CaregiverPatient, User
from medications.models import DoseLog
from .models import Escalation, Notification

LEVEL_CAREGIVER = 1
LEVEL_CLINIC = 2


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def missed_after():
    return timedelta(minutes=getattr(settings, 'ESCALATION_MISSED_AFTER_MINUTES', 60))


def level2_after():
    return timedelta(minutes=getattr(settings, 'ESCALATION_LEVEL2_AFTER_MINUTES', 240))


def max_age():
    """Doses older than this are left alone (e.g. old seed data, historic logs)."""
    return timedelta(hours=getattr(settings, 'ESCALATION_MAX_AGE_HOURS', 48))


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #
@dataclass
class EscalationResult:
    marked_missed: int = 0
    level1_created: int = 0
    level2_created: int = 0
    skipped_no_recipient: int = 0
    dose_ids: list = field(default_factory=list)

    @property
    def total_escalations(self):
        return self.level1_created + self.level2_created


# --------------------------------------------------------------------------- #
# Checkable rule functions (pure: no writes)
# --------------------------------------------------------------------------- #
def is_overdue(dose, now=None):
    """True if the dose is unconfirmed and past the 'missed' threshold."""
    now = now or timezone.now()
    return dose.status != 'confirmed' and now >= dose.scheduled_datetime + missed_after()


def required_level(dose, now=None):
    """
    Highest escalation level this dose currently warrants.
    Returns 0 (none), 1 (caregiver) or 2 (clinic).
    """
    now = now or timezone.now()
    if dose.status == 'confirmed':
        return 0
    age = now - dose.scheduled_datetime
    if age >= level2_after():
        return LEVEL_CLINIC
    if age >= missed_after():
        return LEVEL_CAREGIVER
    return 0


def get_caregivers(patient):
    """Approved caregivers who have alerts switched on."""
    links = CaregiverPatient.objects.filter(
        patient=patient, approved=True, caregiver__notif_caregiver_alerts=True
    ).select_related('caregiver')
    return [link.caregiver for link in links]


def get_clinic_staff(patient):
    """CHWs and clinic admins at the patient's clinic (the only CHW link the schema has)."""
    if not patient.clinic_id:
        return []
    return list(User.objects.filter(clinic=patient.clinic, role__in=['chw', 'clinic_admin']))


# --------------------------------------------------------------------------- #
# Message copy
# --------------------------------------------------------------------------- #
def _patient_name(patient):
    return patient.first_name or patient.username


def build_message(dose, level):
    name = _patient_name(dose.patient)
    med = dose.schedule.medication.generic_name
    when = timezone.localtime(dose.scheduled_datetime).strftime('%H:%M')
    if level == LEVEL_CAREGIVER:
        return (f'PILL PAL ALERT (Caregiver): {name} may have missed their {when} '
                f'{med} dose. Please check in with them.')
    return (f'PILL PAL ALERT (Clinic): {name} has not confirmed their {when} {med} dose '
            f'after several hours. Please follow up.')


def _channel_for(recipient):
    """Map the recipient's preference to a Notification channel ('app' if unknown)."""
    pref = recipient.channel_preference
    return pref if pref in ('sms', 'voice', 'app') else 'app'


# --------------------------------------------------------------------------- #
# Actions (these write)
# --------------------------------------------------------------------------- #
def _send(dose, level, recipient):
    """
    Create the Escalation + Notification for one recipient.

    Notification is created directly here. When Mbuzeni's notifications/services.py
    lands, swap the Notification.objects.create(...) call below for her service
    function; nothing else in this module needs to change.
    """
    Escalation.objects.create(dose_log=dose, level=level, alert_sent_to=recipient)
    Notification.objects.create(
        recipient=recipient,
        channel=_channel_for(recipient),
        notification_type='escalation',
        message=build_message(dose, level),
        status='sent',
        sent_at=timezone.now(),
        dose_log=dose,
    )


def _escalate_level(dose, level, result):
    """Escalate one dose at one level, skipping if that level already exists."""
    if Escalation.objects.filter(dose_log=dose, level=level).exists():
        return False

    recipients = get_caregivers(dose.patient) if level == LEVEL_CAREGIVER else get_clinic_staff(dose.patient)
    if not recipients:
        result.skipped_no_recipient += 1
        return False

    for recipient in recipients:
        _send(dose, level, recipient)

    if level == LEVEL_CAREGIVER:
        result.level1_created += 1
    else:
        result.level2_created += 1
    return True


def run_escalation_check(now=None, dry_run=False):
    """
    Scan for overdue doses and escalate them. Safe to call repeatedly.

    Returns an EscalationResult. With dry_run=True nothing is written, but the
    counts show what *would* happen.
    """
    now = now or timezone.now()
    result = EscalationResult()

    candidates = (
        DoseLog.objects
        .exclude(status='confirmed')
        .filter(
            scheduled_datetime__lte=now - missed_after(),
            scheduled_datetime__gte=now - max_age(),
        )
        .select_related('patient', 'patient__clinic', 'schedule__medication')
        .order_by('scheduled_datetime')
    )

    for dose in candidates:
        level = required_level(dose, now)
        if level == 0:
            continue

        if dry_run:
            result.dose_ids.append(dose.pk)
            if dose.status == 'pending':
                result.marked_missed += 1
            for lvl in range(1, level + 1):
                if not Escalation.objects.filter(dose_log=dose, level=lvl).exists():
                    if lvl == LEVEL_CAREGIVER:
                        result.level1_created += 1
                    else:
                        result.level2_created += 1
            continue

        with transaction.atomic():
            # Re-read inside the transaction so a confirmation that lands between the
            # query and now is not overwritten.
            dose.refresh_from_db(fields=['status', 'escalated'])
            if dose.status == 'confirmed':
                continue

            if dose.status == 'pending':
                dose.status = 'missed'
                result.marked_missed += 1

            # Catch up on any level not yet sent (level 1 first, then 2).
            for lvl in range(1, level + 1):
                _escalate_level(dose, lvl, result)

            dose.escalated = True
            dose.save(update_fields=['status', 'escalated'])
            result.dose_ids.append(dose.pk)

    return result


def resolve_for_dose(dose, when=None):
    """
    Mark every open escalation on this dose as resolved.
    Call this when the patient finally confirms, or when a caregiver/CHW acknowledges.
    Returns the number of escalations resolved.
    """
    when = when or timezone.now()
    return Escalation.objects.filter(dose_log=dose, resolved=False).update(
        resolved=True, resolved_at=when
    )
