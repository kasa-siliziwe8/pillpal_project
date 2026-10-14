from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('sms/', views.sms_simulator, name='sms_simulator'),
    path('voice/', views.voice_channel, name='voice_channel'),
    path('api/confirm-dose/', views.api_confirm_dose, name='api_confirm_dose'),
    path('api/sms-respond/', views.api_sms_respond, name='api_sms_respond'),
    path('internal/run-seed-data/', views.run_seed_data, name='run_seed_data'),
    path('internal/run-create-superuser/', views.run_create_superuser, name='run_create_superuser'),
]
