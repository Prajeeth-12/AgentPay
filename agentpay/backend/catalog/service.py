import json
import os
import re
from typing import Optional

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "products.json")

_CATALOG: list[dict] | None = None


def _load_catalog() -> list[dict]:
    global _CATALOG
    if _CATALOG is None:
        with open(CATALOG_PATH, "r") as f:
            _CATALOG = json.load(f)
    return _CATALOG


def search_products(
    query: str = "",
    category: str = "",
    max_price: int = 0,
    min_price: int = 0,
    limit: int = 20,
) -> list[dict]:
    products = _load_catalog()
    results = []

    query_lower = query.lower().strip()
    stopwords = {
        "products", "product", "all", "items", "item", "anything", "catalog",
        "everything", "goods", "shop", "what", "there", "list", "show", "under",
        "below", "less", "than", "for", "with", "rupees", "rupee", "rs", "inr",
        "and", "the", "find", "get", "buy", "me", "some", "give", "available", "suggest"
    }

    # Extract price constraints directly from query if not provided
    if not max_price:
        match_max = re.search(r'(?:under|below|less\s+than|upto|within|max|budget(?:\s+of)?)\s*(?:₹|rs\.?|inr)?\s*(\d+)', query_lower)
        if match_max:
            try:
                parsed = int(match_max.group(1))
                max_price = parsed * 100 if parsed < 10000 else parsed
            except ValueError:
                pass

    # Normalize max_price if passed in Rupees instead of paise (e.g. 2000 -> 200000)
    if max_price:
        try:
            max_p = int(max_price)
            if 0 < max_p < 10000:
                max_p *= 100
            max_price = max_p
        except (ValueError, TypeError):
            max_price = 0

    if min_price:
        try:
            min_p = int(min_price)
            if 0 < min_p < 10000:
                min_p *= 100
            min_price = min_p
        except (ValueError, TypeError):
            min_price = 0

    # Extract meaningful keywords excluding stopwords and pure digits
    tokens = [w for w in query_lower.split() if len(w) > 1 and w not in stopwords and not w.isdigit()]
    is_generic = len(tokens) == 0

    scored_results = []
    for p in products:
        price = int(p["offers"]["price"])
        if max_price and price > max_price:
            continue
        if min_price and price < min_price:
            continue

        if category:
            if category.lower() not in p.get("category", "").lower():
                continue

        if not is_generic and tokens:
            searchable = f"{p['name']} {p.get('description', '')} {p.get('category', '')} {p.get('brand', {}).get('name', '')}".lower()
            score = sum(1 for t in tokens if t in searchable)
            if score == 0:
                continue
            scored_results.append((score, p))
        else:
            scored_results.append((1, p))

    # Sort by relevance score descending
    scored_results.sort(key=lambda x: x[0], reverse=True)
    results = [p for _, p in scored_results]

    # If no exact token matches, return top in-budget products as fallback
    if not results and products:
        results = [p for p in products if (not max_price or int(p["offers"]["price"]) <= max_price)][:limit]

    return results[:limit]


def get_product(product_id: str) -> Optional[dict]:
    products = _load_catalog()
    for p in products:
        if p["id"] == product_id:
            return p
    return None


def list_products(limit: int = 50) -> list[dict]:
    products = _load_catalog()
    return products[:limit]


def get_categories() -> list[str]:
    products = _load_catalog()
    categories = set()
    for p in products:
        cat = p.get("category", "")
        if cat:
            categories.add(cat.split(" > ")[0])
    return sorted(categories)
