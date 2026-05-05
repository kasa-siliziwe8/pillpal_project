from django.contrib import admin
from django.urls import path, include

handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('medications/', include('medications.urls')),
    path('reports/', include('reports.urls')),
    path('notifications/', include('notifications.urls')),
]
