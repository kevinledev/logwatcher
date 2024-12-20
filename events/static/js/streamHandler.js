class StreamHandler {
  constructor() {
    this.subscribers = new Map();
    this.eventSource = null;
    this.dataBuffer = [];
    this.lastUpdate = Date.now();
    this.currentInterval = 10; // Default 10s interval
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

  setInterval(seconds) {
    this.currentInterval = seconds;
    this.dataBuffer = []; // Clear buffer when interval changes
    this.lastUpdate = Date.now(); // Reset timer
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
        this.dataBuffer.push(formattedData);

        // Immediately notify non-buffered subscribers
        this.subscribers.forEach((sub) => {
          if (!sub.options.buffered) {
            sub.callback(formattedData);
          }
        });

        const now = Date.now();
        // Use the configured interval for buffer timing
        if (now - this.lastUpdate >= this.currentInterval * 1000) {
          if (this.dataBuffer.length > 0) {
            const avgDuration = this.dataBuffer.reduce((sum, item) => sum + item.duration, 0) / this.dataBuffer.length;
            const latestTime = this.dataBuffer[this.dataBuffer.length - 1].time;
            
            const aggregatedData = {
              time: latestTime,
              duration: avgDuration,
              method: formattedData.method,
              source: formattedData.source,
              status: formattedData.status,
              isError: formattedData.isError,
              message: formattedData.message
            };

            // Notify buffered subscribers
            this.subscribers.forEach((sub) => {
              if (sub.options.buffered) {
                sub.callback(aggregatedData);
              }
            });
            
            this.dataBuffer = [];
            this.lastUpdate = now;
          }
        }
      } catch (error) {
        console.error("Error processing stream data:", error);
      }
    });
  }

  subscribe(callback, options = { buffered: false }) {
    const id = Math.random().toString(36);
    this.subscribers.set(id, { callback, options });
    if (isGenerating && !this.eventSource) {
      this.connect();
    }
    return () => this.subscribers.delete(id);
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
        rawData.status_code >= 400 ? rawData.metadata.error_message : "Success",
    };
  }
}
