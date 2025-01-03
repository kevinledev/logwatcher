# logwatcher

A real-time analytics dashboard that demonstrates modern web monitoring/logging patterns using lightweight technologies. Instead of relying on heavy frameworks or complex infrastructure, the project showcases how server-sent events (SSE), Chart.js, and Django can create a responsive, production-grade monitoring solution. The system generates and streams mock API traffic to simulate real-world web activity, tracking common metrics like throughput monitoring, error rate tracking, and latency measurements.

## Core Features
- Real-time traffic generation and streaming
  - Start/stop stream on demand
  - Mock API traffic with realistic patterns
  - Synchronized controls across browser tabs
- Live dashboard with three key metrics:
  - API Throughput
  - Error Rates (4xx, 5xx)
  - Response Latency

## Tech Stack
### Backend
- Django
- PostgreSQL
- Django's built-in async capabilities for event streaming

### Frontend
- Django Templates
- Chart.js for real-time visualizations
- HTMX for dynamic updates
- Halfmoon CSS for UI

### Infrastructure
- AWS EC2 for hosting
- AWS RDS PostgreSQL database
- NGINX web server (reverse proxy)
  - Configured for SSE support
- Uvicorn ASGI server
  - Handles Django async views
  - Supports SSE streaming
  - Required for Django's async views

## Development Journey & Technical Decisions

### Data Source
- Decided to mock API calls instead of using production API
  - Simpler implementation
  - Predictable error rates and patterns
- Designed generic event model tracking:
  - HTTP methods
  - Status codes
  - Response times
  - Source endpoints

### Evolution of Real-time Updates
The real-time functionality went through several iterations to reach its current form. Initially, the dashboard used a simple polling mechanism with two separate 5-second timers - one for generating data points and another for updating the charts. While functional, this approach was inefficient and could lead to missed events. The solution evolved to use Server-Sent Events (SSE) for true real-time streaming, eliminating the polling overhead. The event generation was then integrated directly into the SSE stream using Django's async views and asyncio to streamline the data flow. As multiple components needed to listen to this event stream, I developed `streamHandler.js` to manage client-side subscriptions and event distribution. This final architecture provides efficient real-time updates while maintaining clean separation of concerns: the server handles event generation and streaming, while the StreamHandler manages client-side data distribution and chart updates.

### Real-time Updates Architecture
- Chose Server-Sent Events over WebSockets
  - Simpler implementation for one-way data flow
  - Native browser support
  - Less overhead than WebSockets
- Used Python's asyncio with Django
- Live stream controls sync automatically across all open browser tabs

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
  - Migration from Django's default SQLite db to PostgreSQL

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
