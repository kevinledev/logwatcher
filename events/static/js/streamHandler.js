class StreamHandler {
  constructor() {
    console.log("[StreamHandler] Initializing...");
    this.subscribers = new Map();
    this.eventSource = null;
    
    // Add broadcast channel
    this.broadcastChannel = new BroadcastChannel('stream_state');
    this.broadcastChannel.onmessage = (event) => {
      if (event.data.type === 'stream_state_change') {
        isGenerating = event.data.isGenerating;
        if (isGenerating) {
          this.connect();
        } else {
          this.disconnect();
        }
        this.updateNavbarIndicator();
      }
    };
    
    console.log("[StreamHandler] Initialized successfully");
  }

  // Add method to update UI
  updateNavbarIndicator() {
    const btn = document.getElementById('generateBtn');
    const liveIndicator = document.getElementById('liveIndicator');
    const cardElement = liveIndicator.querySelector('.card');
    const statusIndicator = cardElement.querySelector('span:first-child');
    const statusText = cardElement.querySelector('.d-none.d-sm-inline');
    
    // Update button
    btn.textContent = isGenerating ? 'Stop Stream' : 'Start Stream';
    btn.classList.toggle('btn-danger', isGenerating);
    btn.classList.toggle('btn-primary', !isGenerating);
    
    // Update indicator
    if (isGenerating) {
      statusIndicator.className = 'spinner-grow spinner-grow-sm text-primary';
      statusIndicator.setAttribute('role', 'status');
      statusIndicator.setAttribute('aria-hidden', 'true');
      statusIndicator.textContent = '';
    } else {
      statusIndicator.className = 'text-danger';
      statusIndicator.removeAttribute('role');
      statusIndicator.removeAttribute('aria-hidden');
      statusIndicator.textContent = '●';
    }
    
    // Update status text while maintaining responsive classes
    statusText.textContent = isGenerating ? 'Live' : 'Stopped';
    
    // Update tooltip
    cardElement.setAttribute('data-bs-title', 
      isGenerating 
        ? "Stream is generating data. Click 'Stop Stream' to stop"
        : "Stream has stopped. Click 'Start Stream' to begin"
    );
    
    // Refresh tooltip instance
    const oldTooltip = bootstrap.Tooltip.getInstance(cardElement);
    if (oldTooltip) {
      oldTooltip.dispose();
    }
    new bootstrap.Tooltip(cardElement);
  }

  connect() {
    console.log("[StreamHandler] Attempting to connect...");

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

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
          
          const now = formattedData.time.getTime();
          
          // Synchronized update check
          if (!this.lastUpdateTime || (now - this.lastUpdateTime) >= this.updateInterval) {
            this.subscribers.forEach((subscriber) => {
              if (typeof subscriber.callback === "function") {
                subscriber.callback(formattedData, true); // true indicates it's an update boundary
              }
            });
            this.lastUpdateTime = now;
          } else {
            // Just collect data without updating charts
            this.subscribers.forEach((subscriber) => {
              if (typeof subscriber.callback === "function") {
                subscriber.callback(formattedData, false); // false indicates no update needed
              }
            });
          }
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

  async disconnect() {
    console.log("[StreamHandler] Disconnecting...");
    if (this.eventSource) {
      try {
        this.eventSource.close();
        this.eventSource = null;
        console.log("[StreamHandler] EventSource closed");
      } catch (error) {
        console.error("[StreamHandler] Error closing EventSource:", error);
      }
    }
  }

  subscribe(callback, options = {}) {
    const id = Math.random().toString(36);
    this.subscribers.set(id, { callback, options });
    
    if (isGenerating) {
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
