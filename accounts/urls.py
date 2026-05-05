from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('settings/', views.settings_view, name='settings'),
    path('change-password/', views.change_password, name='change_password'),
    path('caregivers/', views.caregiver_management, name='caregiver_management'),
    path('profile/', views.profile_view, name='profile'),
    path('api/unread/', views.api_unread_notifications, name='api_unread_notifications'),
]
