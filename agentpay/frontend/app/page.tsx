"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Chat } from "@/components/Chat";
import { MandateViewer } from "@/components/MandateViewer";
import { AuditTrail } from "@/components/AuditTrail";
import { SessionSetup } from "@/components/SessionSetup";
import { AgentPaySocket } from "@/lib/websocket";
import { ChatMessage, Mandate, AuditEntry, Product, WSEvent } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [budgetLimit, setBudgetLimit] = useState(0);
  const [budgetSpent, setBudgetSpent] = useState(0);

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
          id: `msg_${Date.now()}`,
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
        if (typeof event.spent === "number") {
          setBudgetSpent((prev) => prev + (event.spent as number));
        }
        if (typeof event.limit === "number" && (event.limit as number) > 0) {
          setBudgetLimit(event.limit as number);
        }
        break;

      case "constraint_violation": {
        const details = event.details as Record<string, unknown>;
        const sysMsg: ChatMessage = {
          id: `sys_${Date.now()}`,
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
          id: `err_${Date.now()}`,
          role: "system",
          content: `Error: ${event.message as string}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errMsg]);
        break;
      }
    }
  }, []);

  const createSession = async (budget: number) => {
    setIsCreating(true);
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ budget_limit: budget }),
      });
      const data = await res.json();

      setSessionId(data.session_id);
      setBudgetLimit(budget);
      setBudgetSpent(0);

      const mandatesRes = await fetch(`${API_BASE}/api/sessions/${data.session_id}/mandates`);
      const mandatesData = await mandatesRes.json();
      setMandates(mandatesData);

      const auditRes = await fetch(`${API_BASE}/api/sessions/${data.session_id}/audit`);
      const auditData = await auditRes.json();
      setAuditEntries(auditData);

      const socket = new AgentPaySocket(data.session_id, handleWSEvent);
      socket.connect();
      socketRef.current = socket;
    } catch (err) {
      console.error("Failed to create session:", err);
    } finally {
      setIsCreating(false);
    }
  };

  const sendMessage = (text: string) => {
    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setStreamingText("");
    socketRef.current?.sendMessage(text);
  };

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
        const mandatesData = await mandatesRes.json();
        const auditData = await auditRes.json();
        const sessionData = await sessionRes.json();
        setMandates(mandatesData);
        setAuditEntries(auditData);
        setBudgetSpent(sessionData.budget_spent || 0);
      } catch {
        // ignore polling errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [sessionId]);

  if (!sessionId) {
    return <SessionSetup onCreateSession={createSession} isCreating={isCreating} />;
  }

  return (
    <div className="h-screen bg-zinc-950 text-white flex flex-col">
      <header className="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold tracking-tight">
            Agent<span className="text-blue-500">Pay</span>
          </h1>
          <span className="text-[10px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            UAP + AP2
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-400">
          <span>Session: <code className="text-zinc-500">{sessionId.slice(0, 16)}...</code></span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            Connected
          </span>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[40%] border-r border-zinc-800 flex flex-col">
          <Chat
            messages={messages}
            onSend={sendMessage}
            isLoading={isLoading}
            streamingText={streamingText}
          />
        </div>

        <div className="w-[30%] border-r border-zinc-800 flex flex-col">
          <MandateViewer
            mandates={mandates}
            budgetLimit={budgetLimit}
            budgetSpent={budgetSpent}
          />
        </div>

        <div className="w-[30%] flex flex-col">
          <AuditTrail entries={auditEntries} />
        </div>
      </div>
    </div>
  );
}
