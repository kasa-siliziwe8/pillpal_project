from django.db import models
from django.conf import settings

class Notification(models.Model):
    CHANNEL_CHOICES = [
        ('sms', 'SMS'), ('voice', 'Voice'), ('app', 'App'), ('email', 'Email'),
    ]
    TYPE_CHOICES = [
        ('reminder', 'Medication Reminder'),
        ('escalation', 'Escalation Alert'),
        ('refill', 'Refill Reminder'),
        ('broadcast', 'Clinic Broadcast'),
        ('confirmation', 'Dose Confirmation'),
        ('info', 'Medication Info Response'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('sent', 'Sent'), ('delivered', 'Delivered'), ('failed', 'Failed'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    dose_log = models.ForeignKey(
        'medications.DoseLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient} | {self.notification_type} | {self.status}"


class Escalation(models.Model):
    dose_log = models.ForeignKey('medications.DoseLog', on_delete=models.CASCADE, related_name='escalations')
    level = models.IntegerField(default=1)
    alert_sent_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='received_escalations'
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Escalation L{self.level} — {self.dose_log}"
