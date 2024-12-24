class StreamHandler {
  constructor() {
    this.eventSource = null;
    this.subscribers = new Set();
    this.dataBuffers = new Map();
    this.lastUpdates = new Map();
    this.defaultInterval = 60;  // Default interval in seconds
    console.log('[StreamHandler] Initializing...');
  }

  connect() {
    console.log('[StreamHandler] Attempting to connect...');
    if (this.eventSource) {
      console.log('[StreamHandler] Connection already exists, disconnecting first...');
      this.disconnect();
    }

    this.eventSource = new EventSource('/stream/events/');
    console.log('[StreamHandler] EventSource created');

    this.eventSource.onerror = (e) => {
      console.error('[StreamHandler] Connection error:', e);
      console.log('[StreamHandler] Connection state:', this.eventSource.readyState);
      console.log('[StreamHandler] Attempting to reconnect...');
    };

    this.setupSubscribers();
  }

  disconnect() {
    console.log('[StreamHandler] Disconnecting...');
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      
      fetch('/stream/stop/')
        .then(response => response.json())
        .then(data => console.log('[StreamHandler] Stop request sent:', data))
        .catch(error => console.error('[StreamHandler] Error stopping stream:', error));
    }
  }

  setupSubscribers() {
    console.log('[StreamHandler] Setting up event listeners...');
    
    this.eventSource.addEventListener("api.request", (e) => {
      console.log('[StreamHandler] Received api.request event');
      
      if (!isGenerating) {
        console.log('[StreamHandler] Generation stopped, disconnecting');
        this.disconnect();
        return;
      }

      try {
        const rawData = JSON.parse(e.data);
        console.log('[StreamHandler] Parsed event data:', rawData);

        if (!rawData.timestamp) {
          console.warn('[StreamHandler] Missing timestamp in data');
          return;
        }

        const formattedData = this.formatEventData(rawData);
        console.log('[StreamHandler] Formatted data:', formattedData);

        this.subscribers.forEach(callback => callback(formattedData));
      } catch (error) {
        console.error('[StreamHandler] Error processing stream data:', error);
      }
    });
  }

  formatEventData(rawData) {
    return {
      time: new Date(rawData.timestamp),
      method: rawData.method,
      source: rawData.source,
      status: rawData.status_code,
      duration: rawData.duration_ms,
      metadata: rawData.metadata
    };
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  getBuffer(key) {
    if (!this.dataBuffers.has(key)) {
      this.dataBuffers.set(key, []);
    }
    return this.dataBuffers.get(key);
  }

  clearBuffer(key) {
    this.dataBuffers.set(key, []);
  }

  updateLastTimestamp(key, timestamp) {
    this.lastUpdates.set(key, timestamp);
  }

  getLastUpdate(key) {
    return this.lastUpdates.get(key) || 0;
  }
}
