from .models import Notification


def _model_has_field(name):
    return any(f.name == name for f in Notification._meta.get_fields())


class SimulatedProvider:
    """
    Pretend SMS/voice sender. Doesn't actually send anything;
    it just returns success so the rest of the app can be built
    and tested without a real SMS/voice account.
    """
    def send(self, recipient, message, channel):
        print(f"[SIMULATED {channel.upper()}] to {recipient}: {message}")
        return {"status": "sent"}


def send_notification(dose_log=None, channel=None, notification_type='reminder',
                      message=None, recipient=None):
    """
    Creates a Notification record and 'sends' it via the simulated provider.
    dose_log is optional, because some messages (like HELP) aren't about one dose.
    If dose_log is not given, recipient must be.
    """
    patient = recipient or (dose_log.patient if dose_log else None)
    if patient is None:
        raise ValueError("send_notification needs a dose_log or a recipient")

    channel = channel or getattr(patient, 'channel_preference', 'sms')

    if message is None:
        if dose_log:
            med = dose_log.schedule.medication
            message = f"Reminder: take {med.generic_name} ({dose_log.schedule.dosage})"
        else:
            message = "Message from Pill Pal"

    provider = SimulatedProvider()
    result = provider.send(recipient=patient, message=message, channel=channel)

    fields = dict(
        recipient=patient,
        channel=channel,
        notification_type=notification_type,
        status='sent' if result['status'] == 'sent' else 'failed',
        dose_log=dose_log,
    )
    # Only save the text if the Notification model has a place for it
    if _model_has_field('message'):
        fields['message'] = message

    return Notification.objects.create(**fields)