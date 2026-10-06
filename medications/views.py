from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import date
from .models import Medication, MedicationSchedule, DoseLog
from notifications.escalation import resolve_for_dose
import json

@login_required
def medication_list(request):
    schedules = MedicationSchedule.objects.filter(patient=request.user, is_active=True).select_related('medication')
    all_meds = Medication.objects.all()
    selected_id = request.GET.get('med')
    selected = None
    schedule = None
    if selected_id:
        selected = get_object_or_404(Medication, pk=selected_id)
        schedule = MedicationSchedule.objects.filter(patient=request.user, medication=selected, is_active=True).first()
    elif schedules.exists():
        schedule = schedules.first()
        selected = schedule.medication
    return render(request, 'core/medications.html', {
        'schedules': schedules, 'all_meds': all_meds,
        'selected': selected, 'schedule': schedule,
    })

@login_required
def medication_detail(request, pk):
    med = get_object_or_404(Medication, pk=pk)
    schedules = MedicationSchedule.objects.filter(patient=request.user, is_active=True).select_related('medication')
    schedule = MedicationSchedule.objects.filter(patient=request.user, medication=med, is_active=True).first()
    return render(request, 'core/medications.html', {
        'schedules': schedules, 'selected': med, 'schedule': schedule,
    })

@login_required
def schedule_list(request):
    """Full schedule management for patient."""
    schedules = MedicationSchedule.objects.filter(patient=request.user).select_related('medication').order_by('-is_active', 'scheduled_time_1')
    all_meds = Medication.objects.all()
    return render(request, 'core/schedule_list.html', {
        'schedules': schedules, 'all_meds': all_meds,
    })

@login_required
def schedule_add(request):
    if request.method == 'POST':
        med_id = request.POST.get('medication')
        dosage = request.POST.get('dosage', '')
        frequency = request.POST.get('frequency', 'once_daily')
        time1 = request.POST.get('scheduled_time_1', '08:00')
        time2 = request.POST.get('scheduled_time_2') or None
        instructions = request.POST.get('special_instructions', '')
        supply = int(request.POST.get('supply_days', 30))
        try:
            med = Medication.objects.get(pk=med_id)
            MedicationSchedule.objects.create(
                patient=request.user, medication=med, dosage=dosage,
                frequency=frequency, scheduled_time_1=time1,
                scheduled_time_2=time2, special_instructions=instructions,
                start_date=date.today(), supply_days=supply,
            )
            messages.success(request, f'{med.generic_name} schedule added successfully.')
        except Exception as e:
            messages.error(request, f'Error adding schedule: {e}')
        return redirect('schedule_list')
    return redirect('schedule_list')

@login_required
def schedule_toggle(request, pk):
    schedule = get_object_or_404(MedicationSchedule, pk=pk, patient=request.user)
    schedule.is_active = not schedule.is_active
    schedule.save()
    status = 'activated' if schedule.is_active else 'paused'
    messages.success(request, f'{schedule.medication.generic_name} schedule {status}.')
    return redirect('schedule_list')

@login_required
def schedule_delete(request, pk):
    schedule = get_object_or_404(MedicationSchedule, pk=pk, patient=request.user)
    name = schedule.medication.generic_name
    schedule.delete()
    messages.success(request, f'{name} schedule removed.')
    return redirect('schedule_list')

@login_required
def dose_history(request):
    """Paginated dose history for a patient."""
    logs = DoseLog.objects.filter(patient=request.user).select_related('schedule__medication').order_by('-scheduled_datetime')
    status_filter = request.GET.get('status', '')
    if status_filter:
        logs = logs.filter(status=status_filter)
    return render(request, 'core/dose_history.html', {
        'logs': logs[:60],
        'status_filter': status_filter,
    })

@login_required
def api_dose_confirm(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Bad request'})
        log_id = data.get('log_id')
        method = data.get('method', 'app')
        if log_id:
            try:
                log = DoseLog.objects.get(pk=log_id, patient=request.user)
                log.status = 'confirmed'
                log.confirmed_at = timezone.now()
                log.confirmation_method = method
                log.save()
                resolve_for_dose(log)
                return JsonResponse({'success': True, 'message': 'Dose confirmed!'})
            except DoseLog.DoesNotExist:
                pass
        # Confirm latest pending dose
        log = DoseLog.objects.filter(patient=request.user, status='pending').order_by('scheduled_datetime').first()
        if log:
            log.status = 'confirmed'
            log.confirmed_at = timezone.now()
            log.confirmation_method = method
            log.save()
            resolve_for_dose(log)
            return JsonResponse({'success': True, 'message': 'Dose confirmed!'})
        return JsonResponse({'success': True, 'message': 'Confirmed!'})
    return JsonResponse({'success': False})
