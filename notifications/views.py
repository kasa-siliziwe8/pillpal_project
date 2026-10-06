from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import Notification, Escalation
from .escalation import resolve_for_dose

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
