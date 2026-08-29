"use client";

import { AuditEntry } from "@/lib/types";

interface AuditTrailProps {
  entries: AuditEntry[];
}

const EVENT_ICONS: Record<string, string> = {
  INTENT_REGISTERED: "💬",
  UAP_AGENT_VERIFIED: "🔑",
  OPEN_MANDATE_CREATED: "📜",
  CATALOG_SEARCHED: "🔍",
  PRODUCTS_PRESENTED: "📋",
  USER_SELECTED_PRODUCT: "✅",
  CART_UPDATED: "🛒",
  CLOSED_CHECKOUT_SIGNED: "✍️",
  CONSTRAINT_CHECK_PASSED: "✅",
  CONSTRAINT_CHECK_FAILED: "⛔",
  MANDATE_VIOLATION_BLOCKED: "🚫",
  CLOSED_PAYMENT_SIGNED: "🔏",
  RAZORPAY_ORDER_CREATED: "📦",
  PAYMENT_LINK_CREATED: "🔗",
  PAYMENT_LINK_SENT: "📤",
  PAYMENT_AUTHORIZED: "💳",
  PAYMENT_CAPTURED: "💰",
  PAYMENT_FAILED: "❌",
  TRANSACTION_COMPLETE: "🎉",
  SESSION_EXPIRED: "⏰",
};

const EVENT_COLORS: Record<string, string> = {
  MANDATE_VIOLATION_BLOCKED: "text-red-400",
  CONSTRAINT_CHECK_FAILED: "text-red-400",
  PAYMENT_FAILED: "text-red-400",
  PAYMENT_CAPTURED: "text-emerald-400",
  TRANSACTION_COMPLETE: "text-emerald-400",
  CONSTRAINT_CHECK_PASSED: "text-emerald-400",
  CLOSED_CHECKOUT_SIGNED: "text-blue-400",
  CLOSED_PAYMENT_SIGNED: "text-blue-400",
};

export function AuditTrail({ entries }: AuditTrailProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-900/50 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          Audit Trail
        </h2>
        <span className="text-[10px] text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
          {entries.length} events
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {entries.length === 0 ? (
          <div className="text-center text-zinc-500 mt-12">
            <div className="text-2xl mb-2">📝</div>
            <p className="text-xs">Every action will be logged here.</p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className="px-4 py-2.5 hover:bg-zinc-800/30 transition-colors"
              >
                <div className="flex items-start gap-2">
                  <span className="text-sm mt-0.5 shrink-0">
                    {EVENT_ICONS[entry.event_type] || "📌"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`text-xs font-medium truncate ${
                          EVENT_COLORS[entry.event_type] || "text-zinc-300"
                        }`}
                      >
                        {entry.event_type.replace(/_/g, " ")}
                      </span>
                      <span className="text-[10px] text-zinc-600 shrink-0">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    {entry.constraint_check && (
                      <div className="mt-1">
                        {(entry.constraint_check as Record<string, unknown>).passed ? (
                          <span className="text-[10px] text-emerald-500">
                            Constraint passed
                          </span>
                        ) : (
                          <span className="text-[10px] text-red-400">
                            {String((entry.constraint_check as Record<string, unknown>).reason || "Constraint failed").replace(/_/g, " ")}
                          </span>
                        )}
                      </div>
                    )}

                    {entry.razorpay_refs && (
                      <div className="mt-1 space-x-2">
                        {String((entry.razorpay_refs as Record<string, unknown>).order_id || "") && (
                          <span className="text-[10px] font-mono text-zinc-500">
                            {"order: "}{String((entry.razorpay_refs as Record<string, unknown>).order_id).slice(0, 20)}{"..."}
                          </span>
                        )}
                      </div>
                    )}

                    {entry.mandate_id && (
                      <div className="text-[10px] text-zinc-600 font-mono mt-0.5">
                        mandate: {entry.mandate_id}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
