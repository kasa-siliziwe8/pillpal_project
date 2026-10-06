from datetime import timedelta, time, date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User, CaregiverPatient
from core.models import Clinic
from medications.models import Medication, MedicationSchedule, DoseLog
from notifications.escalation import (
    run_escalation_check, required_level, resolve_for_dose,
)
from notifications.models import Escalation, Notification


class EscalationTestBase(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(name='Test Clinic', province='NC', district='SP')
        self.patient = User.objects.create_user('pat', first_name='Thabo', role='patient', clinic=self.clinic)
        self.caregiver = User.objects.create_user('cg', first_name='Nomsa', role='caregiver')
        self.chw = User.objects.create_user('chw1', role='chw', clinic=self.clinic)
        self.admin = User.objects.create_user('adm', role='clinic_admin', clinic=self.clinic)
        CaregiverPatient.objects.create(caregiver=self.caregiver, patient=self.patient, approved=True)

        med = Medication.objects.create(
            generic_name='Tenofovir', description='d', how_to_take='h',
            side_effects='s', missed_dose_instructions='m')
        self.schedule = MedicationSchedule.objects.create(
            patient=self.patient, medication=med, dosage='300mg',
            scheduled_time_1=time(8, 0), start_date=date.today())
        self.now = timezone.now()

    def make_dose(self, minutes_ago, status='pending'):
        return DoseLog.objects.create(
            schedule=self.schedule, patient=self.patient,
            scheduled_datetime=self.now - timedelta(minutes=minutes_ago), status=status)


class RuleTests(EscalationTestBase):
    def test_levels_by_age(self):
        self.assertEqual(required_level(self.make_dose(30), self.now), 0)
        self.assertEqual(required_level(self.make_dose(61), self.now), 1)
        self.assertEqual(required_level(self.make_dose(241), self.now), 2)

    def test_confirmed_never_escalates(self):
        self.assertEqual(required_level(self.make_dose(500, 'confirmed'), self.now), 0)


class RunCheckTests(EscalationTestBase):
    def test_recent_dose_untouched(self):
        dose = self.make_dose(30)
        run_escalation_check(self.now)
        dose.refresh_from_db()
        self.assertEqual(dose.status, 'pending')
        self.assertEqual(Escalation.objects.count(), 0)

    def test_level1_marks_missed_and_alerts_caregiver(self):
        dose = self.make_dose(90)
        result = run_escalation_check(self.now)
        dose.refresh_from_db()
        self.assertEqual(dose.status, 'missed')
        self.assertTrue(dose.escalated)
        self.assertEqual(result.level1_created, 1)
        esc = Escalation.objects.get()
        self.assertEqual(esc.level, 1)
        self.assertEqual(esc.alert_sent_to, self.caregiver)
        note = Notification.objects.get(recipient=self.caregiver)
        self.assertEqual(note.notification_type, 'escalation')
        self.assertEqual(note.dose_log, dose)
        self.assertIn('Thabo', note.message)
        self.assertIn('Tenofovir', note.message)

    def test_level2_alerts_chw_and_admin_and_backfills_level1(self):
        self.make_dose(300)
        result = run_escalation_check(self.now)
        self.assertEqual(result.level1_created, 1)
        self.assertEqual(result.level2_created, 1)
        recipients = set(Escalation.objects.filter(level=2).values_list('alert_sent_to', flat=True))
        self.assertEqual(recipients, {self.chw.pk, self.admin.pk})

    def test_idempotent(self):
        self.make_dose(90)
        run_escalation_check(self.now)
        run_escalation_check(self.now)
        run_escalation_check(self.now + timedelta(minutes=5))
        self.assertEqual(Escalation.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_level2_added_later_without_repeating_level1(self):
        self.make_dose(90)
        run_escalation_check(self.now)
        run_escalation_check(self.now + timedelta(hours=4))
        self.assertEqual(Escalation.objects.filter(level=1).count(), 1)
        self.assertEqual(Escalation.objects.filter(level=2).count(), 2)  # chw + admin

    def test_confirmed_dose_ignored(self):
        self.make_dose(300, 'confirmed')
        run_escalation_check(self.now)
        self.assertEqual(Escalation.objects.count(), 0)

    def test_old_doses_outside_window_ignored(self):
        self.make_dose(60 * 24 * 10)  # 10 days old (e.g. old seed data)
        run_escalation_check(self.now)
        self.assertEqual(Escalation.objects.count(), 0)

    def test_already_missed_dose_still_escalates(self):
        """Seed data / other code may set 'missed' directly; we must still escalate it."""
        self.make_dose(90, 'missed')
        run_escalation_check(self.now)
        self.assertEqual(Escalation.objects.filter(level=1).count(), 1)

    def test_unapproved_caregiver_not_alerted(self):
        CaregiverPatient.objects.update(approved=False)
        self.make_dose(90)
        result = run_escalation_check(self.now)
        self.assertEqual(Escalation.objects.count(), 0)
        self.assertEqual(result.skipped_no_recipient, 1)

    def test_caregiver_with_alerts_off_not_alerted(self):
        self.caregiver.notif_caregiver_alerts = False
        self.caregiver.save()
        self.make_dose(90)
        run_escalation_check(self.now)
        self.assertEqual(Escalation.objects.count(), 0)

    def test_patient_without_clinic_skips_level2(self):
        self.patient.clinic = None
        self.patient.save()
        self.make_dose(300)
        result = run_escalation_check(self.now)
        self.assertEqual(result.level1_created, 1)
        self.assertEqual(result.level2_created, 0)

    def test_dry_run_writes_nothing(self):
        dose = self.make_dose(90)
        result = run_escalation_check(self.now, dry_run=True)
        dose.refresh_from_db()
        self.assertEqual(dose.status, 'pending')
        self.assertEqual(Escalation.objects.count(), 0)
        self.assertEqual(result.level1_created, 1)

    @override_settings(ESCALATION_MISSED_AFTER_MINUTES=10, ESCALATION_LEVEL2_AFTER_MINUTES=20)
    def test_thresholds_configurable(self):
        self.make_dose(25)
        result = run_escalation_check(self.now)
        self.assertEqual(result.level1_created, 1)
        self.assertEqual(result.level2_created, 1)


class ResolveTests(EscalationTestBase):
    def test_resolve_for_dose(self):
        dose = self.make_dose(300)
        run_escalation_check(self.now)
        count = resolve_for_dose(dose)
        self.assertEqual(count, 3)
        self.assertFalse(Escalation.objects.filter(resolved=False).exists())
        self.assertFalse(Escalation.objects.filter(resolved_at__isnull=True).exists())


class CommandTests(EscalationTestBase):
    def test_command_runs(self):
        self.make_dose(90)
        out = StringIO()
        call_command('check_escalations', stdout=out)
        self.assertIn('L1 caregiver: 1', out.getvalue())
        self.assertEqual(Escalation.objects.count(), 1)

    def test_command_dry_run(self):
        self.make_dose(90)
        out = StringIO()
        call_command('check_escalations', '--dry-run', stdout=out)
        self.assertIn('[DRY RUN]', out.getvalue())
        self.assertEqual(Escalation.objects.count(), 0)


class WiringTests(EscalationTestBase):
    """Views and endpoints that consume escalations."""

    def test_caregiver_dashboard_shows_open_escalation(self):
        self.make_dose(90)
        run_escalation_check(self.now)
        self.client.force_login(self.caregiver)
        resp = self.client.get('/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Alert: Tenofovir')
        self.assertContains(resp, 'resolveEscalation')

    def test_resolved_escalation_hidden_from_dashboard(self):
        dose = self.make_dose(90)
        run_escalation_check(self.now)
        resolve_for_dose(dose)
        self.client.force_login(self.caregiver)
        resp = self.client.get('/dashboard/')
        self.assertNotContains(resp, 'Alert: Tenofovir')

    def test_caregiver_can_resolve_via_endpoint(self):
        self.make_dose(90)
        run_escalation_check(self.now)
        esc = Escalation.objects.get()
        self.client.force_login(self.caregiver)
        resp = self.client.post(f'/notifications/escalations/{esc.pk}/resolve/')
        self.assertEqual(resp.status_code, 200)
        esc.refresh_from_db()
        self.assertTrue(esc.resolved)
        self.assertIsNotNone(esc.resolved_at)

    def test_resolve_requires_post(self):
        self.make_dose(90)
        run_escalation_check(self.now)
        esc = Escalation.objects.get()
        self.client.force_login(self.caregiver)
        self.assertEqual(self.client.get(f'/notifications/escalations/{esc.pk}/resolve/').status_code, 405)

    def test_unrelated_user_cannot_resolve(self):
        self.make_dose(90)
        run_escalation_check(self.now)
        esc = Escalation.objects.get()
        stranger = User.objects.create_user('stranger', role='caregiver')
        self.client.force_login(stranger)
        resp = self.client.post(f'/notifications/escalations/{esc.pk}/resolve/')
        self.assertEqual(resp.status_code, 403)
        esc.refresh_from_db()
        self.assertFalse(esc.resolved)

    def test_clinic_admin_can_resolve_level2(self):
        self.make_dose(300)
        run_escalation_check(self.now)
        esc = Escalation.objects.get(level=2, alert_sent_to=self.admin)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(f'/notifications/escalations/{esc.pk}/resolve/').status_code, 200)

    def test_patient_confirming_late_auto_resolves(self):
        dose = self.make_dose(90)
        run_escalation_check(self.now)
        dose.refresh_from_db()
        self.assertEqual(dose.status, 'missed')
        self.client.force_login(self.patient)
        resp = self.client.post('/api/confirm-dose/', data='{"log_id": %d}' % dose.pk,
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        dose.refresh_from_db()
        self.assertEqual(dose.status, 'confirmed')
        self.assertFalse(Escalation.objects.filter(dose_log=dose, resolved=False).exists())

    def test_medications_confirm_endpoint_also_auto_resolves(self):
        dose = self.make_dose(90)
        run_escalation_check(self.now)
        self.client.force_login(self.patient)
        self.client.post('/medications/api/confirm/', data='{"log_id": %d}' % dose.pk,
                         content_type='application/json')
        self.assertFalse(Escalation.objects.filter(dose_log=dose, resolved=False).exists())
