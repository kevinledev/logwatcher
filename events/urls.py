from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('start/', views.start_generation, name='start_generation'),
    path('stop/', views.stop_generation, name='stop_generation'),
] 