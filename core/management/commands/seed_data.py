from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date, time
import random
from core.models import Clinic
from accounts.models import User, CaregiverPatient
from medications.models import Medication, MedicationSchedule, DoseLog

class Command(BaseCommand):
    help = 'Seed demo data for Pill Pal'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding...')

        # Clinic
        clinic, _ = Clinic.objects.get_or_create(
            name='Galeshewe Clinic',
            defaults={'province': 'Northern Cape', 'district': 'Sol Plaatje', 'contact_email': 'info@galeshewe.gov.za'}
        )

        # Medications
        meds_data = [
            {'generic_name': 'Tenofovir', 'brand_name': 'Tenofovir Disoproxil Fumarate (TDF)',
             'drug_class': 'Antiretroviral · NRTI', 'pill_color': '#2A9090,#1A6B6B',
             'description': 'Tenofovir is an antiretroviral medication used to treat HIV infection. It works by blocking the enzyme HIV needs to copy itself, slowing virus multiplication. Take every day at the same time.',
             'how_to_take': 'Take 1 tablet (300mg) once daily at the same time every day. Can be taken with or without food.',
             'side_effects': 'Nausea or stomach upset\nHeadache\nDizziness\nTiredness or weakness\nChanges in body fat distribution',
             'missed_dose_instructions': 'Take as soon as you remember — unless almost time for next dose. Never double up.'},
            {'generic_name': 'Lamivudine', 'brand_name': 'Lamivudine 3TC',
             'drug_class': 'Antiretroviral · NRTI', 'pill_color': '#C0572B,#E8785A',
             'description': 'Lamivudine treats HIV infection and works with other medicines to prevent the virus from multiplying.',
             'how_to_take': 'Take 1 tablet (150mg) twice daily — morning and evening at the same times each day.',
             'side_effects': 'Headache\nNausea\nTiredness\nDifficulty sleeping',
             'missed_dose_instructions': 'Take as soon as possible. If almost time for next dose, skip. Do not double up.'},
            {'generic_name': 'Efavirenz', 'brand_name': 'Efavirenz EFV',
             'drug_class': 'Antiretroviral · NNRTI', 'pill_color': '#6B3FA0,#9B59B6',
             'description': 'Efavirenz blocks a key enzyme that HIV needs to reproduce. Part of combination HIV therapy.',
             'how_to_take': 'Take 1 tablet (600mg) at bedtime on an empty stomach to reduce dizziness side effects.',
             'side_effects': 'Dizziness especially in first 2-4 weeks\nVivid dreams or nightmares\nRash\nMood changes',
             'missed_dose_instructions': 'Take as soon as you remember. If nearly time for next dose, skip and continue. Never double dose.'},
            {'generic_name': 'Metformin', 'brand_name': 'Metformin Hydrochloride',
             'drug_class': 'Antidiabetic · Biguanide', 'pill_color': '#D4952A,#F0C040',
             'description': 'Metformin controls blood sugar levels in Type 2 diabetes by reducing glucose production in the liver and improving insulin sensitivity.',
             'how_to_take': 'Take 1 tablet (500mg) twice daily with breakfast and with dinner.',
             'side_effects': 'Nausea or diarrhoea especially when starting\nStomach cramps\nLoss of appetite',
             'missed_dose_instructions': 'Take with your next meal. Never take two tablets at once.'},
        ]
        meds = []
        for md in meds_data:
            m, _ = Medication.objects.get_or_create(generic_name=md['generic_name'], defaults=md)
            meds.append(m)

        # Patient
        patient, _ = User.objects.get_or_create(
            username='thabo',
            defaults={
                'first_name': 'Thabo', 'last_name': 'Dlamini',
                'role': 'patient', 'phone_number': '+27724567890',
                'channel_preference': 'sms', 'language_preference': 'en',
                'clinic': clinic,
            }
        )
        patient.set_password('demo1234')
        patient.save()

        # Caregiver
        caregiver, _ = User.objects.get_or_create(
            username='nomsa',
            defaults={
                'first_name': 'Nomsa', 'last_name': 'Mokoena',
                'role': 'caregiver', 'phone_number': '+27831234567',
            }
        )
        caregiver.set_password('demo1234')
        caregiver.save()

        CaregiverPatient.objects.get_or_create(caregiver=caregiver, patient=patient, defaults={'approved': True})

        # Clinic admin
        admin_user, _ = User.objects.get_or_create(
            username='sister_pk',
            defaults={
                'first_name': 'Precious', 'last_name': 'Khumalo',
                'role': 'clinic_admin', 'clinic': clinic,
            }
        )
        admin_user.set_password('demo1234')
        admin_user.save()

        # Schedules
        if not MedicationSchedule.objects.filter(patient=patient).exists():
            sched1 = MedicationSchedule.objects.create(
                patient=patient, medication=meds[0], dosage='300mg',
                frequency='once_daily', scheduled_time_1=time(8, 0),
                start_date=date.today() - timedelta(days=30), supply_days=30,
            )
            sched2 = MedicationSchedule.objects.create(
                patient=patient, medication=meds[1], dosage='150mg',
                frequency='twice_daily', scheduled_time_1=time(8, 0), scheduled_time_2=time(20, 0),
                start_date=date.today() - timedelta(days=30), supply_days=30,
            )
            sched3 = MedicationSchedule.objects.create(
                patient=patient, medication=meds[2], dosage='600mg',
                frequency='once_daily', scheduled_time_1=time(20, 0),
                special_instructions='Take on empty stomach at bedtime.',
                start_date=date.today() - timedelta(days=30), supply_days=30,
            )

            # Seed 30 days of dose logs with ~85% adherence
            for i in range(30, 0, -1):
                d = date.today() - timedelta(days=i)
                for sched in [sched1, sched2, sched3]:
                    times = [sched.scheduled_time_1]
                    if sched.scheduled_time_2:
                        times.append(sched.scheduled_time_2)
                    for t_slot in times:
                        scheduled_dt = timezone.make_aware(
                            timezone.datetime.combine(d, t_slot)
                        )
                        confirmed = random.random() < 0.85
                        log = DoseLog.objects.create(
                            schedule=sched, patient=patient,
                            scheduled_datetime=scheduled_dt,
                            status='confirmed' if confirmed else 'missed',
                        )
                        if confirmed:
                            log.confirmed_at = scheduled_dt + timedelta(minutes=random.randint(2, 45))
                            log.confirmation_method = random.choice(['sms', 'app', 'voice'])
                            log.save()


        # Seed notifications for thabo
        from notifications.models import Notification as Notif
        notif_data = [
            ('reminder', 'sms', 'delivered', f'PILL PAL: {patient.first_name}, time to take your Tenofovir 300mg. Reply 1 to confirm.', 1),
            ('confirmation', 'sms', 'delivered', f'PILL PAL: ✓ Thank you {patient.first_name}! Tenofovir confirmed at 08:02. Keep it up!', 1),
            ('reminder', 'sms', 'delivered', 'PILL PAL: Time to take your Efavirenz 600mg. Take at bedtime on empty stomach. Reply 1 to confirm.', 2),
            ('escalation', 'sms', 'delivered', 'PILL PAL ALERT (Caregiver): Thabo may have missed their 20:00 Efavirenz dose. Please check in with them.', 3),
            ('refill', 'sms', 'delivered', 'PILL PAL REFILL ALERT: Your Tenofovir supply will run out in ~5 days. Visit Galeshewe Clinic.', 5),
            ('broadcast', 'sms', 'delivered', 'PILL PAL — Galeshewe Clinic: Pharmacy closed on 14 June public holiday. Collect before 13 June.', 7),
        ]
        if not Notif.objects.filter(recipient=patient).exists():
            for ntype, channel, status, msg, days_ago in notif_data:
                Notif.objects.create(
                    recipient=patient,
                    notification_type=ntype,
                    channel=channel,
                    status=status,
                    message=msg,
                    created_at=timezone.now() - timedelta(days=days_ago),
                    read=(days_ago > 2),
                )
        self.stdout.write('  + Notifications seeded')
        self.stdout.write(self.style.SUCCESS('✅ Seed data created!'))
        self.stdout.write('Login: thabo / demo1234 (patient)')
        self.stdout.write('Login: nomsa / demo1234 (caregiver)')
        self.stdout.write('Login: sister_pk / demo1234 (clinic admin)')
