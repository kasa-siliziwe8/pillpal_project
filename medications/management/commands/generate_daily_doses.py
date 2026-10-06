"""
python manage.py generate_daily_doses                      # generate for today
python manage.py generate_daily_doses --date 2026-10-10     # generate for one date
python manage.py generate_daily_doses --backfill 7          # today and the 6 days before it

Pairs with check_escalations (Siliziwe's command): this creates 'pending'
DoseLog rows, check_escalations later marks overdue ones 'missed' and sends
alerts. Run this before check_escalations each day.

Cron example (once a day, just after midnight local time):
    5 0 * * * cd /path/to/pillpal_project && python manage.py generate_daily_doses
"""
import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from medications.dose_generation import generate_doses_for_date, generate_doses_for_range


class Command(BaseCommand):
    help = "Generate today's DoseLog rows from active MedicationSchedules."

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, default=None,
                            help='Generate for a specific date (YYYY-MM-DD). Defaults to today.')
        parser.add_argument('--backfill', type=int, default=None,
                            help='Generate for the last N days (including today), for demos/catch-up.')

    def handle(self, *args, **options):
        if options['backfill']:
            end = timezone.localdate()
            start = end - dt.timedelta(days=options['backfill'] - 1)
            result = generate_doses_for_range(start, end)
            self.stdout.write(f"Backfilled {start} to {end}.")
        else:
            target_date = timezone.localdate()
            if options['date']:
                try:
                    target_date = dt.date.fromisoformat(options['date'])
                except ValueError:
                    raise CommandError('--date must be YYYY-MM-DD')
            result = generate_doses_for_date(target_date)
            self.stdout.write(f"Generated doses for {target_date}.")

        self.stdout.write(
            f"  schedules processed: {result.schedules_processed} | "
            f"skipped (inactive/out of date range): {result.schedules_skipped_inactive_or_dated}"
        )
        self.stdout.write(self.style.SUCCESS(
            f"  dose logs created: {result.created} | already existed: {result.already_existed}"
        ))
        if result.incomplete_frequency_schedules:
            self.stdout.write(self.style.WARNING(
                f"  {len(result.incomplete_frequency_schedules)} schedule(s) use a frequency "
                f"('three_daily' or 'weekly') the model can't fully represent yet "
                f"(no 3rd time slot, no weekday field) — see dose_generation.py docstring."
            ))
