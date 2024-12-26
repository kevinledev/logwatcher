import asyncio
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from .models import Event
import random
import time
from django.db.models import Avg, Min
import json
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import (
    ExtractMinute, ExtractSecond, ExtractHour
)
from django.db.models import IntegerField
from django.db.models.expressions import ExpressionWrapper
from django.core.paginator import Paginator
from asgiref.sync import sync_to_async
from django.db import models
import logging

# Global flag to control event generation
is_generating = False

logger = logging.getLogger(__name__)

# Create async versions of all database operations
create_event_async = sync_to_async(Event.objects.create)
save_event_async = sync_to_async(lambda x: x.save())
get_events_async = sync_to_async(Event.objects.filter)
paginate_async = sync_to_async(Paginator)

async def generate_event_async():
    """Async version of generate_event"""
    ENDPOINTS = [
        "/api/users",
        "/api/products",
        "/api/orders",
    ]

    API_PATTERNS = [
        {"method": "GET", "duration_range": (50, 200), "weight": 60},
        {"method": "POST", "duration_range": (100, 400), "weight": 25},
        {"method": "PUT", "duration_range": (80, 300), "weight": 10},
        {"method": "DELETE", "duration_range": (50, 150), "weight": 5},
    ]

    STATUS_PATTERNS = [
        {"code": 200, "weight": 85, "message": "Success"},
        {"code": 201, "weight": 5, "message": "Created"},
        {"code": 400, "weight": 4, "message": "Bad request format"},
        {"code": 404, "weight": 4, "message": "Resource not found"},
        {"code": 500, "weight": 2, "message": "Internal server error"},
    ]

    pattern = random.choices(API_PATTERNS, weights=[p["weight"] for p in API_PATTERNS])[0]
    status = random.choices(STATUS_PATTERNS, weights=[s["weight"] for s in STATUS_PATTERNS])[0]

    event = await create_event_async(
        method=pattern["method"],
        source=random.choice(ENDPOINTS),
        duration_ms=random.randint(*pattern["duration_range"]),
        status_code=status["code"],
        metadata={},
    )

    error_details = None
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
        await save_event_async(event)

    return event

def dashboard(request):
    """Main view that renders the monitoring dashboard"""
    global is_generating
    return render(request, "dashboard/index.html", {
        "is_generating": is_generating,
    })

def table_rows(request):
    """HTMX endpoint for paginated table rows"""
    page_number = request.GET.get("page", 1)
    paginator = Paginator(Event.objects.all().order_by("-timestamp"), 15)
    events = paginator.get_page(page_number)
    return render(request, "dashboard/table/base.html", {"events": events})

def generate_events():
    """Background thread that generates events while is_generating is True"""
    global is_generating
    while is_generating:
        generate_event_async()
        time.sleep(5)

def start_generation(request):
    """API endpoint to start event generation"""
    global is_generating
    logger.info("Start generation requested")
    is_generating = True
    logger.info("Generation started")
    return JsonResponse({"status": "started"})

def stop_generation(request):
    """API endpoint to stop event generation"""
    global is_generating
    logger.info("Stop generation requested")
    is_generating = False
    logger.info("Generation stopped")
    return JsonResponse({"status": "stopped"})

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

def get_historical_error_data(request):
    interval_seconds = int(request.GET.get("interval", "60"))
    range_minutes = int(request.GET.get('range', '15'))
    
    # Scale window size based on timeframe
    # Use ~1/12 of the total range as the window size
    window_minutes = max(1, range_minutes // 12)
    window_size = timedelta(minutes=window_minutes)

    now = timezone.now()
    start_time = now - timedelta(minutes=range_minutes)
    events = Event.objects.filter(timestamp__gte=start_time).order_by('timestamp')

    data_points = []
    current_time = start_time
    
    while current_time <= now:
        window_start = current_time - window_size
        window_events = events.filter(
            timestamp__gt=window_start,
            timestamp__lte=current_time
        )
        
        total = window_events.count()
        if total > 0:
            client_errors = window_events.filter(status_code__gte=400, status_code__lt=500).count()
            server_errors = window_events.filter(status_code__gte=500).count()
            
            data_points.append({
                'timestamp': current_time,
                'client_error_rate': (client_errors / total) * 100,
                'server_error_rate': (server_errors / total) * 100
            })
        
        current_time += timedelta(seconds=interval_seconds)

    return JsonResponse({
        'client_errors': [
            {
                'x': point['timestamp'].timestamp() * 1000,
                'y': point['client_error_rate']
            } for point in data_points
        ],
        'server_errors': [
            {
                'x': point['timestamp'].timestamp() * 1000,
                'y': point['server_error_rate']
            } for point in data_points
        ]
    })

async def event_stream(request):
    logger.info("SSE connection attempted")
    global is_generating
    
    if not is_generating:
        logger.info("Stream requested but generation is stopped")
        return StreamingHttpResponse(
            content_type='text/event-stream',
            streaming_content=iter([f"data: {json.dumps({'error': 'Generation stopped'})}\n\n"])
        )
    
    try:
        async def event_stream_generator():
            logger.info("Starting event stream generator")
            while True:
                try:
                    if not is_generating:
                        logger.info("Generation stopped, breaking stream")
                        break

                    logger.info("Generating event...")
                    event = await generate_event_async()
                    if not event:
                        logger.warning("No event generated")
                        continue

                    event_data = {
                        'timestamp': event.timestamp.isoformat(),
                        'method': event.method,
                        'source': event.source,
                        'status_code': event.status_code,
                        'duration_ms': event.duration_ms,
                        'metadata': event.metadata
                    }

                    yield f"data: {json.dumps(event_data)}\nevent: api.request\n\n"
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error in generator: {str(e)}")
                    break

        response = StreamingHttpResponse(
            event_stream_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        return StreamingHttpResponse(
            content_type='text/event-stream',
            streaming_content=iter([f"data: {json.dumps({'error': str(e)})}\n\n"])
        )
