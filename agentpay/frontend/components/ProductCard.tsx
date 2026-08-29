"use client";

import { Product } from "@/lib/types";

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-3 flex items-center gap-3">
      <div className="w-10 h-10 bg-zinc-700 rounded-lg flex items-center justify-center text-lg shrink-0">
        {product.category?.includes("Footwear") ? "👟" :
         product.category?.includes("Electronics") ? "🎧" :
         product.category?.includes("Clothing") ? "👕" :
         product.category?.includes("Books") ? "📚" : "📦"}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-200 truncate">{product.name}</p>
        <p className="text-xs text-zinc-400">{product.brand}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-sm font-bold text-emerald-400">{product.price_display}</p>
        <p className="text-xs text-zinc-500">
          {product.in_stock ? "In stock" : "Out of stock"}
        </p>
      </div>
    </div>
  );
}
