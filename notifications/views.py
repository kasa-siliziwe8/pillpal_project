from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification

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
