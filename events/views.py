from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from .models import Event
import random
import threading
import time
from django.db.models import Avg, Min, Max
import json
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import (
    TruncMinute, ExtractMinute, ExtractSecond, ExtractHour
)
from django.db.models import IntegerField
from django.db.models.expressions import ExpressionWrapper

# Global flag to control event generation
is_generating = False
generator_thread = None


def generate_single_event():
    ENDPOINTS = [
        "/api/users",
        "/api/products",
        "/api/orders",
    ]

    # Adjusted patterns with weights for more realistic distribution
    API_PATTERNS = [
        {"method": "GET", "duration_range": (50, 200), "weight": 60},  # 60% GET
        {"method": "POST", "duration_range": (100, 400), "weight": 25},  # 25% POST
        {"method": "PUT", "duration_range": (80, 300), "weight": 10},  # 10% PUT
        {"method": "DELETE", "duration_range": (50, 150), "weight": 5},  # 5% DELETE
    ]

    # Status code patterns with weights and messages
    STATUS_PATTERNS = [
        {"code": 200, "weight": 85, "message": "Success"},
        {"code": 201, "weight": 5, "message": "Created"},
        {"code": 400, "weight": 4, "message": "Bad request format"},
        {"code": 404, "weight": 4, "message": "Resource not found"},
        {"code": 500, "weight": 2, "message": "Internal server error"},
    ]

    pattern = random.choices(API_PATTERNS, weights=[p["weight"] for p in API_PATTERNS])[
        0
    ]

    status = random.choices(
        STATUS_PATTERNS, weights=[s["weight"] for s in STATUS_PATTERNS]
    )[0]

    event = Event.objects.create(
        method=pattern["method"],
        source=random.choice(ENDPOINTS),
        duration_ms=random.randint(*pattern["duration_range"]),
        status_code=status["code"],
        metadata={},
    )

    error_details = None  # Initialize with a default value

    if event.status_code >= 400:
        if event.status_code == 404:
            error_details = f"The requested resource at {event.source} does not exist"
        elif event.status_code == 400:
            error_details = f"Invalid parameters provided for {event.source}"
        elif event.status_code == 500:
            error_details = f"Server encountered an error processing request to {event.source}"

        event.metadata = {
            'error_type': 'server_error' if event.status_code >= 500 else 'client_error',
            'error_message': f"{status['message']} for {event.method} request to {event.source}",
            'error_details': error_details
        }

    event.save()
    return event


def event_list(request):
    events = Event.objects.all().order_by("-timestamp")
    
    return render(
        request,
        "events_list.html",
        {
            "events": events,
            "is_generating": is_generating,
        },
    )


def generate_events():
    global is_generating
    while is_generating:
        generate_single_event()
        time.sleep(5)  # Generate event every 5 seconds


def start_generation(request):
    global is_generating, generator_thread
    if not is_generating:
        is_generating = True
        generator_thread = threading.Thread(target=generate_events)
        generator_thread.start()
    return JsonResponse({"status": "started"})


def stop_generation(request):
    global is_generating
    is_generating = False
    return JsonResponse({"status": "stopped"})


def get_latency_data(request):
    window_seconds = int(request.GET.get('interval', '60'))
    
    now = timezone.now()
    start_time = now - timedelta(seconds=window_seconds)
    
    latest_data = Event.objects.filter(
        timestamp__gte=start_time
    ).aggregate(avg_latency=Avg('duration_ms'))
    
    return JsonResponse({
        'latest_latency': round(latest_data['avg_latency'], 2) if latest_data['avg_latency'] else 0
    })


def get_historical_latency_data(request):
    interval_seconds = int(request.GET.get("interval", "60"))
    range_minutes = int(request.GET.get('range', '15'))  # Now expecting direct minutes
    
    now = timezone.now()
    start_time = now - timedelta(minutes=range_minutes)
    
    events = Event.objects.filter(timestamp__gte=start_time).order_by('timestamp')
    
    if interval_seconds < 60:  # Sub-minute intervals (10s, 30s)
        aggregated_data = (
            events.annotate(
                bucket=ExpressionWrapper(
                    (ExtractHour('timestamp') * 3600 + 
                     ExtractMinute('timestamp') * 60 + 
                     ExtractSecond('timestamp')) / interval_seconds,
                    output_field=IntegerField()
                )
            )
            .values('bucket')
            .annotate(
                avg_latency=Avg('duration_ms'),
                timestamp=Min('timestamp')
            )
            .order_by('bucket')
        )
    else:  # Minute-based intervals (1m, 5m)
        minutes_fraction = interval_seconds // 60
        aggregated_data = (
            events.annotate(
                bucket=ExpressionWrapper(
                    (ExtractHour('timestamp') * 60 + ExtractMinute('timestamp')) / minutes_fraction,
                    output_field=IntegerField()
                )
            )
            .values('bucket')
            .annotate(
                avg_latency=Avg('duration_ms'),
                timestamp=Min('timestamp')
            )
            .order_by('bucket')
        )
    
    return JsonResponse({
        'data': [
            {
                'x': entry['timestamp'].timestamp() * 1000,
                'y': round(entry['avg_latency'], 2) if entry['avg_latency'] else 0
            } for entry in aggregated_data
        ]
    })


def event_stream(request):
    def stream():
        while True:
            if not is_generating:
                yield "data: {}\n\n"
                time.sleep(1)
                continue
                
            event = generate_single_event()
            data = {
                'timestamp': event.timestamp.timestamp() * 1000,
                'latency': event.duration_ms
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(5)  # Keep your existing 5s interval
    
    response = StreamingHttpResponse(
        streaming_content=stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
