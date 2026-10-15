from datetime import date, time

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, CaregiverPatient
from core.models import Clinic
from medications.models import Medication, MedicationSchedule, DoseLog
from notifications.models import Escalation


class DemoTriggerMissedDoseTests(TestCase):
    """Patient-facing demo button: simulate a missed dose for live demos."""

    def setUp(self):
        self.clinic = Clinic.objects.create(name='Demo Clinic', province='NC', district='SP')
        self.patient = User.objects.create_user('demopat', role='patient', clinic=self.clinic)
        self.caregiver = User.objects.create_user('democg', role='caregiver')
        CaregiverPatient.objects.create(caregiver=self.caregiver, patient=self.patient, approved=True)
        self.med = Medication.objects.create(
            generic_name='Efavirenz', description='d', how_to_take='h',
            side_effects='s', missed_dose_instructions='m')
        self.schedule = MedicationSchedule.objects.create(
            patient=self.patient, medication=self.med, dosage='600mg',
            scheduled_time_1=time(8, 0), start_date=date.today(), is_active=True)

    def test_creates_overdue_dose_and_escalation(self):
        self.client.force_login(self.patient)
        resp = self.client.post('/demo/trigger-missed-dose/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['medication'], 'Efavirenz')
        self.assertEqual(data['level1_escalations'], 1)

        dose = DoseLog.objects.get(pk=data['dose_id'])
        self.assertEqual(dose.status, 'missed')
        self.assertTrue(Escalation.objects.filter(dose_log=dose, level=1).exists())

    def test_requires_post(self):
        self.client.force_login(self.patient)
        resp = self.client.get('/demo/trigger-missed-dose/')
        self.assertEqual(resp.status_code, 405)
        self.assertEqual(DoseLog.objects.count(), 0)

    def test_requires_login(self):
        resp = self.client.post('/demo/trigger-missed-dose/')
        self.assertNotEqual(resp.status_code, 200)

    def test_rejects_non_patient_roles(self):
        self.client.force_login(self.caregiver)
        resp = self.client.post('/demo/trigger-missed-dose/')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(DoseLog.objects.count(), 0)

    def test_no_active_schedule_returns_clear_error(self):
        self.schedule.is_active = False
        self.schedule.save()
        self.client.force_login(self.patient)
        resp = self.client.post('/demo/trigger-missed-dose/')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])
        self.assertIn('No active medication schedule', resp.json()['error'])

    def test_can_be_triggered_multiple_times(self):
        """Repeatable for multiple demo runs/rehearsals -- each click adds a new dose."""
        self.client.force_login(self.patient)
        self.client.post('/demo/trigger-missed-dose/')
        self.client.post('/demo/trigger-missed-dose/')
        self.assertEqual(DoseLog.objects.count(), 2)
        self.assertEqual(Escalation.objects.count(), 2)

    def test_resulting_escalation_visible_on_caregiver_poll(self):
        """Confirms this wires into the live-polling dashboard from earlier."""
        self.client.force_login(self.patient)
        self.client.post('/demo/trigger-missed-dose/')

        self.client.force_login(self.caregiver)
        resp = self.client.get('/notifications/escalations/poll/')
        data = resp.json()['escalations']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['medication'], 'Efavirenz')

    def test_dashboard_renders_demo_button_for_patient(self):
        self.client.force_login(self.patient)
        resp = self.client.get('/dashboard/')
        self.assertContains(resp, 'Simulate Missed Dose')
        self.assertContains(resp, 'triggerDemoMissedDose')
