from django.urls import path

from .views import EventLogView, TankConfigView, TankStateView

app_name = 'control'

urlpatterns = [
    path('state/', TankStateView.as_view(), name='state'),
    path('config/', TankConfigView.as_view(), name='config'),
    path('events/', EventLogView.as_view(), name='events'),
]
