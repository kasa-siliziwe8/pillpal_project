from django.contrib import admin
from .models import Medication, MedicationSchedule, DoseLog

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ['generic_name', 'brand_name', 'drug_class']
    search_fields = ['generic_name', 'brand_name']

@admin.register(MedicationSchedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medication', 'dosage', 'frequency', 'scheduled_time_1', 'is_active']
    list_filter = ['is_active', 'frequency']

@admin.register(DoseLog)
class DoseLogAdmin(admin.ModelAdmin):
    list_display = ['patient', 'schedule', 'scheduled_datetime', 'status', 'confirmation_method', 'escalated']
    list_filter = ['status', 'confirmation_method']
