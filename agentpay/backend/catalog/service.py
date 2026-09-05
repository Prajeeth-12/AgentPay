import json
import os
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
    limit: int = 10,
) -> list[dict]:
    products = _load_catalog()
    results = []

    query_lower = query.lower()
    for p in products:
        if query_lower:
            searchable = f"{p['name']} {p.get('description', '')} {p.get('category', '')} {p.get('brand', {}).get('name', '')}".lower()
            if query_lower not in searchable:
                continue

        price = p["offers"]["price"]
        if max_price and price > max_price:
            continue
        if min_price and price < min_price:
            continue

        if category:
            if category.lower() not in p.get("category", "").lower():
                continue

        results.append(p)

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
