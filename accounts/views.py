from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import User, CaregiverPatient
from core.models import Clinic

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.POST.get('next', 'dashboard'))
        messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html', {'next': request.GET.get('next', '')})

def logout_view(request):
    logout(request)
    return redirect('login')

def register_view(request):
    clinics = Clinic.objects.all()
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', 'patient')
        phone = request.POST.get('phone_number', '').strip()
        channel = request.POST.get('channel_preference', 'sms')
        language = request.POST.get('language_preference', 'en')
        clinic_id = request.POST.get('clinic')
        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'That username is already taken.')
        elif len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        else:
            user = User.objects.create_user(
                username=username, password=password,
                first_name=first_name, last_name=last_name,
                role=role, phone_number=phone,
                channel_preference=channel, language_preference=language,
            )
            if clinic_id:
                try:
                    user.clinic = Clinic.objects.get(pk=clinic_id)
                    user.save()
                except Clinic.DoesNotExist:
                    pass
            login(request, user)
            messages.success(request, f'Welcome to Pill Pal, {first_name or username}!')
            return redirect('dashboard')
    return render(request, 'registration/register.html', {'clinics': clinics})

@login_required
def settings_view(request):
    user = request.user
    clinics = Clinic.objects.all()
    notif_fields = [
        ('notif_reminders', 'Medication Reminders', user.notif_reminders),
        ('notif_refill', 'Refill Reminders', user.notif_refill),
        ('notif_broadcasts', 'Clinic Broadcasts', user.notif_broadcasts),
        ('notif_weekly', 'Weekly Summary', user.notif_weekly),
        ('notif_caregiver_alerts', 'Caregiver Alerts', user.notif_caregiver_alerts),
    ]
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name = request.POST.get('last_name', user.last_name).strip()
        user.phone_number = request.POST.get('phone_number', user.phone_number).strip()
        user.language_preference = request.POST.get('language_preference', user.language_preference)
        user.channel_preference = request.POST.get('channel_preference', user.channel_preference)
        user.notif_reminders = 'notif_reminders' in request.POST
        user.notif_refill = 'notif_refill' in request.POST
        user.notif_broadcasts = 'notif_broadcasts' in request.POST
        user.notif_weekly = 'notif_weekly' in request.POST
        user.notif_caregiver_alerts = 'notif_caregiver_alerts' in request.POST
        clinic_id = request.POST.get('clinic')
        if clinic_id:
            try:
                user.clinic = Clinic.objects.get(pk=clinic_id)
            except Clinic.DoesNotExist:
                pass
        elif clinic_id == '':
            user.clinic = None
        user.save()
        messages.success(request, 'Settings saved successfully.')
        return redirect('settings')
    return render(request, 'core/settings.html', {
        'clinics': clinics, 'notif_fields': notif_fields,
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        old_pw = request.POST.get('old_password', '')
        new_pw = request.POST.get('new_password', '')
        confirm_pw = request.POST.get('confirm_password', '')
        if not request.user.check_password(old_pw):
            messages.error(request, 'Current password is incorrect.')
        elif len(new_pw) < 6:
            messages.error(request, 'New password must be at least 6 characters.')
        elif new_pw != confirm_pw:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_pw)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('settings')
    return render(request, 'core/change_password.html')

@login_required
def caregiver_management(request):
    """Patient manages their linked caregivers."""
    links = CaregiverPatient.objects.filter(patient=request.user).select_related('caregiver')
    if request.method == 'POST':
        action = request.POST.get('action')
        link_id = request.POST.get('link_id')
        phone = request.POST.get('caregiver_phone', '').strip()

        if action == 'invite' and phone:
            try:
                caregiver = User.objects.get(phone_number=phone, role='caregiver')
                _, created = CaregiverPatient.objects.get_or_create(
                    caregiver=caregiver, patient=request.user,
                    defaults={'approved': True}
                )
                if created:
                    messages.success(request, f'{caregiver.get_full_name()} linked as your caregiver.')
                else:
                    messages.info(request, 'That caregiver is already linked.')
            except User.DoesNotExist:
                messages.error(request, 'No caregiver account found with that phone number.')

        elif action == 'remove' and link_id:
            link = get_object_or_404(CaregiverPatient, pk=link_id, patient=request.user)
            name = link.caregiver.get_full_name()
            link.delete()
            messages.success(request, f'{name} has been removed as your caregiver.')

    links = CaregiverPatient.objects.filter(patient=request.user).select_related('caregiver')
    return render(request, 'core/caregiver_management.html', {'links': links})

@login_required
def profile_view(request):
    return render(request, 'core/profile.html', {'profile_user': request.user})

@login_required
def api_unread_notifications(request):
    from notifications.models import Notification
    count = Notification.objects.filter(recipient=request.user, read=False).count()
    return JsonResponse({'count': count})
