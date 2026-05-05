from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('patient', 'Patient'),
        ('caregiver', 'Caregiver'),
        ('clinic_admin', 'Clinic Admin'),
        ('chw', 'Community Health Worker'),
    ]
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('voice', 'Voice Call'),
        ('app', 'App Push Notification'),
    ]
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('zu', 'isiZulu'),
        ('xh', 'isiXhosa'),
        ('st', 'Sesotho'),
        ('tn', 'Setswana'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    language_preference = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    channel_preference = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='sms')
    clinic = models.ForeignKey('core.Clinic', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    # Notification preferences
    notif_reminders = models.BooleanField(default=True)
    notif_refill = models.BooleanField(default=True)
    notif_broadcasts = models.BooleanField(default=True)
    notif_weekly = models.BooleanField(default=False)
    notif_caregiver_alerts = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def initials(self):
        parts = self.get_full_name().split()
        return ''.join(p[0] for p in parts[:2]).upper() if parts else self.username[:2].upper()


class CaregiverPatient(models.Model):
    caregiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='caregiving_links')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='caregiver_links')
    approved = models.BooleanField(default=False)
    linked_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('caregiver', 'patient')

    def __str__(self):
        return f"{self.caregiver} → {self.patient}"
