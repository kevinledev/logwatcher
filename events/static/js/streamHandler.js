class StreamHandler {
  constructor() {
    console.log("[StreamHandler] Initializing...");
    this.subscribers = new Map();
    this.eventSource = null;
    console.log("[StreamHandler] Initialized successfully");
  }

  connect() {
    console.log("[StreamHandler] Attempting to connect...");
    if (!this.eventSource) {
      try {
        this.eventSource = new EventSource("/stream/events/");

        this.eventSource.onerror = (error) => {
          console.error("[StreamHandler] Connection error:", error);
          if (!isGenerating) {
            console.log(
              "[StreamHandler] Generation stopped, closing connection"
            );
            this.disconnect();
            return;
          }
          console.log(
            "[StreamHandler] Connection state:",
            this.eventSource.readyState
          );
        };

        this.eventSource.addEventListener("api.request", async (e) => {
          try {
            const rawData = JSON.parse(e.data);
            const formattedData = this.formatEventData(rawData);

            this.subscribers.forEach((subscriber) => {
              if (typeof subscriber.callback === "function") {
                subscriber.callback(formattedData);
              }
            });
          } catch (error) {
            console.error(
              "[StreamHandler] Error processing stream data:",
              error
            );
          }
        });
      } catch (error) {
        console.error("[StreamHandler] Failed to create EventSource:", error);
      }
    }
  }

  async disconnect() {
    console.log("[StreamHandler] Disconnecting...");
    if (this.eventSource) {
      try {
        this.eventSource.close();
        this.eventSource = null;
        console.log("[StreamHandler] EventSource closed");

        const response = await fetch("/stream/stop/");
        const data = await response.json();
        console.log("[StreamHandler] Stop request response:", data);

        this.subscribers.clear();
      } catch (error) {
        console.error("[StreamHandler] Error stopping stream:", error);
      }
    }
  }

  subscribe(callback, options = {}) {
    const id = Math.random().toString(36);
    this.subscribers.set(id, { callback, options });
    
    if (isGenerating && !this.eventSource) {
      this.connect();
    }
    return id;
  }

  unsubscribe(id) {
    if (this.subscribers.has(id)) {
      this.subscribers.delete(id);
      console.log("[StreamHandler] Unsubscribed:", id);
    }
  }

  formatEventData(rawData) {
    return {
      time: new Date(rawData.timestamp),
      method: rawData.method,
      source: rawData.source,
      duration: rawData.duration_ms,
      status: rawData.status_code,
      isError: rawData.status_code >= 400,
      message: rawData.status_code >= 400 ? rawData.metadata.error_message : "",
    };
  }
}
