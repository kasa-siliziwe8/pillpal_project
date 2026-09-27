from .models import Notification


class SimulatedProvider:
    """
    Pretend SMS/voice sender. Doesn't actually send anything;
    it just returns success so the rest of the app can be built
    and tested without a real SMS/voice account.
    """
    def send(self, recipient, message, channel):
        print(f"[SIMULATED {channel.upper()}] to {recipient}: {message}")
        return {"status": "sent"}


def send_notification(dose_log, channel=None, notification_type='reminder', message=None):
    """
    Creates a Notification record and 'sends' it via the simulated provider.
    """
    patient = dose_log.patient
    medication = dose_log.schedule.medication
    channel = channel or getattr(patient, 'preferred_channel', 'sms')
    message = message or f"Reminder: take {medication.generic_name} ({dose_log.schedule.dosage})"

    provider = SimulatedProvider()
    result = provider.send(recipient=patient, message=message, channel=channel)

    notification = Notification.objects.create(
        recipient=patient,
        channel=channel,
        notification_type=notification_type,
        status='sent' if result['status'] == 'sent' else 'failed',
        dose_log=dose_log,
    )
    return notification