from django.contrib import admin
from .models import Notification, Escalation

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'notification_type', 'channel', 'status', 'created_at', 'read']
    list_filter = ['notification_type', 'channel', 'status', 'read']
    search_fields = ['recipient__username', 'message']
    date_hierarchy = 'created_at'

@admin.register(Escalation)
class EscalationAdmin(admin.ModelAdmin):
    list_display = ['dose_log', 'level', 'alert_sent_to', 'sent_at', 'resolved']
    list_filter = ['level', 'resolved']
