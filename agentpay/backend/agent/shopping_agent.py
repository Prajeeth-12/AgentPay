import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import asyncio
import httpx

logger = logging.getLogger(__name__)

from config import get_settings
from agent.prompts import SHOPPING_AGENT_SYSTEM_PROMPT
from agent.tools import AGENT_TOOLS
from catalog.service import search_products, get_product
from mandates.manager import mandate_manager
from mandates.constraints import check_budget as do_check_budget
from payments.razorpay_client import create_order, create_payment_link
from mcp.razorpay_mcp import fetch_payment_status, create_qr_code, initiate_refund
from audit.logger import audit_logger
from db.database import get_db
from db.models import AuditEventType


def _convert_tools_to_openai_format(anthropic_tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in anthropic_tools
    ]


OPENAI_TOOLS = _convert_tools_to_openai_format(AGENT_TOOLS)


class ShoppingAgent:
    def __init__(self, session_id: str, agent_id: str, private_key_pem: str):
        self.session_id = session_id
        self.agent_id = agent_id
        self.private_key_pem = private_key_pem
        self.messages: list[dict] = []
        self.settings = get_settings()

    async def _get_session_context(self) -> str:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT budget_limit, budget_spent FROM sessions WHERE id = ?",
                (self.session_id,),
            )
            row = await cursor.fetchone()

            cart_cursor = await db.execute(
                "SELECT product_id, product_title, price, quantity FROM cart_items WHERE session_id = ?",
                (self.session_id,),
            )
            cart_items = await cart_cursor.fetchall()
        finally:
            await db.close()

        if not row:
            return "\n\nWARNING: Session not found. Do not proceed with any purchases."

        budget_limit = row["budget_limit"]
        budget_spent = row["budget_spent"]
        remaining = budget_limit - budget_spent

        cart_desc = "Cart is currently empty."
        if cart_items:
            cart_lines = [f"  • {item['product_title']} (x{item['quantity']}) - ₹{item['price'] / 100:,.0f}" for item in cart_items]
            cart_desc = "Current Cart:\n" + "\n".join(cart_lines)

        return (
            f"\n\nCurrent session context:\n"
            f"- Budget limit: ₹{budget_limit / 100:,.0f}\n"
            f"- Budget spent: ₹{budget_spent / 100:,.0f}\n"
            f"- Budget remaining: ₹{remaining / 100:,.0f}\n"
            f"- {cart_desc}\n"
            f"- Available Store Categories & Price Ranges: Micro items (₹49-₹499: accessories, cables, cleaning kits, socks, energy gels), Footwear (₹1,499-₹8,999: running & casual shoes), Electronics (₹99-₹14,999: audio, chargers, tablets, wearables, accessories), Clothing (₹399-₹3,499: t-shirts, hoodies, jeans, sportswear), Books (₹499-₹899: tech & self-help).\n"
            f"- Session ID: {self.session_id}\n"
        )

    async def process_message(self, user_message: str) -> AsyncGenerator[dict, None]:
        self.messages.append({"role": "user", "content": user_message})

        session_context = await self._get_session_context()
        system_prompt = SHOPPING_AGENT_SYSTEM_PROMPT + session_context

        while True:
            logger.info(f"Calling LLM for session {self.session_id} with {len(self.messages)} messages...")
            response = await self._call_llm(system_prompt)

            message = response.get("choices", [{}])[0].get("message", {})
            content = message.get("content", "") or ""
            tool_calls = message.get("tool_calls", []) or []
            logger.info(f"LLM Response: content={content[:50]!r}, tool_calls={[tc.get('function', {}).get('name') for tc in tool_calls]}")

            if content and not tool_calls:
                yield {"type": "agent_text", "text": content}

            assistant_msg: dict = {
                "role": "assistant",
                "content": content if content else None,
            }
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.messages.append(assistant_msg)

            if not tool_calls:
                final_text = content or ""
                if not final_text and any(m.get("role") == "tool" for m in self.messages):
                    final_text = "Here are the matching options from our catalog within your budget:"
                yield {"type": "agent_message", "text": final_text}
                break

            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                try:
                    tool_input = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_input = {}
                    result = await self._handle_tool_call(tool_name, tool_input)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps({"error": "Malformed tool arguments from LLM"}),
                    })
                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "result": {"data": {"error": "Malformed tool arguments"}, "events": []},
                    }
                    continue

                result = await self._handle_tool_call(tool_name, tool_input)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result["data"]),
                })

                yield {
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "result": result,
                }

    async def _call_llm(self, system_prompt: str) -> dict:
        messages = [{"role": "system", "content": system_prompt}] + self.messages

        request_body = {
            "model": self.settings.llm_model,
            "messages": messages,
            "tools": OPENAI_TOOLS,
            "max_tokens": 4096,
        }

        max_retries = 3
        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=60) as client:
                try:
                    resp = await client.post(
                        f"{self.settings.llm_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.settings.llm_api_key}",
                            "Content-Type": "application/json",
                        },
                        json=request_body,
                    )
                    if resp.status_code == 429 or resp.status_code >= 500:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 * (attempt + 1))
                            continue
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    raise e

    async def _handle_tool_call(self, tool_name: str, tool_input: dict) -> dict:
        if tool_name == "search_catalog":
            return await self._tool_search_catalog(tool_input)
        elif tool_name == "get_product_details":
            return await self._tool_get_product(tool_input)
        elif tool_name == "check_budget":
            return await self._tool_check_budget(tool_input)
        elif tool_name == "add_to_cart":
            return await self._tool_add_to_cart(tool_input)
        elif tool_name == "view_cart":
            return await self._tool_view_cart()
        elif tool_name == "remove_from_cart":
            return await self._tool_remove_from_cart(tool_input)
        elif tool_name == "execute_payment":
            return await self._tool_execute_payment()
        elif tool_name == "check_payment_status":
            return await self._tool_check_payment_status(tool_input)
        elif tool_name == "create_upi_qr":
            return await self._tool_create_upi_qr(tool_input)
        elif tool_name == "request_refund":
            return await self._tool_request_refund(tool_input)
        else:
            return {"data": {"error": f"Unknown tool: {tool_name}"}, "events": []}

    async def _tool_search_catalog(self, input: dict) -> dict:
        results = search_products(
            query=input.get("query", ""),
            category=input.get("category", ""),
            max_price=input.get("max_price", 0),
        )

        simplified = [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p["description"],
                "brand": p.get("brand", {}).get("name", ""),
                "price_paise": p["offers"]["price"],
                "price_display": f"₹{p['offers']['price'] / 100:,.0f}",
                "category": p.get("category", ""),
                "in_stock": "InStock" in p["offers"].get("availability", ""),
                "merchant": p["offers"].get("seller", {}).get("name", ""),
            }
            for p in results
        ]

        await audit_logger.log(
            session_id=self.session_id,
            event_type=AuditEventType.CATALOG_SEARCHED,
            details={"query": input.get("query", ""), "results_count": len(simplified)},
            agent_id=self.agent_id,
        )

        return {
            "data": {"products": simplified, "count": len(simplified)},
            "events": [{"type": "products", "items": simplified}],
        }

    async def _tool_get_product(self, input: dict) -> dict:
        product = get_product(input["product_id"])
        if not product:
            return {"data": {"error": "Product not found"}, "events": []}

        return {
            "data": {
                "id": product["id"],
                "name": product["name"],
                "description": product["description"],
                "brand": product.get("brand", {}).get("name", ""),
                "price_paise": product["offers"]["price"],
                "price_display": f"₹{product['offers']['price'] / 100:,.0f}",
                "category": product.get("category", ""),
            },
            "events": [],
        }

    async def _tool_check_budget(self, input: dict) -> dict:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT budget_limit, budget_spent FROM sessions WHERE id = ?",
                (self.session_id,),
            )
            row = await cursor.fetchone()
        finally:
            await db.close()

        if not row:
            return {"data": {"error": "Session not found"}, "events": []}

        proposed = input.get("proposed_amount", 0)
        result = do_check_budget(proposed, row["budget_limit"], row["budget_spent"])

        result["budget_display"] = {
            "limit": f"₹{row['budget_limit'] / 100:,.0f}",
            "spent": f"₹{row['budget_spent'] / 100:,.0f}",
            "remaining": f"₹{(row['budget_limit'] - row['budget_spent']) / 100:,.0f}",
            "proposed": f"₹{proposed / 100:,.0f}",
        }

        return {
            "data": result,
            "events": [{"type": "budget_update", "spent": row["budget_spent"], "limit": row["budget_limit"]}],
        }

    async def _tool_add_to_cart(self, input: dict) -> dict:
        product = get_product(input["product_id"])
        if not product:
            return {"data": {"error": "Product not found"}, "events": []}

        price = int(product["offers"]["price"])
        quantity = int(input.get("quantity", 1))

        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT budget_limit, budget_spent FROM sessions WHERE id = ?",
                (self.session_id,),
            )
            session = await cursor.fetchone()

            existing = await db.execute(
                "SELECT SUM(price * quantity) as cart_total FROM cart_items WHERE session_id = ?",
                (self.session_id,),
            )
            cart_row = await existing.fetchone()
            cart_total = cart_row["cart_total"] or 0

            proposed_total = cart_total + (price * quantity)
            budget_check = do_check_budget(proposed_total, session["budget_limit"], session["budget_spent"])

            if not budget_check["passed"]:
                await audit_logger.log(
                    session_id=self.session_id,
                    event_type=AuditEventType.CONSTRAINT_CHECK_FAILED,
                    details={
                        "product_id": input["product_id"],
                        "product_name": product["name"],
                        "price": price,
                        "cart_total_with_item": proposed_total,
                    },
                    agent_id=self.agent_id,
                    constraint_check=budget_check,
                )
                return {
                    "data": {
                        "error": "budget_exceeded",
                        "message": f"Adding {product['name']} (₹{price/100:,.0f}) would bring cart total to ₹{proposed_total/100:,.0f}, exceeding budget of ₹{session['budget_limit']/100:,.0f}",
                        "budget_check": budget_check,
                    },
                    "events": [{"type": "constraint_violation", "details": budget_check}],
                }

            item_id = f"cart_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()

            await db.execute(
                "INSERT INTO cart_items (id, session_id, product_id, product_title, price, quantity, added_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (item_id, self.session_id, product["id"], product["name"], price, quantity, now),
            )
            await db.commit()
        finally:
            await db.close()

        await audit_logger.log(
            session_id=self.session_id,
            event_type=AuditEventType.CART_UPDATED,
            details={
                "action": "added",
                "product_id": product["id"],
                "product_name": product["name"],
                "price": price,
                "quantity": quantity,
            },
            agent_id=self.agent_id,
        )

        return {
            "data": {
                "added": True,
                "product": product["name"],
                "price_display": f"₹{price / 100:,.0f}",
                "quantity": quantity,
            },
            "events": [{"type": "cart_updated", "action": "added", "product_id": product["id"]}],
        }

    async def _tool_view_cart(self) -> dict:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM cart_items WHERE session_id = ?", (self.session_id,)
            )
            items = await cursor.fetchall()

            cursor2 = await db.execute(
                "SELECT budget_limit, budget_spent FROM sessions WHERE id = ?",
                (self.session_id,),
            )
            session = await cursor2.fetchone()
        finally:
            await db.close()

        if not session:
            return {"data": {"error": "Session not found"}, "events": []}

        cart_items = [
            {
                "product_id": row["product_id"],
                "title": row["product_title"],
                "price": row["price"],
                "price_display": f"₹{row['price'] / 100:,.0f}",
                "quantity": row["quantity"],
            }
            for row in items
        ]

        total = sum(item["price"] * item["quantity"] for item in cart_items)

        return {
            "data": {
                "items": cart_items,
                "total_paise": total,
                "total_display": f"₹{total / 100:,.0f}",
                "budget_remaining": f"₹{(session['budget_limit'] - session['budget_spent'] - total) / 100:,.0f}",
                "item_count": len(cart_items),
            },
            "events": [],
        }

    async def _tool_remove_from_cart(self, input: dict) -> dict:
        db = await get_db()
        try:
            await db.execute(
                "DELETE FROM cart_items WHERE session_id = ? AND product_id = ?",
                (self.session_id, input["product_id"]),
            )
            await db.commit()
        finally:
            await db.close()

        await audit_logger.log(
            session_id=self.session_id,
            event_type=AuditEventType.CART_UPDATED,
            details={"action": "removed", "product_id": input["product_id"]},
            agent_id=self.agent_id,
        )

        return {
            "data": {"removed": True, "product_id": input["product_id"]},
            "events": [{"type": "cart_updated", "action": "removed", "product_id": input["product_id"]}],
        }

    async def _tool_execute_payment(self) -> dict:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM cart_items WHERE session_id = ?", (self.session_id,)
            )
            items = await cursor.fetchall()

            if not items:
                return {"data": {"error": "Cart is empty"}, "events": []}

            cart_items = [dict(row) for row in items]
            total = sum(item["price"] * item["quantity"] for item in cart_items)

            merchant = {
                "id": "merchant_sportsdirect",
                "name": "SportsDirect India",
                "website": "https://sportsdirect.in",
            }

            line_items = [
                {
                    "id": f"line_{i}",
                    "product_id": item["product_id"],
                    "title": item["product_title"],
                    "price": item["price"],
                    "currency": "INR",
                    "quantity": item["quantity"],
                }
                for i, item in enumerate(cart_items)
            ]

            order_id = f"order_{uuid.uuid4().hex[:12]}"

            checkout_result = await mandate_manager.create_closed_checkout(
                session_id=self.session_id,
                agent_id=self.agent_id,
                private_key_pem=self.private_key_pem,
                order_id=order_id,
                merchant=merchant,
                line_items=line_items,
                total_price=total,
            )

            if checkout_result.get("error"):
                return {
                    "data": {
                        "error": "mandate_violation",
                        "message": "Payment blocked by mandate constraints",
                        "validation": checkout_result["validation"],
                    },
                    "events": [{"type": "constraint_violation", "details": checkout_result["validation"]}],
                }

            payment_mandate = await mandate_manager.create_closed_payment(
                session_id=self.session_id,
                agent_id=self.agent_id,
                private_key_pem=self.private_key_pem,
                checkout_hash=checkout_result["checkout_hash"],
                merchant=merchant,
                amount=total,
            )

            if payment_mandate.get("error"):
                return {
                    "data": {
                        "error": "mandate_violation",
                        "message": "Payment blocked by mandate constraints",
                        "validation": payment_mandate["validation"],
                    },
                    "events": [{"type": "constraint_violation", "details": payment_mandate["validation"]}],
                }

            item_names = ", ".join(item["product_title"] for item in cart_items)
            razorpay_order = await create_order(
                amount_paise=total,
                currency="INR",
                receipt=order_id,
                notes={"session_id": self.session_id, "mandate_id": payment_mandate["id"]},
            )

            await audit_logger.log(
                session_id=self.session_id,
                event_type=AuditEventType.RAZORPAY_ORDER_CREATED,
                details={"razorpay_order_id": razorpay_order["id"], "amount": total},
                agent_id=self.agent_id,
                mandate_id=payment_mandate["id"],
                razorpay_refs={"order_id": razorpay_order["id"]},
            )

            payment_link = await create_payment_link(
                amount_paise=total,
                description=f"AgentPay: {item_names}",
                notes={"session_id": self.session_id, "order_id": order_id},
            )

            await audit_logger.log(
                session_id=self.session_id,
                event_type=AuditEventType.PAYMENT_LINK_CREATED,
                details={
                    "link_id": payment_link["id"],
                    "link_url": payment_link["short_url"],
                    "amount": total,
                },
                agent_id=self.agent_id,
                mandate_id=payment_mandate["id"],
                razorpay_refs={
                    "order_id": razorpay_order["id"],
                    "link_id": payment_link["id"],
                },
            )

            payment_id = f"pay_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()

            await db.execute(
                """INSERT INTO payments (id, session_id, mandate_id, razorpay_order_id, razorpay_link_id, razorpay_link_url, amount, currency, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'INR', 'link_sent', ?, ?)""",
                (
                    payment_id, self.session_id, payment_mandate["id"],
                    razorpay_order["id"], payment_link["id"], payment_link["short_url"],
                    total, now, now,
                ),
            )

            await db.execute(
                "UPDATE sessions SET budget_spent = budget_spent + ?, updated_at = ? WHERE id = ?",
                (total, now, self.session_id),
            )
            await db.commit()
        finally:
            await db.close()

        return {
            "data": {
                "success": True,
                "order_id": order_id,
                "razorpay_order_id": razorpay_order["id"],
                "payment_link": payment_link["short_url"],
                "amount_display": f"₹{total / 100:,.0f}",
                "items": [item["product_title"] for item in cart_items],
                "mandates": {
                    "closed_checkout": checkout_result["id"],
                    "closed_payment": payment_mandate["id"],
                },
            },
            "events": [
                {"type": "mandate_created", "mandate": {"id": checkout_result["id"], "type": "closed_checkout", "status": "verified"}},
                {"type": "mandate_created", "mandate": {"id": payment_mandate["id"], "type": "closed_payment", "status": "verified"}},
                {"type": "payment_link", "url": payment_link["short_url"], "amount": total},
                {"type": "budget_update", "spent": total, "limit": 0},
            ],
        }

    async def _tool_check_payment_status(self, input: dict) -> dict:
        order_id = input.get("razorpay_order_id", "")
        if not order_id:
            return {"data": {"error": "razorpay_order_id is required"}, "events": []}

        status = await fetch_payment_status(order_id)

        await audit_logger.log(
            session_id=self.session_id,
            event_type=AuditEventType.PAYMENT_AUTHORIZED if status.get("status") == "authorized" else AuditEventType.CATALOG_SEARCHED,
            details={"mcp_tool": "check_payment_status", "order_id": order_id, "status": status.get("status")},
            agent_id=self.agent_id,
            razorpay_refs={"order_id": order_id, "payment_id": status.get("payment_id", "")},
        )

        return {"data": status, "events": []}

    async def _tool_create_upi_qr(self, input: dict) -> dict:
        amount = input.get("amount_paise", 0)
        description = input.get("description", "AgentPay Purchase")

        if not amount:
            return {"data": {"error": "amount_paise is required"}, "events": []}

        result = await create_qr_code(amount, description, self.session_id)

        if result.get("error"):
            return {"data": result, "events": []}

        await audit_logger.log(
            session_id=self.session_id,
            event_type=AuditEventType.PAYMENT_LINK_CREATED,
            details={
                "mcp_tool": "create_upi_qr",
                "qr_id": result.get("qr_id"),
                "amount": amount,
            },
            agent_id=self.agent_id,
        )

        return {
            "data": {
                "qr_id": result.get("qr_id"),
                "image_url": result.get("image_url"),
                "amount_display": f"₹{amount / 100:,.0f}",
                "method": "UPI QR Code",
                "mcp_powered": True,
            },
            "events": [{"type": "payment_link", "url": result.get("image_url", ""), "amount": amount}],
        }

    async def _tool_request_refund(self, input: dict) -> dict:
        payment_id = input.get("payment_id", "")
        amount = input.get("amount_paise", 0)
        reason = input.get("reason", "customer_request")

        if not payment_id or not amount:
            return {"data": {"error": "payment_id and amount_paise are required"}, "events": []}

        result = await initiate_refund(payment_id, amount, reason)

        if result.get("error"):
            return {"data": result, "events": []}

        await audit_logger.log(
            session_id=self.session_id,
            event_type=AuditEventType.PAYMENT_FAILED,
            details={
                "mcp_tool": "request_refund",
                "refund_id": result.get("refund_id"),
                "payment_id": payment_id,
                "amount": amount,
                "reason": reason,
            },
            agent_id=self.agent_id,
            razorpay_refs={"payment_id": payment_id},
        )

        return {
            "data": {
                "refund_id": result.get("refund_id"),
                "status": result.get("status"),
                "amount_display": f"₹{amount / 100:,.0f}",
                "mcp_powered": True,
            },
            "events": [],
        }
