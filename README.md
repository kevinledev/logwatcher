# logwatcher

A real-time dashboard that demonstrates modern web monitoring and logging built using lightweigh technologies. Instead of relying on heavy frameworks or complex infrastructure, the project showcases how server-sent events (SSE), Chart.js, and Django can create a responsive, production-grade monitoring solution. The system generates and streams mock API traffic to simulate real-world web activity, tracking common metrics (like throughput, API latency, error rates) and plotting them on real-time charts and tables.

## Quick Start

Click "Start Stream" in the navigation bar to begin generating sample API traffic data. The dashboard will display real-time visualizations of the following metrics:

- API response latency
- Error rates
- Request throughput
- HTTP method distribution

## System Architecture
The following diagram illustrates the system's key components and data flow
<div align="center">
<a href="https://i.imgur.com/huNNdk3.png" target="_blank">
  <img src="https://i.imgur.com/huNNdk3.png" alt="System Architecture Diagram" width="800"/>
</a>
<a href="https://i.imgur.com/huNNdk3.png" target="_blank">Click to view full size</a>
</div>

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

## Development Journey: From Polling to Real-time Streaming
The real-time functionality went through several iterations to reach its current form. Initially, the dashboard used a simple polling mechanism with two separate 5-second timers - one for generating data points and another for updating the charts. While functional, this approach was inefficient and could lead to missed events. The solution evolved to use Server-Sent Events (SSE) for true real-time streaming, eliminating the polling overhead. The event generation was then integrated directly into the SSE stream using Django's async views and asyncio to streamline the data flow. As multiple components needed to listen to this event stream, I developed `streamHandler.js` to manage client-side subscriptions and event distribution. This final architecture allows efficient real-time updates while maintaining clean separation of concerns: the server handles event generation and streaming, while the StreamHandler manages client-side data distribution and chart updates.

### Real-time Implementation: SSE and Cross-Tab Synchronization
For real-time data streaming, Server-Sent Events (SSE) was chosen over WebSockets due to its unidirectional nature. The server exposes an SSE endpoint `/stream` that continuously generates simulated API traffic data. On the frontend, charts and tables subscribe to this event stream which allows for real-time updates. Since data only flows from server to client, SSE provides a simpler and more efficient approach compared to WebSocket's bidirectional overhead. The implementation uses Python's asyncio with Django for the streaming backend, while BroadcastChannel API ensures the charts and data stream controls stay synchronized across all open browser tabs and windows.

### Frontend Architecture
The frontend prioritizes simplicity and performance by avoiding heavy frameworks. Instead of using solutions like Grafana or React, I built the dashboard using Chart.js and vanilla JavaScript. The charts and tables subscribe to a server-sent event stream `/stream` through a centralized StreamHandler `streamHandler.js`, which manages real-time data distribution and updates. HTMX handles dynamic content updates like table pagination with minimal JavaScript.

### Data Storage & Time Series Handling
While a time-series database would be the conventional choice, I implemented the solution using PostgreSQL with custom time-based bucketing as a learning exercise. The system maintains consistent granularity across charts with configurable timeframes, targeting 60 data points per view for optimal real-time visualization performance.

### Performance Optimization
- Data Buffering Strategy
  - Server-side aggregation for historical data
  - Optimized update intervals
- Update Frequency
  - Handled mismatch between server events (~0.8s) and display intervals


