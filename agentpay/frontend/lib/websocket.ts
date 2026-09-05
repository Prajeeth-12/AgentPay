import { WSEvent } from "./types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001";

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export class AgentPaySocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private onEvent: (event: WSEvent) => void;
  private onStatusChange: (status: ConnectionStatus) => void;
  private reconnectAttempts = 0;
  private maxReconnects = 3;
  private intentionalDisconnect = false;

  constructor(
    sessionId: string,
    onEvent: (event: WSEvent) => void,
    onStatusChange: (status: ConnectionStatus) => void = () => {},
  ) {
    this.sessionId = sessionId;
    this.onEvent = onEvent;
    this.onStatusChange = onStatusChange;
  }

  connect() {
    this.intentionalDisconnect = false;
    const url = `${WS_BASE}/ws/${this.sessionId}`;
    this.ws = new WebSocket(url);
    this.onStatusChange("connecting");

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onStatusChange("connected");
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSEvent;
        this.onEvent(data);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    this.ws.onclose = () => {
      if (this.intentionalDisconnect) {
        this.onStatusChange("disconnected");
        return;
      }
      if (this.reconnectAttempts < this.maxReconnects) {
        this.reconnectAttempts++;
        this.onStatusChange("connecting");
        setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
      } else {
        this.onStatusChange("disconnected");
      }
    };

    this.ws.onerror = (event) => {
      console.error("WebSocket error:", event);
      this.onStatusChange("error");
      this.ws?.close();
    };
  }

  send(type: string, data: Record<string, unknown> = {}): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...data }));
      return true;
    }
    return false;
  }

  sendMessage(text: string): boolean {
    return this.send("user_message", { text });
  }

  disconnect() {
    this.intentionalDisconnect = true;
    this.ws?.close();
    this.ws = null;
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
