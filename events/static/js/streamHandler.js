class StreamHandler {
  constructor() {
    this.subscribers = new Map();
    this.eventSource = null;
    this.dataBuffers = new Map();
    this.lastUpdates = new Map();
    this.defaultInterval = 10;
  }

  connect() {
    if (!this.eventSource) {
      this.eventSource = new EventSource("/stream/events/");
      this.eventSource.onerror = () => {
        console.log("SSE connection error, attempting to reconnect...");
      };
      this.setupSubscribers();
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
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
    this.eventSource.addEventListener("api.request", (e) => {
      if (!isGenerating) {
        this.disconnect();
        return;
      }

      try {
        const rawData = JSON.parse(e.data);
        if (!rawData.timestamp) return;

        const formattedData = this.formatEventData(rawData);

        this.subscribers.forEach((sub, id) => {
          if (sub.options.buffered) {
            if (!this.dataBuffers.has(id)) {
              this.dataBuffers.set(id, [formattedData]);
              this.lastUpdates.set(id, Date.now());
              return;
            }

            const buffer = this.dataBuffers.get(id);
            buffer.push(formattedData);

            const now = Date.now();
            const lastUpdate = this.lastUpdates.get(id);
            const interval = sub.interval * 1000;
            const timeSinceLastUpdate = now - lastUpdate;

            if (timeSinceLastUpdate >= interval || buffer.length === 1) {
              const intervals = Math.floor(timeSinceLastUpdate / interval);
              this.lastUpdates.set(id, lastUpdate + intervals * interval);
              
              if (buffer.length > 0) {
                const avgDuration = buffer.reduce((sum, item) => sum + item.duration, 0) / buffer.length;
                const latestTime = buffer[buffer.length - 1].time;

                const aggregatedData = {
                  time: latestTime,
                  duration: avgDuration,
                  method: formattedData.method,
                  source: formattedData.source,
                  status: formattedData.status,
                  isError: formattedData.isError,
                  message: formattedData.message
                };

                sub.callback(aggregatedData);
                this.dataBuffers.set(id, []);
                this.lastUpdates.set(id, now);
              }
            }
          } else {
            sub.callback(formattedData);
          }
        });
      } catch (error) {
        console.error("Error processing stream data:", error);
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
