"""
python manage.py check_escalations              # run once
python manage.py check_escalations --dry-run    # show what would happen, write nothing
python manage.py check_escalations --loop       # keep running every 60s (demo / no cron)
python manage.py check_escalations --loop --interval 30

Pairs with generate_daily_doses: that command creates 'pending' DoseLog rows,
this one turns overdue pending doses into 'missed' and escalates them.
It only depends on the DoseLog fields, so it works with any version of the generator.

Cron example (every 10 minutes):
    */10 * * * * cd /path/to/pillpal_project && python manage.py check_escalations
"""
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.escalation import run_escalation_check


class Command(BaseCommand):
    help = 'Mark overdue doses as missed and send caregiver / clinic escalations.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would be escalated without writing anything.')
        parser.add_argument('--loop', action='store_true',
                            help='Run repeatedly until interrupted (Ctrl+C). Useful without cron.')
        parser.add_argument('--interval', type=int, default=60,
                            help='Seconds between runs in --loop mode (default 60).')

    def handle(self, *args, **options):
        dry = options['dry_run']

        if not options['loop']:
            self._run_once(dry)
            return

        self.stdout.write(f"Escalation loop started (every {options['interval']}s). Ctrl+C to stop.")
        try:
            while True:
                self._run_once(dry)
                time.sleep(options['interval'])
        except KeyboardInterrupt:
            self.stdout.write('\nStopped.')

    def _run_once(self, dry):
        result = run_escalation_check(dry_run=dry)
        stamp = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
        prefix = '[DRY RUN] ' if dry else ''
        self.stdout.write(
            f"{prefix}{stamp}  marked missed: {result.marked_missed} | "
            f"L1 caregiver: {result.level1_created} | "
            f"L2 clinic: {result.level2_created} | "
            f"no recipient: {result.skipped_no_recipient}"
        )
        if result.total_escalations:
            style = self.style.WARNING if dry else self.style.SUCCESS
            self.stdout.write(style(f"  {result.total_escalations} escalation(s) "
                                    f"{'would be ' if dry else ''}created."))
