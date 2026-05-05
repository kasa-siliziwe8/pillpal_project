from django.db import models
from django.conf import settings

class Medication(models.Model):
    generic_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)
    drug_class = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    how_to_take = models.TextField()
    side_effects = models.TextField()
    missed_dose_instructions = models.TextField()
    pill_color = models.CharField(max_length=50, default='#2A9090,#1A6B6B')

    def __str__(self):
        return self.generic_name

    def side_effects_list(self):
        return [s.strip() for s in self.side_effects.split('\n') if s.strip()]


class MedicationSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('three_daily', 'Three Times Daily'),
        ('weekly', 'Weekly'),
    ]
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='schedules')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='once_daily')
    scheduled_time_1 = models.TimeField()
    scheduled_time_2 = models.TimeField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    supply_days = models.IntegerField(default=30)

    def __str__(self):
        return f"{self.patient} — {self.medication} {self.dosage}"


class DoseLog(models.Model):
    STATUS_CHOICES = [('confirmed', 'Confirmed'), ('missed', 'Missed'), ('pending', 'Pending')]
    METHOD_CHOICES = [('sms', 'SMS'), ('voice', 'Voice'), ('app', 'App'), ('manual', 'Manual')]

    schedule = models.ForeignKey(MedicationSchedule, on_delete=models.CASCADE, related_name='dose_logs')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dose_logs')
    scheduled_datetime = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmation_method = models.CharField(max_length=10, choices=METHOD_CHOICES, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    escalated = models.BooleanField(default=False)

    class Meta:
        ordering = ['-scheduled_datetime']

    def __str__(self):
        return f"{self.patient} — {self.schedule.medication} — {self.status}"
