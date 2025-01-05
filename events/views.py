import asyncio
from itertools import count
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from .models import Event
import random
import time
from django.db.models import Avg, Min, Count
import json
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import (
    ExtractMinute, ExtractSecond, ExtractHour
)
from django.db.models import IntegerField
from django.db.models.expressions import ExpressionWrapper
from django.core.paginator import Paginator
from asgiref.sync import sync_to_async, async_to_sync
from django.db import models
import logging
import markdown2

# Global flag to control event generation
is_generating = False
generation_start_time = None
auto_stop_task = None

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

    # Read and convert README.md to HTML
    with open("README.md", "r") as f:
        readme_content = markdown2.markdown(f.read())

    return render(
        request,
        "dashboard/index.html",
        {"is_generating": is_generating, "readme_content": readme_content},
    )

def table_rows(request):
    """HTMX endpoint for paginated table rows"""
    page_number = request.GET.get("page", 1)
    paginator = Paginator(Event.objects.all().order_by("-timestamp"), 15)
    events = paginator.get_page(page_number)
    return render(request, "dashboard/table/base.html", {"events": events})

async def stop_generation_after_delay():
    """Background task to stop generation after 15 minutes"""
    try:
        await asyncio.sleep(15 * 60)  # 15 minutes
        global is_generating
        if is_generating:
            logger.info("Auto-stopping generation after 15 minutes")
            is_generating = False
    except asyncio.CancelledError:
        logger.info("Auto-stop task cancelled")

async def async_start_generation():
    """Async helper for starting generation"""
    global is_generating, generation_start_time, auto_stop_task
    
    is_generating = True
    generation_start_time = timezone.now()
    
    # Cancel any existing auto-stop task
    if auto_stop_task and not auto_stop_task.done():
        auto_stop_task.cancel()
    
    # Create new auto-stop task
    loop = asyncio.get_event_loop()
    auto_stop_task = loop.create_task(stop_generation_after_delay())
    
    return {"status": "started"}

def start_generation(request):
    """API endpoint to start event generation"""
    global is_generating
    logger.info("Start generation requested")
    
    try:
        # Convert async function to sync
        result = async_to_sync(async_start_generation)()
        logger.info("Generation started with 15-minute auto-stop")
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error starting generation: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

def stop_generation(request):
    """API endpoint to stop event generation"""
    global is_generating, generation_start_time, auto_stop_task
    logger.info("Stop generation requested")
    
    is_generating = False
    generation_start_time = None
    
    # Cancel auto-stop task if it exists
    if auto_stop_task and not auto_stop_task.done():
        async_to_sync(auto_stop_task.cancel)()
        auto_stop_task = None
    
    logger.info("Generation stopped")
    return JsonResponse({"status": "stopped"})

def get_historical_latency_data(request):
    interval_seconds = int(request.GET.get("interval", "60"))
    range_minutes = int(request.GET.get('range', '15'))

    print(f"\n=== Historical Latency Data Request ===")
    print(f"Interval: {interval_seconds}s, Range: {range_minutes}m")

    now = timezone.now()
    start_time = now - timedelta(minutes=range_minutes)

    events = Event.objects.filter(timestamp__gte=start_time).order_by('timestamp')
    print(f"Total events in range: {events.count()}")

    if interval_seconds < 60:  # Sub-minute intervals
        print(f"Using sub-minute interval bucketing")
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
    else:  # Minute-based intervals
        print(f"Using minute-based interval bucketing")
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

    data = list(aggregated_data)
    print(f"Number of buckets after aggregation: {len(data)}")
    if len(data) > 0:
        print(f"First bucket: {data[0]}")
        print(f"Last bucket: {data[-1]}")
        print(f"Bucket values: {[d['bucket'] for d in data[:5]]}...")

    return JsonResponse({
        'data': [
            {
                'x': entry['timestamp'].timestamp() * 1000,
                'y': round(entry['avg_latency'], 2) if entry['avg_latency'] else 0
            } for entry in data
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
            MEAN_INTERVAL = 0.8  # ~75 events per minute on average

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
                    # Exponential distribution with mean of 0.8 seconds
                    await asyncio.sleep(random.expovariate(1.0/MEAN_INTERVAL))
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


def get_historical_throughput_data(request):
    interval_seconds = int(request.GET.get("interval", "60"))
    range_minutes = int(request.GET.get("range", "15"))

    now = timezone.now()
    start_time = now - timedelta(minutes=range_minutes)

    events = Event.objects.filter(timestamp__gte=start_time).order_by("timestamp")

    if interval_seconds < 60:  # Sub-minute intervals
        aggregated_data = (
            events.annotate(
                bucket=ExpressionWrapper(
                    (
                        ExtractHour("timestamp") * 3600
                        + ExtractMinute("timestamp") * 60
                        + ExtractSecond("timestamp")
                    )
                    / interval_seconds,
                    output_field=IntegerField(),
                )
            )
            .values("bucket")
            .annotate(count=Count("id"), timestamp=Min("timestamp"))
            .order_by("bucket")
        )
    else:  # Minute-based intervals
        minutes_fraction = interval_seconds // 60
        aggregated_data = (
            events.annotate(
                bucket=ExpressionWrapper(
                    (ExtractHour("timestamp") * 60 + ExtractMinute("timestamp"))
                    / minutes_fraction,
                    output_field=IntegerField(),
                )
            )
            .values("bucket")
            .annotate(count=Count("id"), timestamp=Min("timestamp"))
            .order_by("bucket")
        )

    return JsonResponse(
        {
            "data": [
                {
                    "x": entry["timestamp"].timestamp() * 1000,
                    "y": (entry["count"] * 60)
                    / interval_seconds,  # Convert to requests per minute
                }
                for entry in aggregated_data
            ]
        }
    )

def get_method_distribution(request):
    range_minutes = int(request.GET.get('range', '15'))
    start_time = timezone.now() - timedelta(minutes=range_minutes)
    
    method_counts = (Event.objects.filter(timestamp__gte=start_time)
                    .values('method')
                    .annotate(count=Count('method'))
                    .order_by('-count'))
    
    return JsonResponse({
        'labels': [item['method'] for item in method_counts],
        'data': [item['count'] for item in method_counts],
    })

def get_historical_method_data(request):
    range_minutes = int(request.GET.get('range', '15'))
    start_time = timezone.now() - timedelta(minutes=range_minutes)
    
    events = Event.objects.filter(timestamp__gte=start_time)
    
    method_counts = {
        'GET': events.filter(method='GET').count(),
        'POST': events.filter(method='POST').count(),
        'PUT': events.filter(method='PUT').count(),
        'DELETE': events.filter(method='DELETE').count(),
    }
    
    data = [
        method_counts['GET'],
        method_counts['POST'],
        method_counts['PUT'],
        method_counts['DELETE'],
    ]
    
    return JsonResponse({'data': data})
