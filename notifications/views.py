from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import Notification, Escalation
from .escalation import resolve_for_dose
from accounts.models import CaregiverPatient

@login_required
def notification_list(request):
    notifs = Notification.objects.filter(recipient=request.user)
    unread = notifs.filter(read=False).count()
    return render(request, 'core/notifications.html', {'notifications': notifs, 'unread': unread})

@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.read = True
    notif.save()
    return JsonResponse({'success': True})

@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    return JsonResponse({'success': True})

@login_required
def unread_count(request):
    count = Notification.objects.filter(recipient=request.user, read=False).count()
    return JsonResponse({'count': count})


@login_required
def resolve_escalation(request, pk):
    """
    Caregiver / CHW / clinic admin acknowledges an escalation from the dashboard.
    Only the person the alert was sent to (or a clinic admin/CHW at the patient's
    clinic) may resolve it.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    esc = get_object_or_404(Escalation.objects.select_related('dose_log__patient'), pk=pk)
    patient = esc.dose_log.patient
    user = request.user

    allowed = (
        esc.alert_sent_to_id == user.id
        or (user.role in ('chw', 'clinic_admin') and user.clinic_id and user.clinic_id == patient.clinic_id)
    )
    if not allowed:
        return JsonResponse({'success': False, 'message': 'Not allowed'}, status=403)

    if not esc.resolved:
        esc.resolved = True
        esc.resolved_at = timezone.now()
        esc.save(update_fields=['resolved', 'resolved_at'])
    return JsonResponse({'success': True, 'message': 'Escalation resolved'})


@login_required
def poll_escalations(request):
    """
    Lightweight JSON endpoint for dashboard polling (see dashboard.html /
    pillpal.js). Returns the open escalations currently relevant to the
    logged-in user, scoped the same way the dashboard view itself scopes
    them, so polling can never reveal an escalation the user couldn't
    already see by refreshing the page.

    Response shape:
        {"escalations": [
            {"id": 7, "patient_name": "Thabo Dlamini", "medication": "Tenofovir",
             "scheduled_at": "29 Sep 18:18", "level": 1}
        ]}
    """
    user = request.user

    if user.role == 'caregiver':
        patient_ids = CaregiverPatient.objects.filter(
            caregiver=user, approved=True
        ).values_list('patient_id', flat=True)
        qs = Escalation.objects.filter(
            dose_log__patient_id__in=patient_ids, alert_sent_to=user, resolved=False
        )
    elif user.role in ('chw', 'clinic_admin') and user.clinic_id:
        qs = Escalation.objects.filter(
            dose_log__patient__clinic_id=user.clinic_id, alert_sent_to=user, resolved=False
        )
    else:
        qs = Escalation.objects.none()

    qs = qs.select_related('dose_log__patient', 'dose_log__schedule__medication').order_by('-sent_at')

    data = [{
        'id': esc.pk,
        'patient_id': esc.dose_log.patient_id,
        'patient_name': esc.dose_log.patient.get_full_name() or esc.dose_log.patient.username,
        'medication': esc.dose_log.schedule.medication.generic_name,
        'scheduled_at': timezone.localtime(esc.dose_log.scheduled_datetime).strftime('%d %b %H:%M'),
        'level': esc.level,
    } for esc in qs]

    return JsonResponse({'escalations': data})
