from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('start/', views.start_generation, name='start_generation'),
    path('stop/', views.stop_generation, name='stop_generation'),
    path('api/latency-data/', views.get_latency_data, name='latency_data'),
    path('api/historical-latency-data/', views.get_historical_latency_data, name='historical_latency_data'),
    path('api/events-stream/', views.event_stream, name='event_stream'),
    path('api/event-rows/', views.event_rows, name='event_rows'),
] 