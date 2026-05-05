from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notifications'),
    path('<int:pk>/read/', views.mark_read, name='notification_read'),
    path('mark-all-read/', views.mark_all_read, name='notifications_mark_all_read'),
    path('unread-count/', views.unread_count, name='notifications_unread_count'),
]
