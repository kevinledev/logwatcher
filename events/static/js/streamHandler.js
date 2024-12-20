class StreamHandler {
  constructor() {
    this.subscribers = new Map();
    this.eventSource = null;
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
        this.subscribers.forEach(callback => callback(formattedData));
      } catch (error) {
        console.error("Error processing stream data:", error);
      }
    });
  }

  subscribe(callback) {
    const id = Math.random().toString(36);
    this.subscribers.set(id, callback);
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
