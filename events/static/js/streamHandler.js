class StreamHandler {
  constructor() {
    this.eventSource = new EventSource("/stream/events/");
    this.subscribers = new Map();

    // Handle connection errors/retries
    this.eventSource.onerror = () => {
      console.log("SSE connection error, attempting to reconnect...");
    };
  }

  subscribe(callback) {
    // Subscribe to stream events
    this.eventSource.addEventListener("api.request", (e) => {
      if (!isGenerating) return;

      try {
        const rawData = JSON.parse(e.data);
        if (!rawData.timestamp) return;

        const formattedData = this.formatEventData(rawData);
        callback(formattedData);
      } catch (error) {
        console.error("Error processing stream data:", error);
      }
    });
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
