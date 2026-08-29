export interface Product {
  id: string;
  name: string;
  description: string;
  brand: string;
  price_paise: number;
  price_display: string;
  category: string;
  in_stock: boolean;
  merchant: string;
}

export interface CartItem {
  product_id: string;
  title: string;
  price: number;
  price_display: string;
  quantity: number;
}

export interface Mandate {
  id: string;
  type: "open_checkout" | "closed_checkout" | "open_payment" | "closed_payment";
  vct: string;
  status: string;
  mandate_hash?: string;
  parent_id?: string;
  signed_by?: string;
  created_at: string;
  payload?: Record<string, unknown>;
  constraints?: Record<string, unknown>[];
}

export interface AuditEntry {
  id: number;
  session_id: string;
  timestamp: string;
  event_type: string;
  agent_id?: string;
  mandate_id?: string;
  mandate_type?: string;
  details: Record<string, unknown>;
  razorpay_refs?: Record<string, unknown>;
  constraint_check?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  timestamp: string;
  products?: Product[];
  paymentLink?: string;
}

export interface SessionState {
  session_id: string;
  agent_id: string;
  budget_limit: number;
  budget_spent: number;
  status: string;
  mandates: Mandate[];
  audit_trail: AuditEntry[];
  messages: ChatMessage[];
}

export type WSEventType =
  | "connected"
  | "agent_text"
  | "agent_message"
  | "tool_result"
  | "products"
  | "mandate_created"
  | "mandate_updated"
  | "audit_entry"
  | "budget_update"
  | "constraint_violation"
  | "payment_link"
  | "payment_status"
  | "cart_updated"
  | "error";

export interface WSEvent {
  type: WSEventType;
  [key: string]: unknown;
}
