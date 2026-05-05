from django.contrib import admin
from .models import Clinic

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ['name', 'province', 'district']
