from django.urls import path
from . import views

urlpatterns = [
    path('', views.medication_list, name='medications'),
    path('<int:pk>/', views.medication_detail, name='medication_detail'),
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/add/', views.schedule_add, name='schedule_add'),
    path('schedules/<int:pk>/toggle/', views.schedule_toggle, name='schedule_toggle'),
    path('schedules/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
    path('history/', views.dose_history, name='dose_history'),
    path('api/confirm/', views.api_dose_confirm, name='api_dose_confirm'),
]
