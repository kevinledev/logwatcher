from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('', views.monitor_dashboard, name='dashboard'),
    
    # Generator endpoints
    path('generator/start/', views.start_generation, name='generator_start'),
    path('generator/stop/', views.stop_generation, name='generator_stop'),
    
    # Data API endpoints
    path('api/latency-data/', views.get_latency_data, name='latency_data'),
    path('api/historical-latency-data/', views.get_historical_latency_data, name='historical_latency'),
    path('api/event-rows/', views.event_rows, name='event_rows'),
    
    # Stream endpoint
    path('stream/events/', views.event_stream, name='event_stream'),
] 