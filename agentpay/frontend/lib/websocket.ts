import { WSEvent } from "./types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001";

export class AgentPaySocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private onEvent: (event: WSEvent) => void;
  private reconnectAttempts = 0;
  private maxReconnects = 3;

  constructor(sessionId: string, onEvent: (event: WSEvent) => void) {
    this.sessionId = sessionId;
    this.onEvent = onEvent;
  }

  connect() {
    const url = `${WS_BASE}/ws/${this.sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSEvent;
        this.onEvent(data);
      } catch {
        // ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnects) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  send(type: string, data: Record<string, unknown> = {}) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...data }));
    }
  }

  sendMessage(text: string) {
    this.send("user_message", { text });
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
