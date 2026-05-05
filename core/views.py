from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, date
from medications.models import MedicationSchedule, DoseLog, Medication
from accounts.models import User, CaregiverPatient
import json

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/landing.html')

def handler404(request, exception):
    return render(request, 'core/404.html', status=404)

def handler500(request):
    return render(request, 'core/500.html', status=500)

@login_required
def dashboard(request):
    user = request.user
    context = {'user': user}

    if user.role == 'patient':
        schedules = MedicationSchedule.objects.filter(patient=user, is_active=True).select_related('medication')
        today = date.today()
        today_logs = DoseLog.objects.filter(patient=user, scheduled_datetime__date=today).select_related('schedule__medication')
        confirmed_today = today_logs.filter(status='confirmed').count()
        total_today = today_logs.count() or schedules.count()

        thirty_ago = timezone.now() - timedelta(days=30)
        all_logs = DoseLog.objects.filter(patient=user, scheduled_datetime__gte=thirty_ago)
        total = all_logs.count()
        confirmed = all_logs.filter(status='confirmed').count()
        missed = total - confirmed
        adherence_pct = round((confirmed / total * 100) if total else 0)

        # Streak
        streak = 0
        check = today
        while True:
            day_logs = DoseLog.objects.filter(patient=user, scheduled_datetime__date=check)
            if day_logs.exists() and not day_logs.filter(status='missed').exists():
                streak += 1
                check -= timedelta(days=1)
            else:
                break

        cal_days = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_logs = DoseLog.objects.filter(patient=user, scheduled_datetime__date=d)
            if i == 0:
                status = 'today'
            elif day_logs.filter(status='missed').exists():
                status = 'missed'
            elif day_logs.filter(status='confirmed').exists():
                status = 'confirmed'
            else:
                status = 'upcoming'
            cal_days.append({'date': d, 'status': status, 'day_abbr': d.strftime('%a')[0]})

        # Next pending dose
        next_dose = schedules.first() if schedules.exists() else None
        caregiver_links = CaregiverPatient.objects.filter(patient=user, approved=True).select_related('caregiver')

        context.update({
            'schedules': schedules,
            'today_logs': today_logs,
            'confirmed_today': confirmed_today,
            'total_today': total_today,
            'adherence_pct': adherence_pct,
            'confirmed_30': confirmed,
            'missed_30': missed,
            'cal_days': cal_days,
            'streak': streak,
            'next_dose': next_dose,
            'caregiver_links': caregiver_links,
        })

    elif user.role == 'caregiver':
        links = CaregiverPatient.objects.filter(caregiver=user, approved=True).select_related('patient')
        patient_data = []
        for link in links:
            p = link.patient
            seven_ago = timezone.now() - timedelta(days=7)
            logs = DoseLog.objects.filter(patient=p, scheduled_datetime__gte=seven_ago)
            total = logs.count()
            confirmed = logs.filter(status='confirmed').count()
            pct = round((confirmed / total * 100) if total else 0)
            missed_recent = logs.filter(status='missed').order_by('-scheduled_datetime').first()
            last_confirmed = logs.filter(status='confirmed').order_by('-confirmed_at').first()
            patient_data.append({
                'patient': p, 'pct': pct,
                'missed_recent': missed_recent,
                'last_confirmed': last_confirmed,
                'link': link,
            })
        context['patient_data'] = patient_data

    elif user.role == 'clinic_admin':
        clinic = user.clinic
        if clinic:
            patients = User.objects.filter(clinic=clinic, role='patient')
            total_patients = patients.count()
            thirty_ago = timezone.now() - timedelta(days=30)
            today = date.today()
            all_logs = DoseLog.objects.filter(patient__in=patients, scheduled_datetime__gte=thirty_ago)
            total_l = all_logs.count()
            confirmed_l = all_logs.filter(status='confirmed').count()
            avg_adherence = round((confirmed_l / total_l * 100) if total_l else 0)

            today_logs = DoseLog.objects.filter(patient__in=patients, scheduled_datetime__date=today)
            doses_today_confirmed = today_logs.filter(status='confirmed').count()
            doses_today_total = today_logs.count()

            at_risk = []
            for p in patients:
                logs = DoseLog.objects.filter(patient=p, scheduled_datetime__gte=thirty_ago)
                t = logs.count()
                c = logs.filter(status='confirmed').count()
                pct = round((c / t * 100) if t else 0)
                if pct < 80:
                    last_log = logs.filter(status='confirmed').order_by('-confirmed_at').first()
                    at_risk.append({'patient': p, 'pct': pct, 'missed': t - c, 'last_confirmed': last_log})
            at_risk.sort(key=lambda x: x['pct'])

            context.update({
                'clinic': clinic,
                'total_patients': total_patients,
                'avg_adherence': avg_adherence,
                'at_risk': at_risk,
                'at_risk_count': len(at_risk),
                'doses_today_confirmed': doses_today_confirmed,
                'doses_today_total': doses_today_total,
            })

    return render(request, 'core/dashboard.html', context)

@login_required
def sms_simulator(request):
    commands = [
        ('1', 'Confirm dose taken'),
        ('INFO [drug name]', 'Get medication information'),
        ('REFILL', 'Check refill status'),
        ('HELP', 'Get full command list'),
        ('STOP', 'Pause reminders (not recommended)'),
        ('START', 'Resume reminders'),
    ]
    return render(request, 'core/sms_simulator.html', {'commands': commands})

@login_required
def voice_channel(request):
    steps = [
        ('1', 'Automated call at scheduled time', 'Pill Pal calls your number at medication time — works on any phone, no data needed.'),
        ('2', 'Listen to your reminder', 'A friendly voice reads your medication name, dosage, and instructions in your language.'),
        ('3', 'Press 1 to confirm', 'Press 1 to confirm the dose. Press 2 to snooze 30 minutes. Press 0 for help.'),
        ('4', 'Missed call confirmation', 'Call the Pill Pal number back and hang up to confirm — free, no data required.'),
    ]
    return render(request, 'core/voice_channel.html', {'steps': steps})

@login_required
def api_confirm_dose(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            data = {}
        log_id = data.get('log_id')
        method = data.get('method', 'app')
        if log_id:
            try:
                log = DoseLog.objects.get(pk=log_id, patient=request.user)
                log.status = 'confirmed'
                log.confirmed_at = timezone.now()
                log.confirmation_method = method
                log.save()
                return JsonResponse({'success': True, 'message': 'Dose confirmed!'})
            except DoseLog.DoesNotExist:
                pass
        # Fallback: confirm next pending
        log = DoseLog.objects.filter(patient=request.user, status='pending').order_by('scheduled_datetime').first()
        if log:
            log.status = 'confirmed'
            log.confirmed_at = timezone.now()
            log.confirmation_method = method
            log.save()
        return JsonResponse({'success': True, 'message': 'Dose confirmed!'})
    return JsonResponse({'success': False})

@login_required
def api_sms_respond(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'reply': 'PILL PAL: Could not process your message.'})
        message = data.get('message', '').strip().upper()
        user = request.user
        name = user.first_name or user.username
        responses = {
            '1': f'PILL PAL: ✓ Thank you {name}! Dose confirmed at {timezone.localtime().strftime("%H:%M")}. Keep it up! 💪',
            'YES': f'PILL PAL: ✓ Dose confirmed, {name}! Well done.',
            'HELP': 'PILL PAL COMMANDS:\n1 — Confirm dose\nINFO [drug] — Medication info\nREFILL — Refill status\nSTOP — Pause reminders\nSTART — Resume reminders\nEmergencies: call 10177',
            'REFILL': 'PILL PAL: Your next refill is due soon. Please visit your clinic and bring your yellow patient card. Mon–Fri 08:00–16:30.',
            'STOP': f'PILL PAL: Reminders paused for 24 hours, {name}. Reply START to resume. Important: staying on your medication is vital for your health.',
            'START': f'PILL PAL: Reminders resumed, {name}! Great decision — consistent treatment leads to better health outcomes.',
        }
        if message in responses:
            reply = responses[message]
        elif message.startswith('INFO '):
            drug = message[5:].strip()
            med = Medication.objects.filter(generic_name__icontains=drug).first()
            if med:
                reply = (f'PILL PAL INFO — {med.generic_name}:\n'
                         f'{med.description[:180]}\n'
                         f'Side effects: {", ".join(med.side_effects_list()[:3])}.\n'
                         f'Missed dose: {med.missed_dose_instructions[:80]}\nReply HELP for commands.')
            else:
                reply = f'PILL PAL: No info found for "{message[5:]}". Check spelling or ask your clinic. Reply HELP for commands.'
        else:
            reply = f'PILL PAL: Message not recognised. Reply HELP for a list of commands, or visit your clinic for assistance.'
        return JsonResponse({'reply': reply})
    return JsonResponse({'reply': ''})
