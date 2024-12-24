class StreamHandler {
  constructor() {
    console.log('[StreamHandler] Initializing...');
    this.subscribers = new Map();
    this.eventSource = null;
    this.dataBuffers = new Map();
    this.lastUpdates = new Map();
    this.defaultInterval = 10;
    console.log('[StreamHandler] Initialized successfully');
  }

  connect() {
    console.log('[StreamHandler] Attempting to connect...');
    if (!this.eventSource) {
        try {
            this.eventSource = new EventSource("/stream/events/");
            console.log('[StreamHandler] EventSource created');
            
            this.eventSource.onopen = () => {
                console.log('[StreamHandler] Connection opened successfully');
            };

            this.eventSource.onerror = (error) => {
                console.error('[StreamHandler] Connection error:', error);
                if (!isGenerating) {
                    console.log('[StreamHandler] Generation stopped, closing connection');
                    this.disconnect();
                    return;
                }
                console.log('[StreamHandler] Connection state:', this.eventSource.readyState);
            };

            this.setupSubscribers();
        } catch (error) {
            console.error('[StreamHandler] Failed to create EventSource:', error);
        }
    }
  }

  async disconnect() {
    console.log('[StreamHandler] Disconnecting...');
    if (this.eventSource) {
        try {
            // First close the EventSource
            this.eventSource.close();
            this.eventSource = null;
            console.log('[StreamHandler] EventSource closed');
            
            // Then tell the server to stop
            const response = await fetch('/stream/stop/');
            const data = await response.json();
            console.log('[StreamHandler] Stop request response:', data);
            
            // Clear all subscribers and buffers
            this.subscribers.clear();
            this.dataBuffers.clear();
            this.lastUpdates.clear();
        } catch (error) {
            console.error('[StreamHandler] Error stopping stream:', error);
        }
    }
  }

  setInterval(seconds, subscriberId) {
    const lastUpdate = this.lastUpdates.get(subscriberId) || Date.now();
    
    const timeSinceLastUpdate = Date.now() - lastUpdate;
    const remainingTime = seconds * 1000 - (timeSinceLastUpdate % (seconds * 1000));
    
    this.dataBuffers.set(subscriberId, []);
    this.lastUpdates.set(subscriberId, lastUpdate + (timeSinceLastUpdate - remainingTime));
  }

  setupSubscribers() {
    console.log('[StreamHandler] Setting up event listeners...');
    
    this.eventSource.addEventListener("api.request", async (e) => {
        console.log('[StreamHandler] Received api.request event');
        
        try {
            const rawData = JSON.parse(e.data);
            console.log('[StreamHandler] Parsed event data:', rawData);

            if (!rawData.timestamp) {
                console.warn('[StreamHandler] Missing timestamp in data');
                return;
            }

            if (!isGenerating) {
                console.log('[StreamHandler] Generation stopped, disconnecting');
                await this.disconnect();
                return;
            }

            const formattedData = this.formatEventData(rawData);
            console.log('[StreamHandler] Formatted data:', formattedData);

            this.subscribers.forEach((subscriber) => {
                if (typeof subscriber.callback === 'function') {
                    subscriber.callback(formattedData);
                } else {
                    console.warn('[StreamHandler] Invalid subscriber callback');
                }
            });
        } catch (error) {
            console.error('[StreamHandler] Error processing stream data:', error);
        }
    });
  }

  subscribe(callback, options = { buffered: false }) {
    const id = Math.random().toString(36);
    this.subscribers.set(id, { 
      callback, 
      options,
      interval: this.defaultInterval
    });
    
    if (options.buffered) {
      this.dataBuffers.set(id, []);
      this.lastUpdates.set(id, Date.now());
    }

    if (isGenerating && !this.eventSource) {
      this.connect();
    }
    return () => {
      this.subscribers.delete(id);
      this.dataBuffers.delete(id);
      this.lastUpdates.delete(id);
    };
  }

  formatEventData(rawData) {
    return {
      time: new Date(rawData.timestamp),
      method: rawData.method,
      source: rawData.source,
      duration: rawData.duration_ms,
      status: rawData.status_code,
      isError: rawData.status_code >= 400,
      message:
        rawData.status_code >= 400 ? rawData.metadata.error_message : "",
    };
  }
}
