from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, date
from medications.models import DoseLog, MedicationSchedule
import json

@login_required
def reports_view(request):
    user = request.user
    thirty_ago = timezone.now() - timedelta(days=30)
    logs = DoseLog.objects.filter(patient=user, scheduled_datetime__gte=thirty_ago)
    total = logs.count()
    confirmed = logs.filter(status='confirmed').count()
    missed = logs.filter(status='missed').count()
    adherence_pct = round((confirmed / total * 100) if total else 0)

    # Per-medication breakdown
    schedules = MedicationSchedule.objects.filter(patient=user, is_active=True).select_related('medication')
    med_stats = []
    for s in schedules:
        s_logs = logs.filter(schedule=s)
        t = s_logs.count()
        c = s_logs.filter(status='confirmed').count()
        pct = round((c / t * 100) if t else 0)
        trend = 'improving' if pct >= 85 else ('at_risk' if pct < 75 else 'stable')
        med_stats.append({'schedule': s, 'total': t, 'confirmed': c, 'missed': t - c, 'pct': pct, 'trend': trend})

    # Streak
    streak = 0
    check_date = date.today()
    while True:
        day_logs = DoseLog.objects.filter(patient=user, scheduled_datetime__date=check_date)
        if day_logs.exists() and not day_logs.filter(status='missed').exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # Daily data for chart (last 30 days)
    daily_data = []
    for i in range(29, -1, -1):
        d = date.today() - timedelta(days=i)
        day_logs = DoseLog.objects.filter(patient=user, scheduled_datetime__date=d)
        t = day_logs.count()
        c = day_logs.filter(status='confirmed').count()
        daily_data.append({'date': d.strftime('%d %b'), 'pct': round((c/t*100) if t else 0)})

    context = {
        'total': total, 'confirmed': confirmed, 'missed': missed,
        'adherence_pct': adherence_pct, 'med_stats': med_stats,
        'streak': streak, 'daily_data': json.dumps(daily_data),
    }
    return render(request, 'core/reports.html', context)
