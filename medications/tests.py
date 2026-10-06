from datetime import date, time, timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from .models import Medication, MedicationSchedule, DoseLog
from .dose_generation import generate_doses_for_date, generate_doses_for_range


class DoseGenerationTestBase(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user('pat', role='patient')
        self.med = Medication.objects.create(
            generic_name='Tenofovir', description='d', how_to_take='h',
            side_effects='s', missed_dose_instructions='m')
        self.today = timezone.localdate()

    def make_schedule(self, **kwargs):
        defaults = dict(
            patient=self.patient, medication=self.med, dosage='300mg',
            frequency='once_daily', scheduled_time_1=time(8, 0),
            start_date=self.today - timedelta(days=30), is_active=True,
        )
        defaults.update(kwargs)
        return MedicationSchedule.objects.create(**defaults)


class GenerationTests(DoseGenerationTestBase):
    def test_once_daily_creates_one_dose(self):
        self.make_schedule(frequency='once_daily')
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 1)
        self.assertEqual(DoseLog.objects.count(), 1)
        log = DoseLog.objects.get()
        self.assertEqual(log.status, 'pending')
        self.assertEqual(log.patient, self.patient)
        self.assertEqual(timezone.localtime(log.scheduled_datetime).time(), time(8, 0))

    def test_twice_daily_creates_two_doses(self):
        self.make_schedule(frequency='twice_daily', scheduled_time_1=time(8, 0), scheduled_time_2=time(20, 0))
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 2)
        times = sorted(timezone.localtime(d).time() for d in DoseLog.objects.values_list('scheduled_datetime', flat=True))
        self.assertEqual(times, [time(8, 0), time(20, 0)])

    def test_idempotent_rerun_same_day(self):
        self.make_schedule(frequency='twice_daily', scheduled_time_1=time(8, 0), scheduled_time_2=time(20, 0))
        generate_doses_for_date(self.today)
        result2 = generate_doses_for_date(self.today)
        self.assertEqual(result2.created, 0)
        self.assertEqual(result2.already_existed, 2)
        self.assertEqual(DoseLog.objects.count(), 2)

    def test_inactive_schedule_skipped(self):
        self.make_schedule(is_active=False)
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 0)
        self.assertEqual(result.schedules_skipped_inactive_or_dated, 1)

    def test_not_yet_started_schedule_skipped(self):
        self.make_schedule(start_date=self.today + timedelta(days=5))
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 0)

    def test_ended_schedule_skipped(self):
        self.make_schedule(start_date=self.today - timedelta(days=30), end_date=self.today - timedelta(days=1))
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 0)

    def test_ends_today_still_generates(self):
        self.make_schedule(end_date=self.today)
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 1)

    def test_three_daily_flagged_as_incomplete(self):
        s = self.make_schedule(frequency='three_daily', scheduled_time_1=time(8, 0), scheduled_time_2=time(14, 0))
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 2)  # only 2 of 3 — model limitation
        self.assertIn((s.pk, 'three_daily'), result.incomplete_frequency_schedules)

    def test_weekly_flagged_as_incomplete(self):
        s = self.make_schedule(frequency='weekly')
        result = generate_doses_for_date(self.today)
        self.assertIn((s.pk, 'weekly'), result.incomplete_frequency_schedules)

    def test_multiple_patients_independent(self):
        p2 = User.objects.create_user('pat2', role='patient')
        self.make_schedule()
        self.make_schedule(patient=p2)
        result = generate_doses_for_date(self.today)
        self.assertEqual(result.created, 2)
        self.assertEqual(DoseLog.objects.filter(patient=p2).count(), 1)

    def test_timezone_correct(self):
        """8am scheduled_time_1 should store as 8am Africa/Johannesburg, not UTC."""
        self.make_schedule(scheduled_time_1=time(8, 0))
        generate_doses_for_date(self.today)
        log = DoseLog.objects.get()
        local = timezone.localtime(log.scheduled_datetime)
        self.assertEqual(local.hour, 8)
        self.assertEqual(local.date(), self.today)


class RangeGenerationTests(DoseGenerationTestBase):
    def test_backfill_range(self):
        self.make_schedule(start_date=self.today - timedelta(days=10))
        result = generate_doses_for_range(self.today - timedelta(days=2), self.today)
        self.assertEqual(result.created, 3)
        self.assertEqual(DoseLog.objects.count(), 3)

    def test_range_respects_start_date(self):
        self.make_schedule(start_date=self.today)
        result = generate_doses_for_range(self.today - timedelta(days=3), self.today)
        self.assertEqual(result.created, 1)  # only today, schedule hadn't started before


class CommandTests(DoseGenerationTestBase):
    def test_command_runs_for_today(self):
        self.make_schedule()
        out = StringIO()
        call_command('generate_daily_doses', stdout=out)
        self.assertIn('dose logs created: 1', out.getvalue())
        self.assertEqual(DoseLog.objects.count(), 1)

    def test_command_with_explicit_date(self):
        self.make_schedule()
        target = (self.today + timedelta(days=1)).isoformat()
        out = StringIO()
        call_command('generate_daily_doses', '--date', target, stdout=out)
        self.assertEqual(DoseLog.objects.count(), 1)

    def test_command_rejects_bad_date(self):
        with self.assertRaises(Exception):
            call_command('generate_daily_doses', '--date', 'not-a-date')

    def test_command_backfill(self):
        self.make_schedule(start_date=self.today - timedelta(days=10))
        out = StringIO()
        call_command('generate_daily_doses', '--backfill', '5', stdout=out)
        self.assertEqual(DoseLog.objects.count(), 5)

    def test_command_warns_on_incomplete_frequency(self):
        self.make_schedule(frequency='weekly')
        out = StringIO()
        call_command('generate_daily_doses', stdout=out)
        self.assertIn('frequency', out.getvalue().lower())
