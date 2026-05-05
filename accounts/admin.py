from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CaregiverPatient

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'phone_number', 'channel_preference', 'clinic']
    list_filter = ['role', 'channel_preference', 'language_preference']
    fieldsets = UserAdmin.fieldsets + (
        ('Pill Pal', {'fields': ('role', 'phone_number', 'date_of_birth', 'language_preference', 'channel_preference', 'clinic')}),
        ('Notifications', {'fields': ('notif_reminders', 'notif_refill', 'notif_broadcasts', 'notif_weekly', 'notif_caregiver_alerts')}),
    )

@admin.register(CaregiverPatient)
class CaregiverPatientAdmin(admin.ModelAdmin):
    list_display = ['caregiver', 'patient', 'approved', 'linked_date']
