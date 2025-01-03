from django.urls import path
from . import views

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Stream control endpoints
    path('stream/start/', views.start_generation, name='stream_start'),
    path('stream/stop/', views.stop_generation, name='stream_stop'),
    
    # Stream endpoint
    path('stream/events/', views.event_stream, name='event_stream'),
    
    # Data API endpoints
    path('api/historical-latency-data/', views.get_historical_latency_data, name='historical_latency'),
    path('api/event-rows/', views.table_rows, name='table_rows'),
    path('api/historical-error-data/', views.get_historical_error_data, name='historical_error_data'),
    path('api/historical-throughput-data/', views.get_historical_throughput_data, name='historical_throughput_data'),
] 
