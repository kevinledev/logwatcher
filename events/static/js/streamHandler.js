class StreamHandler {
  constructor() {
    console.log('[StreamHandler] Initializing...');
    this.subscribers = new Map();
    this.eventSource = null;
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
            
            // Clear all subscribers
            this.subscribers.clear();
        } catch (error) {
            console.error('[StreamHandler] Error stopping stream:', error);
        }
    }
  }

  setupSubscribers() {
    console.log('[StreamHandler] Setting up event listeners...');
    
    this.eventSource.addEventListener("api.request", async (e) => {
        const receiveTime = Date.now();
        console.log('[StreamHandler] Received api.request event at:', receiveTime);
        
        try {
            const rawData = JSON.parse(e.data);
            console.log('[StreamHandler] Server generated at:', rawData.generated_at);
            console.log('[StreamHandler] Network latency:', receiveTime - rawData.generated_at, 'ms');

            const formattedData = this.formatEventData(rawData);
            console.log('[StreamHandler] Data formatted at:', Date.now());

            this.subscribers.forEach((subscriber) => {
                console.log('[StreamHandler] Processing subscriber at:', Date.now());
                if (typeof subscriber.callback === 'function') {
                    subscriber.callback(formattedData);
                }
            });
        } catch (error) {
            console.error('[StreamHandler] Error processing stream data:', error);
        }
    });
  }

  subscribe(callback) {
    const id = Math.random().toString(36);
    this.subscribers.set(id, { 
      callback, 
    });

    if (isGenerating && !this.eventSource) {
      this.connect();
    }
    
    return () => {
      this.subscribers.delete(id);
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
