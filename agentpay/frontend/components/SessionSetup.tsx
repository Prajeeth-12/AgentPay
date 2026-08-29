"use client";

import { useState } from "react";

interface SessionSetupProps {
  onCreateSession: (budgetLimit: number) => void;
  isCreating: boolean;
}

const PRESETS = [
  { label: "₹1,000", value: 100000 },
  { label: "₹2,000", value: 200000 },
  { label: "₹5,000", value: 500000 },
  { label: "₹10,000", value: 1000000 },
];

export function SessionSetup({ onCreateSession, isCreating }: SessionSetupProps) {
  const [budget, setBudget] = useState(200000);

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center space-y-3">
          <h1 className="text-4xl font-bold text-white tracking-tight">
            Agent<span className="text-blue-500">Pay</span>
          </h1>
          <p className="text-zinc-400 text-sm">
            India&apos;s First UAP-Compatible Agentic Commerce Platform
          </p>
          <div className="flex items-center justify-center gap-2 text-xs text-zinc-500">
            <span className="bg-zinc-800 px-2 py-0.5 rounded">AP2 Mandates</span>
            <span className="bg-zinc-800 px-2 py-0.5 rounded">Razorpay</span>
            <span className="bg-zinc-800 px-2 py-0.5 rounded">Claude AI</span>
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-3">
              Set your spending budget
            </label>
            <div className="grid grid-cols-4 gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setBudget(p.value)}
                  className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                    budget === p.value
                      ? "bg-blue-600 text-white"
                      : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-zinc-800/50 rounded-xl p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-zinc-400">Budget limit</span>
              <span className="text-white font-semibold">
                ₹{(budget / 100).toLocaleString("en-IN")}
              </span>
            </div>
            <div className="flex justify-between text-xs text-zinc-500">
              <span>Protected by AP2 cryptographic mandates</span>
              <span>ES256 signed</span>
            </div>
          </div>

          <button
            onClick={() => onCreateSession(budget)}
            disabled={isCreating}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white py-3 rounded-xl font-medium transition-colors"
          >
            {isCreating ? "Creating session..." : "Start Shopping"}
          </button>
        </div>

        <p className="text-center text-[10px] text-zinc-600">
          UAP Trust Registry + AP2 Mandate Model + Razorpay Test Mode
        </p>
      </div>
    </div>
  );
}
