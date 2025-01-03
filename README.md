# logwatcher

## Purpose
A lightweight analytics dashboard that tracks and displays mock web application events (API calls, errors) in real-time using server-sent events (SSE). 

This project demonstrates the evolution from a simple dashboard to a robust real-time monitoring system, with careful consideration given to performance, user experience, and maintainability.

## Tech Stack
### Backend
- Django (Python web framework)
- PostgreSQL for event storage
- Django's built-in async capabilities for event streaming

### Frontend
- Django Templates
- Chart.js for real-time visualizations
- HTMX for dynamic updates
- Halfmoon CSS for UI

## Core Features
- Real-time event generation and streaming
- Live dashboard with three key metrics:
  - API Throughput
  - Error Rates (4xx, 5xx)
  - Response Latency
- Configurable time ranges and granularity
- Dark/light mode support

## Development Journey & Technical Decisions

### Data Source
- Decided to mock API calls instead of using production API
  - Simpler implementation
  - Controlled testing environment
  - Predictable error rates and patterns
- Designed generic event model tracking:
  - HTTP methods
  - Status codes
  - Response times
  - Source endpoints

### Real-time Updates Architecture
- Chose Server-Sent Events over WebSockets
  - Simpler implementation for one-way data flow
  - Less overhead than WebSockets (which are bidirectional)
- Evolution of real-time updates:
  1. Initial polling mechanism with dual timers (5s intervals)
  2. Migrated to SSE for more efficient streaming
  3. Integrated event generation within SSE stream
  4. Created StreamHandler.js to manage client-side subscriptions

### Frontend Architecture
- Chose Chart.js over React
  - Lighter weight
  - Built-in real-time plugins
  - Simpler integration with Django templates
- HTMX for dynamic updates
  - Table row rendering
  - Pagination handling
  - Minimal JavaScript

### Data Visualization Challenges
- Time Series Implementation
  - Decided against specialized time-series DB
  - Implemented custom time-based bucketing
  - Sliding window effect for real-time data
- Chart Requirements:
  - Consistent time scale across charts
  - Configurable granularity (5s minimum intervals)
  - ~60 data points target per view
  - Synchronized updates

### Performance Optimization
- Data Buffering Strategy
  - Client-side buffering in StreamHandler
  - Server-side aggregation for historical data
  - Optimized update intervals
- Update Frequency
  - Handled mismatch between server events (~0.8s) and display intervals
  - Implemented smart filtering for chart updates

### Integration Challenges
- Async/Sync Integration
  - Combined Django async views with sync database operations
  - Handled race conditions in real-time updates
- Deployment Issues
  - SSE compatibility with Uvicorn ASGI
  - NGINX configuration for event streams
  - Migration from SQLite to PostgreSQL

### UI/UX Improvements
- Theme Implementation
  - Dark/light mode toggle
  - Dynamic chart color updates
  - Halfmoon CSS integration

### Debugging Journey
- Chart Rendering
  - Fixed tooltip compatibility issues
  - Resolved granularity control bugs
  - Synchronized multi-chart updates
- Data Consistency
  - Matched historical and real-time aggregation
  - Fixed time window calculations
  - Improved error rate accuracy

## API Endpoints
```
GET /api/historical-throughput-data/
GET /api/historical-error-data/
GET /api/historical-latency-data/
GET /event-stream/ # SSE endpoint
```