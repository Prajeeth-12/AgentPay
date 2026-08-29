"use client";

import { Mandate } from "@/lib/types";

interface MandateViewerProps {
  mandates: Mandate[];
  budgetLimit: number;
  budgetSpent: number;
}

const TYPE_LABELS: Record<string, string> = {
  open_checkout: "Open Checkout",
  closed_checkout: "Closed Checkout",
  open_payment: "Open Payment",
  closed_payment: "Closed Payment",
};

const STATUS_COLORS: Record<string, string> = {
  signed: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  verified: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  violated: "bg-red-500/20 text-red-300 border-red-500/30",
  expired: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  created: "bg-amber-500/20 text-amber-300 border-amber-500/30",
};

export function MandateViewer({ mandates, budgetLimit, budgetSpent }: MandateViewerProps) {
  const remaining = budgetLimit - budgetSpent;
  const spentPercent = budgetLimit > 0 ? (budgetSpent / budgetLimit) * 100 : 0;

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          AP2 Mandates
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Budget Gauge */}
        <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Budget</span>
            <span className="text-xs text-zinc-500">
              ₹{(remaining / 100).toLocaleString("en-IN")} remaining
            </span>
          </div>
          <div className="w-full bg-zinc-700 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                spentPercent > 90 ? "bg-red-500" :
                spentPercent > 70 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(spentPercent, 100)}%` }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-zinc-500">
            <span>₹{(budgetSpent / 100).toLocaleString("en-IN")} spent</span>
            <span>₹{(budgetLimit / 100).toLocaleString("en-IN")} limit</span>
          </div>
        </div>

        {/* Mandates */}
        {mandates.length === 0 ? (
          <div className="text-center text-zinc-500 mt-8">
            <div className="text-2xl mb-2">🔐</div>
            <p className="text-xs">Mandates will appear here as the agent acts.</p>
          </div>
        ) : (
          mandates.map((m) => (
            <div
              key={m.id}
              className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-3 space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300">
                  {TYPE_LABELS[m.type] || m.type}
                </span>
                <span
                  className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                    STATUS_COLORS[m.status] || STATUS_COLORS.created
                  }`}
                >
                  {m.status.toUpperCase()}
                </span>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">VCT</span>
                  <span className="text-zinc-400 font-mono text-[10px]">{m.vct}</span>
                </div>
                {m.signed_by && (
                  <div className="flex justify-between text-xs">
                    <span className="text-zinc-500">Signed by</span>
                    <span className="text-zinc-400">{m.signed_by}</span>
                  </div>
                )}
                {m.mandate_hash && (
                  <div className="flex justify-between text-xs">
                    <span className="text-zinc-500">Hash</span>
                    <span className="text-zinc-400 font-mono text-[10px] truncate max-w-[120px]">
                      {m.mandate_hash}
                    </span>
                  </div>
                )}
                {m.constraints && m.constraints.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {m.constraints.map((c, i) => {
                      const constraint = c as Record<string, unknown>;
                      return (
                        <div
                          key={i}
                          className="text-[10px] bg-zinc-900/50 rounded px-2 py-1 text-zinc-400 font-mono"
                        >
                          {String(constraint.type || "")}
                          {constraint.max ? (
                            <span className="text-emerald-400 ml-1">
                              {"max ₹"}{(Number(constraint.max) / 100).toLocaleString("en-IN")}
                            </span>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="text-[10px] text-zinc-600">
                {new Date(m.created_at).toLocaleTimeString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
