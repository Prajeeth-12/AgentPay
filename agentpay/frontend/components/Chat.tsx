"use client";

import { useState, useRef, useEffect } from "react";
import { ChatMessage, Product } from "@/lib/types";
import { ProductCard } from "./ProductCard";

interface ChatProps {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  isLoading: boolean;
  streamingText: string;
}

export function Chat({ messages, onSend, isLoading, streamingText }: ChatProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput("");
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-zinc-800 bg-zinc-900/50">
        <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">
          Shopping Agent
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4" role="log" aria-live="polite" aria-label="Chat messages">
        {messages.length === 0 && (
          <div className="text-center text-zinc-500 mt-12 space-y-2">
            <div className="text-3xl">🛍️</div>
            <p className="text-sm">Start by telling me what you&apos;d like to buy.</p>
            <p className="text-xs text-zinc-600">
              e.g. &quot;Buy me running shoes under ₹2,000&quot;
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id}>
            <div
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.content && (
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : msg.role === "system"
                      ? "bg-amber-900/30 text-amber-200 border border-amber-800/50"
                      : "bg-zinc-800 text-zinc-100"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              )}
            </div>
            {msg.products && msg.products.length > 0 && (
              <div className="mt-3 space-y-2">
                {msg.products.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            )}
            {msg.paymentLink && (
              <div className="mt-3 p-3 bg-green-900/30 border border-green-700/50 rounded-xl">
                <p className="text-sm text-green-300 mb-2">Payment link ready:</p>
                <a
                  href={msg.paymentLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-green-400 underline hover:text-green-300 break-all"
                >
                  {msg.paymentLink}
                </a>
              </div>
            )}
          </div>
        ))}

        {streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl px-4 py-2.5 text-sm bg-zinc-800 text-zinc-100">
              <p className="whitespace-pre-wrap">{streamingText}</p>
              <span className="inline-block w-1.5 h-4 bg-blue-400 animate-pulse ml-0.5" aria-hidden="true" />
            </div>
          </div>
        )}

        {isLoading && !streamingText && (
          <div className="flex justify-start" role="status" aria-label="Agent is thinking">
            <div className="bg-zinc-800 rounded-2xl px-4 py-3">
              <div className="flex space-x-1.5">
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t border-zinc-800">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell me what you'd like to buy..."
            aria-label="Message to shopping agent"
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
