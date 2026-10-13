import os
import requests


def send_sms_via_textbee(phone_number, message_text):
    """Send an SMS via TextBee using the device-specific endpoint."""
    api_key = os.environ.get('TEXTBEE_API_KEY')
    device_id = os.environ.get('TEXTBEE_DEVICE_ID')

    if not api_key or not device_id:
        return {"error": "TextBee credentials not set"}

    url = f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/send-sms"

    payload = {
        "recipients": [phone_number],
        "message": message_text
    }

    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}
