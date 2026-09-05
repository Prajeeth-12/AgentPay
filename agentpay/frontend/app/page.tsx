"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Chat } from "@/components/Chat";
import { MandateViewer } from "@/components/MandateViewer";
import { AuditTrail } from "@/components/AuditTrail";
import { SessionSetup } from "@/components/SessionSetup";
import { AgentPaySocket, ConnectionStatus } from "@/lib/websocket";
import { ChatMessage, Mandate, AuditEntry, Product, WSEvent } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

let msgCounter = 0;
function nextMsgId(prefix: string) {
  return `${prefix}_${++msgCounter}`;
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [activePanel, setActivePanel] = useState<"chat" | "mandates" | "audit">("chat");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [budgetLimit, setBudgetLimit] = useState(0);
  const [budgetSpent, setBudgetSpent] = useState(0);
  const [cartTotal, setCartTotal] = useState(0);

  const socketRef = useRef<AgentPaySocket | null>(null);
  const pendingProductsRef = useRef<Product[]>([]);
  const pendingPaymentLinkRef = useRef<string>("");

  const handleWSEvent = useCallback((event: WSEvent) => {
    switch (event.type) {
      case "connected":
        setBudgetLimit(event.budget_limit as number);
        break;

      case "agent_text":
        setStreamingText((prev) => prev + (event.text as string));
        break;

      case "agent_message": {
        setStreamingText("");
        setIsLoading(false);
        const msg: ChatMessage = {
          id: nextMsgId("msg"),
          role: "agent",
          content: event.text as string,
          timestamp: new Date().toISOString(),
          products: pendingProductsRef.current.length > 0 ? [...pendingProductsRef.current] : undefined,
          paymentLink: pendingPaymentLinkRef.current || undefined,
        };
        setMessages((prev) => [...prev, msg]);
        pendingProductsRef.current = [];
        pendingPaymentLinkRef.current = "";
        break;
      }

      case "tool_result": {
        const result = event.result as Record<string, unknown>;
        const events = (result?.events as Record<string, unknown>[]) || [];
        for (const subEvent of events) {
          handleWSEvent(subEvent as WSEvent);
        }
        break;
      }

      case "products": {
        const items = event.items as Product[];
        if (items?.length > 0) {
          pendingProductsRef.current = items;
        }
        break;
      }

      case "mandate_created":
      case "mandate_updated": {
        const mandate = event.mandate as Mandate;
        if (mandate) {
          setMandates((prev) => {
            const existing = prev.findIndex((m) => m.id === mandate.id);
            if (existing >= 0) {
              const updated = [...prev];
              updated[existing] = { ...updated[existing], ...mandate };
              return updated;
            }
            return [...prev, mandate];
          });
        }
        break;
      }

      case "audit_entry": {
        const entry = event.entry as AuditEntry;
        if (entry) {
          setAuditEntries((prev) => [...prev, entry]);
        }
        break;
      }

      case "budget_update":
        if (typeof event.spent === "number") setBudgetSpent(event.spent as number);
        if (typeof event.cart_total === "number") setCartTotal(event.cart_total as number);
        if (typeof event.limit === "number" && (event.limit as number) > 0) {
          setBudgetLimit(event.limit as number);
        }
        break;

      case "cart_updated":
        if (typeof event.cart_total === "number") setCartTotal(event.cart_total as number);
        break;

      case "constraint_violation": {
        const details = event.details as Record<string, unknown>;
        const sysMsg: ChatMessage = {
          id: nextMsgId("sys"),
          role: "system",
          content: `Mandate violation: ${String(details?.reason || "budget_exceeded").replace(/_/g, " ")}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, sysMsg]);
        break;
      }

      case "payment_link":
        pendingPaymentLinkRef.current = event.url as string;
        break;

      case "error": {
        setIsLoading(false);
        setStreamingText("");
        const errMsg: ChatMessage = {
          id: nextMsgId("err"),
          role: "system",
          content: `Error: ${event.message as string}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errMsg]);
        break;
      }
    }
  }, []);

  const handleStatusChange = useCallback((status: ConnectionStatus) => {
    setConnectionStatus(status);
  }, []);

  const createSession = async (budget: number) => {
    setIsCreating(true);
    setCreateError(null);
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ budget_limit: budget }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Session creation failed (${res.status})`);
      }
      const data = await res.json();

      if (!data.session_id) {
        throw new Error("Invalid session response from server");
      }

      setSessionId(data.session_id);
      setBudgetLimit(budget);
      setBudgetSpent(0);
      setCartTotal(0);

      try {
        localStorage.setItem("agentpay_session_id", data.session_id);
        localStorage.setItem("agentpay_budget_limit", String(budget));
      } catch {}

      const mandatesRes = await fetch(`${API_BASE}/api/sessions/${data.session_id}/mandates`);
      if (mandatesRes.ok) {
        const mandatesData = await mandatesRes.json();
        setMandates(mandatesData);
      }

      const auditRes = await fetch(`${API_BASE}/api/sessions/${data.session_id}/audit`);
      if (auditRes.ok) {
        const auditData = await auditRes.json();
        setAuditEntries(auditData);
      }

      const socket = new AgentPaySocket(data.session_id, handleWSEvent, handleStatusChange);
      socket.connect();
      socketRef.current = socket;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create session";
      setCreateError(message);
      console.error("Failed to create session:", err);
    } finally {
      setIsCreating(false);
    }
  };

  const resetSession = () => {
    socketRef.current?.disconnect();
    socketRef.current = null;
    try {
      localStorage.removeItem("agentpay_session_id");
      localStorage.removeItem("agentpay_budget_limit");
    } catch {}
    setSessionId(null);
    setMessages([]);
    setMandates([]);
    setAuditEntries([]);
    setBudgetSpent(0);
    setCartTotal(0);
  };

  const sendMessage = (text: string) => {
    const sent = socketRef.current?.sendMessage(text);
    if (!sent) {
      const errMsg: ChatMessage = {
        id: nextMsgId("err"),
        role: "system",
        content: "Connection lost. Please refresh the page.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
      return;
    }

    const userMsg: ChatMessage = {
      id: nextMsgId("user"),
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setStreamingText("");
  };

  // Restore session from localStorage on initial page load
  useEffect(() => {
    const savedSessionId = typeof window !== "undefined" ? localStorage.getItem("agentpay_session_id") : null;
    if (!savedSessionId) return;

    async function restoreSession(id: string) {
      try {
        const [sessionRes, mandatesRes, auditRes] = await Promise.all([
          fetch(`${API_BASE}/api/sessions/${id}`),
          fetch(`${API_BASE}/api/sessions/${id}/mandates`),
          fetch(`${API_BASE}/api/sessions/${id}/audit`),
        ]);
        if (sessionRes.ok) {
          const sessionData = await sessionRes.json();
          setSessionId(id);
          setBudgetLimit(sessionData.budget_limit || 0);
          setBudgetSpent(sessionData.budget_spent || 0);
          setCartTotal(sessionData.cart_total || 0);

          if (mandatesRes.ok) setMandates(await mandatesRes.json());
          if (auditRes.ok) setAuditEntries(await auditRes.json());

          const socket = new AgentPaySocket(id, handleWSEvent, handleStatusChange);
          socket.connect();
          socketRef.current = socket;
        } else {
          localStorage.removeItem("agentpay_session_id");
          localStorage.removeItem("agentpay_budget_limit");
        }
      } catch (e) {
        console.error("Failed to restore session:", e);
      }
    }
    restoreSession(savedSessionId);
  }, [handleWSEvent, handleStatusChange]);

  useEffect(() => {
    return () => {
      socketRef.current?.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const interval = setInterval(async () => {
      try {
        const [mandatesRes, auditRes, sessionRes] = await Promise.all([
          fetch(`${API_BASE}/api/sessions/${sessionId}/mandates`),
          fetch(`${API_BASE}/api/sessions/${sessionId}/audit`),
          fetch(`${API_BASE}/api/sessions/${sessionId}`),
        ]);
        if (mandatesRes.ok) {
          const mandatesData = await mandatesRes.json();
          setMandates(mandatesData);
        }
        if (auditRes.ok) {
          const auditData = await auditRes.json();
          setAuditEntries(auditData);
        }
        if (sessionRes.ok) {
          const sessionData = await sessionRes.json();
          setBudgetSpent(sessionData.budget_spent || 0);
          setCartTotal(sessionData.cart_total || 0);
          if (sessionData.budget_limit) setBudgetLimit(sessionData.budget_limit);
        }
      } catch {
        // network error during polling — non-critical
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [sessionId]);

  if (!sessionId) {
    return <SessionSetup onCreateSession={createSession} isCreating={isCreating} error={createError} />;
  }

  const statusColor = connectionStatus === "connected"
    ? "bg-emerald-500"
    : connectionStatus === "connecting"
    ? "bg-amber-500"
    : "bg-red-500";

  const statusLabel = connectionStatus === "connected"
    ? "Connected"
    : connectionStatus === "connecting"
    ? "Reconnecting..."
    : "Disconnected";

  return (
    <div className="h-screen bg-zinc-950 text-white flex flex-col">
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur px-4 md:px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold tracking-tight">
            Agent<span className="text-blue-500">Pay</span>
          </h1>
          <span className="text-[10px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full hidden sm:inline">
            UAP + AP2
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-400">
          <button
            onClick={resetSession}
            className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white px-2.5 py-1 rounded-md transition-colors border border-zinc-700/60"
            title="Start a fresh session with a new budget"
          >
            + New Session
          </button>
          <span className="hidden md:inline">Session: <code className="text-zinc-500">{sessionId.slice(0, 16)}...</code></span>
          <span className="flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full ${statusColor} ${connectionStatus === "connected" ? "animate-pulse" : ""}`} />
            {statusLabel}
          </span>
        </div>
      </header>

      {/* Mobile panel tabs */}
      <div className="flex lg:hidden border-b border-zinc-800 bg-zinc-900/50">
        {(["chat", "mandates", "audit"] as const).map((panel) => (
          <button
            key={panel}
            onClick={() => setActivePanel(panel)}
            className={`flex-1 py-2 text-xs font-medium capitalize transition-colors ${
              activePanel === panel
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {panel === "mandates" ? "AP2 Mandates" : panel === "audit" ? "Audit Trail" : "Chat"}
          </button>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Desktop: 3-column, Mobile: single panel */}
        <div className={`w-full lg:w-[40%] lg:border-r lg:border-zinc-800 flex flex-col ${activePanel !== "chat" ? "hidden lg:flex" : ""}`}>
          <Chat
            messages={messages}
            onSend={sendMessage}
            isLoading={isLoading}
            streamingText={streamingText}
          />
        </div>

        <div className={`w-full lg:w-[30%] lg:border-r lg:border-zinc-800 flex flex-col ${activePanel !== "mandates" ? "hidden lg:flex" : ""}`}>
          <MandateViewer
            mandates={mandates}
            budgetLimit={budgetLimit}
            budgetSpent={budgetSpent}
            cartTotal={cartTotal}
          />
        </div>

        <div className={`w-full lg:w-[30%] flex flex-col ${activePanel !== "audit" ? "hidden lg:flex" : ""}`}>
          <AuditTrail entries={auditEntries} />
        </div>
      </div>
    </div>
  );
}
