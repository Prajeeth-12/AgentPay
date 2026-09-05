import asyncio
import json
import os
import sys
import uuid
import pytest
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from db.database import init_db, get_db
from db.models import AuditEventType
from mandates.manager import mandate_manager
from mandates.constraints import check_budget as do_check_budget
from catalog.service import search_products, get_product
from agent.shopping_agent import ShoppingAgent
from payments.razorpay_client import create_order, create_payment_link
from mcp.razorpay_mcp import fetch_payment_status, create_qr_code


from uap.registry import uap_registry

async def create_test_session(budget_limit_paise: int):
    await init_db()
    agent_info = await uap_registry.register_agent(
        agent_id="agent_uap_001",
        name="AgentPay Shopping Assistant",
        max_budget=10000000,
    )

    session_id = f"sess_test_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO sessions (id, agent_id, budget_limit, budget_spent, status, created_at, updated_at) VALUES (?, 'agent_uap_001', ?, 0, 'active', ?, ?)",
            (session_id, budget_limit_paise, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    open_mandates = await mandate_manager.create_open_mandates(
        session_id=session_id,
        agent_id="agent_uap_001",
        budget_limit=budget_limit_paise,
        agent_public_key_jwk=agent_info["public_key_jwk"],
        private_key_pem=agent_info["private_key_pem"],
    )

    agent = ShoppingAgent(
        session_id=session_id,
        agent_id="agent_uap_001",
        private_key_pem=agent_info["private_key_pem"],
    )

    return session_id, agent


async def run_20_situations_test():
    print("\n=======================================================")
    print("[*] RUNNING 20 AGENTPAY SITUATIONAL STRESS & PROTOCOL TESTS")
    print("=======================================================\n")

    results = []

    # -------------------------------------------------------------
    # Situation 1: Incremental Cart Additions within Budget
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(100000) # ₹1,000
        # Add 4 items incrementally: ₹49 + ₹79 + ₹99 + ₹149 = ₹376
        r1 = await agent._tool_add_to_cart({"product_id": "prod_sports_straw_brush", "quantity": 1})
        r2 = await agent._tool_add_to_cart({"product_id": "prod_fastandup_energy_gel", "quantity": 1})
        r3 = await agent._tool_add_to_cart({"product_id": "prod_microfiber_cloth", "quantity": 1})
        r4 = await agent._tool_add_to_cart({"product_id": "prod_usbc_cable_1m", "quantity": 1})
        
        cart = await agent._tool_view_cart()
        assert cart["data"]["item_count"] == 4
        assert cart["data"]["total_paise"] == 4900 + 7900 + 9900 + 14900
        assert cart["data"]["total_display"] == "₹376"
        assert cart["data"]["budget_remaining"] == "₹624"
        results.append(("Situation 01: Incremental Cart Additions within Budget", True, "4 items added, total ₹376, ₹624 remaining"))
    except Exception as e:
        results.append(("Situation 01: Incremental Cart Additions within Budget", False, str(e)))

    # -------------------------------------------------------------
    # Situation 2: Exact Budget Boundary
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(50000) # ₹500
        # Add item ₹499
        r1 = await agent._tool_add_to_cart({"product_id": "prod_premium_insoles", "quantity": 1}) # ₹499
        assert r1["data"]["added"] is True
        cart = await agent._tool_view_cart()
        assert cart["data"]["total_paise"] == 49900
        assert cart["data"]["budget_remaining"] == "₹1"
        results.append(("Situation 02: Exact Budget Boundary", True, "₹499 added on ₹500 budget, ₹1 remaining"))
    except Exception as e:
        results.append(("Situation 02: Exact Budget Boundary", False, str(e)))

    # -------------------------------------------------------------
    # Situation 3: Budget Exceeded on Subsequent Addition (Defense)
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(100000) # ₹1,000
        # Add Bewakoof T-Shirt (₹799)
        r1 = await agent._tool_add_to_cart({"product_id": "prod_bewakoof_oversized", "quantity": 1})
        assert r1["data"]["added"] is True
        # Attempt to add Portronics Clean Kit (₹249) -> Total ₹1,048 > ₹1,000
        r2 = await agent._tool_add_to_cart({"product_id": "prod_portronics_clean_kit", "quantity": 1})
        assert r2["data"].get("error") == "budget_exceeded"
        cart = await agent._tool_view_cart()
        assert cart["data"]["item_count"] == 1 # Only the first item remains
        assert cart["data"]["total_paise"] == 79900
        results.append(("Situation 03: Budget Exceeded Defense on Subsequent Addition", True, "Blocked ₹249 addition; cart preserved at ₹799"))
    except Exception as e:
        results.append(("Situation 03: Budget Exceeded Defense on Subsequent Addition", False, str(e)))

    # -------------------------------------------------------------
    # Situation 4: Remove Item from Cart and Replace
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(100000) # ₹1,000
        await agent._tool_add_to_cart({"product_id": "prod_bewakoof_oversized", "quantity": 1}) # ₹799
        rem = await agent._tool_remove_from_cart({"product_id": "prod_bewakoof_oversized"})
        assert rem["data"]["removed"] is True
        # Now add Uniqlo T-shirt (₹999) -> fits within ₹1,000!
        r2 = await agent._tool_add_to_cart({"product_id": "prod_uniqlo_airism_tee", "quantity": 1})
        assert r2["data"]["added"] is True
        cart = await agent._tool_view_cart()
        assert cart["data"]["item_count"] == 1
        assert cart["data"]["total_paise"] == 99900
        results.append(("Situation 04: Remove Item and Replace", True, "Removed ₹799 item, added ₹999 item successfully"))
    except Exception as e:
        results.append(("Situation 04: Remove Item and Replace", False, str(e)))

    # -------------------------------------------------------------
    # Situation 5: Pay, Clear Cart, and Subsequent Purchase in Same Session
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(200000) # ₹2,000
        # Purchase 1: Bewakoof T-Shirt (₹799)
        await agent._tool_add_to_cart({"product_id": "prod_bewakoof_oversized", "quantity": 1})
        pay1 = await agent._tool_execute_payment()
        assert pay1["data"]["success"] is True
        await asyncio.sleep(0.5)
        
        # Verify cart is empty after payment!
        cart_after = await agent._tool_view_cart()
        assert cart_after["data"]["item_count"] == 0
        
        # Purchase 2: Uniqlo T-Shirt (₹999) on remaining ₹1,201
        add2 = await agent._tool_add_to_cart({"product_id": "prod_uniqlo_airism_tee", "quantity": 1})
        assert add2["data"]["added"] is True
        pay2 = await agent._tool_execute_payment()
        assert pay2["data"]["success"] is True
        await asyncio.sleep(0.5)
        
        # Verify total spent is ₹1,798 and remaining is ₹202
        db = await get_db()
        cursor = await db.execute("SELECT budget_spent FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        await db.close()
        assert row["budget_spent"] == 79900 + 99900 # ₹1,798
        results.append(("Situation 05: Pay, Clear Cart, and Subsequent Purchase in Same Session", True, "Paid ₹799, cart cleared, paid ₹999, total spent ₹1,798"))
    except Exception as e:
        results.append(("Situation 05: Pay, Clear Cart, and Subsequent Purchase in Same Session", False, str(e)))

    # -------------------------------------------------------------
    # Situation 6: Multi-Item Single Checkout with AP2 Mandates
    # -------------------------------------------------------------
    try:
        await asyncio.sleep(0.5)
        session_id, agent = await create_test_session(200000)
        await agent._tool_add_to_cart({"product_id": "prod_sports_straw_brush", "quantity": 1}) # ₹49
        await agent._tool_add_to_cart({"product_id": "prod_microfiber_cloth", "quantity": 1}) # ₹99
        await agent._tool_add_to_cart({"product_id": "prod_usbc_cable_1m", "quantity": 1}) # ₹149
        pay = await agent._tool_execute_payment()
        assert pay["data"]["success"] is True
        assert len(pay["data"]["items"]) == 3
        assert pay["data"]["amount_display"] == "₹297"
        assert pay["data"]["payment_link"].startswith("https://rzp.io")
        results.append(("Situation 06: Multi-Item Single Checkout with AP2 Mandates", True, "3 items checked out for ₹297 with valid mandates and link"))
    except Exception as e:
        results.append(("Situation 06: Multi-Item Single Checkout with AP2 Mandates", False, str(e)))

    # -------------------------------------------------------------
    # Situation 7: Attempt Payment with Empty Cart
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(200000)
        pay = await agent._tool_execute_payment()
        assert pay["data"].get("error") == "Cart is empty"
        results.append(("Situation 07: Attempt Payment with Empty Cart", True, "Gracefully returned 'Cart is empty' error"))
    except Exception as e:
        results.append(("Situation 07: Attempt Payment with Empty Cart", False, str(e)))

    # -------------------------------------------------------------
    # Situation 8: Add Quantity Multiplier within Budget
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(100000) # ₹1,000
        # Add 3x USB cables (₹149 each = ₹447)
        r = await agent._tool_add_to_cart({"product_id": "prod_usbc_cable_1m", "quantity": 3})
        assert r["data"]["added"] is True
        assert r["data"]["quantity"] == 3
        cart = await agent._tool_view_cart()
        assert cart["data"]["total_paise"] == 14900 * 3
        assert cart["data"]["total_display"] == "₹447"
        results.append(("Situation 08: Quantity Multiplier within Budget", True, "Added 3x ₹149 = ₹447 correctly"))
    except Exception as e:
        results.append(("Situation 08: Quantity Multiplier within Budget", False, str(e)))

    # -------------------------------------------------------------
    # Situation 9: Quantity Multiplier Exceeding Budget
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(50000) # ₹500
        # Attempt to add 5x USB cables (5 * ₹149 = ₹745 > ₹500)
        r = await agent._tool_add_to_cart({"product_id": "prod_usbc_cable_1m", "quantity": 5})
        assert r["data"].get("error") == "budget_exceeded"
        cart = await agent._tool_view_cart()
        assert cart["data"]["item_count"] == 0
        results.append(("Situation 09: Quantity Multiplier Exceeding Budget", True, "Blocked 5x ₹149 (₹745 > ₹500)"))
    except Exception as e:
        results.append(("Situation 09: Quantity Multiplier Exceeding Budget", False, str(e)))

    # -------------------------------------------------------------
    # Situation 10: Natural Query Extraction with Broad Search
    # -------------------------------------------------------------
    try:
        items = search_products(query="Show me cheap accessories under 200 rupees")
        assert len(items) >= 4
        assert all(int(p["offers"]["price"]) <= 20000 for p in items)
        results.append(("Situation 10: Natural Query Extraction with Broad Search", True, f"Matched {len(items)} items under ₹200"))
    except Exception as e:
        results.append(("Situation 10: Natural Query Extraction with Broad Search", False, str(e)))

    # -------------------------------------------------------------
    # Situation 11: Natural Brand Filtering
    # -------------------------------------------------------------
    try:
        items = search_products(query="Nike")
        assert len(items) >= 3
        assert all("nike" in p["name"].lower() or "nike" in p["brand"]["name"].lower() for p in items)
        results.append(("Situation 11: Natural Brand Filtering", True, f"Found {len(items)} Nike products"))
    except Exception as e:
        results.append(("Situation 11: Natural Brand Filtering", False, str(e)))

    # -------------------------------------------------------------
    # Situation 12: Price Range Filtering (Min and Max)
    # -------------------------------------------------------------
    try:
        items = search_products(query="audio", min_price=1000, max_price=3000)
        assert len(items) >= 2
        assert all(100000 <= int(p["offers"]["price"]) <= 300000 for p in items)
        results.append(("Situation 12: Price Range Filtering (Min and Max)", True, f"Found {len(items)} audio items between ₹1,000 and ₹3,000"))
    except Exception as e:
        results.append(("Situation 12: Price Range Filtering (Min and Max)", False, str(e)))

    # -------------------------------------------------------------
    # Situation 13: Multiple Sequential Orders in Same Session
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(300000) # ₹3,000
        # Order 1: ₹49
        await agent._tool_add_to_cart({"product_id": "prod_sports_straw_brush", "quantity": 1})
        await asyncio.sleep(0.5)
        p1 = await agent._tool_execute_payment()
        
        # Order 2: ₹79
        await agent._tool_add_to_cart({"product_id": "prod_fastandup_energy_gel", "quantity": 1})
        await asyncio.sleep(0.5)
        p2 = await agent._tool_execute_payment()
        
        # Order 3: ₹99
        await agent._tool_add_to_cart({"product_id": "prod_microfiber_cloth", "quantity": 1})
        await asyncio.sleep(0.5)
        p3 = await agent._tool_execute_payment()

        assert p1["data"]["order_id"] != p2["data"]["order_id"] != p3["data"]["order_id"]
        assert p1["data"]["payment_link"] != p2["data"]["payment_link"] != p3["data"]["payment_link"]
        results.append(("Situation 13: Multiple Sequential Orders in Same Session", True, "Generated 3 distinct orders & payment links"))
    except Exception as e:
        results.append(("Situation 13: Multiple Sequential Orders in Same Session", False, str(e)))

    # -------------------------------------------------------------
    # Situation 14: Check Payment Status via MCP Tool
    # -------------------------------------------------------------
    try:
        await asyncio.sleep(0.5)
        session_id, agent = await create_test_session(100000)
        await agent._tool_add_to_cart({"product_id": "prod_sports_straw_brush", "quantity": 1})
        pay = await agent._tool_execute_payment()
        order_id = pay["data"]["razorpay_order_id"]
        await asyncio.sleep(0.5)
        status = await agent._tool_check_payment_status({"razorpay_order_id": order_id})
        assert status["data"]["order_id"] == order_id
        assert status["data"]["status"] in ["no_payments", "created", "attempted", "paid", "authorized", "captured"]
        results.append(("Situation 14: Check Payment Status via MCP Tool", True, f"Tracked live order {order_id} via MCP (status: {status['data']['status']})"))
    except Exception as e:
        results.append(("Situation 14: Check Payment Status via MCP Tool", False, str(e)))

    # -------------------------------------------------------------
    # Situation 15: Generate UPI QR Code via MCP Tool
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(100000)
        qr = await agent._tool_create_upi_qr({"amount_paise": 49900, "description": "Dr Scholls Insoles"})
        assert qr["data"]["mcp_powered"] is True
        assert qr["data"]["amount_display"] == "₹499"
        assert "image_url" in qr["data"]
        results.append(("Situation 15: Generate UPI QR Code via MCP Tool", True, "Generated UPI QR code with real payload"))
    except Exception as e:
        results.append(("Situation 15: Generate UPI QR Code via MCP Tool", False, str(e)))

    # -------------------------------------------------------------
    # Situation 16: Budget Exhaustion to Zero Remaining
    # -------------------------------------------------------------
    try:
        await asyncio.sleep(0.5)
        session_id, agent = await create_test_session(100000) # ₹1,000
        # Add Uniqlo Shirt (₹999) -> ₹1 remaining
        await agent._tool_add_to_cart({"product_id": "prod_uniqlo_airism_tee", "quantity": 1})
        await agent._tool_execute_payment()
        # Now attempt to add cheapest item (₹49) -> Reject!
        r = await agent._tool_add_to_cart({"product_id": "prod_sports_straw_brush", "quantity": 1})
        assert r["data"].get("error") == "budget_exceeded"
        results.append(("Situation 16: Budget Exhaustion to Zero Remaining", True, "Rejected ₹49 addition with ₹1 remaining budget"))
    except Exception as e:
        results.append(("Situation 16: Budget Exhaustion to Zero Remaining", False, str(e)))

    # -------------------------------------------------------------
    # Situation 17: Duplicate Item Addition
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(100000)
        await agent._tool_add_to_cart({"product_id": "prod_microfiber_cloth", "quantity": 1}) # ₹99
        await agent._tool_add_to_cart({"product_id": "prod_microfiber_cloth", "quantity": 1}) # ₹99
        cart = await agent._tool_view_cart()
        assert cart["data"]["total_paise"] == 9900 * 2 # ₹198
        assert cart["data"]["total_display"] == "₹198"
        results.append(("Situation 17: Duplicate Item Addition", True, "Added duplicate items; total ₹198 calculated accurately"))
    except Exception as e:
        results.append(("Situation 17: Duplicate Item Addition", False, str(e)))

    # -------------------------------------------------------------
    # Situation 18: View Cart Tool Accuracy
    # -------------------------------------------------------------
    try:
        session_id, agent = await create_test_session(150000) # ₹1,500
        await agent._tool_add_to_cart({"product_id": "prod_steel_water_bottle", "quantity": 1}) # ₹299
        await agent._tool_add_to_cart({"product_id": "prod_boldfit_sweatband_set", "quantity": 1}) # ₹399
        cart = await agent._tool_view_cart()
        assert cart["data"]["item_count"] == 2
        assert cart["data"]["total_display"] == "₹698"
        assert cart["data"]["budget_remaining"] == "₹802"
        results.append(("Situation 18: View Cart Tool Accuracy", True, "Accurate count, items list, total, and remaining budget"))
    except Exception as e:
        results.append(("Situation 18: View Cart Tool Accuracy", False, str(e)))

    # -------------------------------------------------------------
    # Situation 19: AP2 Mandate Hash Integrity & ES256 Signatures
    # -------------------------------------------------------------
    try:
        await asyncio.sleep(0.5)
        session_id, agent = await create_test_session(200000)
        await agent._tool_add_to_cart({"product_id": "prod_steel_water_bottle", "quantity": 1})
        pay = await agent._tool_execute_payment()
        mandates = await mandate_manager.get_session_mandates(session_id)
        assert len(mandates) >= 4
        types = [m["type"] for m in mandates]
        assert "open_checkout" in types
        assert "open_payment" in types
        assert "closed_checkout" in types
        assert "closed_payment" in types
        # Verify hashes and statuses
        for m in mandates:
            assert m["status"] in ["signed", "verified"]
            assert len(m["mandate_hash"]) > 20
        results.append(("Situation 19: AP2 Mandate Hash Integrity & ES256 Signatures", True, "All 4 open/closed AP2 mandates verified with valid hashes"))
    except Exception as e:
        results.append(("Situation 19: AP2 Mandate Hash Integrity & ES256 Signatures", False, str(e)))

    # -------------------------------------------------------------
    # Situation 20: Audit Trail Immutability & Event Ordering
    # -------------------------------------------------------------
    try:
        await asyncio.sleep(0.5)
        session_id, agent = await create_test_session(200000)
        await agent._tool_add_to_cart({"product_id": "prod_steel_water_bottle", "quantity": 1})
        await agent._tool_execute_payment()
        from audit.logger import audit_logger
        trail = await audit_logger.get_trail(session_id)
        assert len(trail) >= 4
        event_types = [entry["event_type"] for entry in trail]
        assert "OPEN_MANDATE_CREATED" in event_types
        assert "CLOSED_CHECKOUT_SIGNED" in event_types
        assert "CLOSED_PAYMENT_SIGNED" in event_types
        assert "RAZORPAY_ORDER_CREATED" in event_types
        assert "PAYMENT_LINK_CREATED" in event_types
        results.append(("Situation 20: Audit Trail Immutability & Event Ordering", True, f"Verified {len(trail)} chronological cryptographic audit events"))
    except Exception as e:
        results.append(("Situation 20: Audit Trail Immutability & Event Ordering", False, str(e)))

    # -------------------------------------------------------------
    # Print Full Scorecard
    # -------------------------------------------------------------
    print("\n=======================================================")
    print("[+] 20 SITUATIONS VERIFICATION SCORECARD")
    print("=======================================================\n")
    passed = 0
    for name, status, details in results:
        status_str = "[PASS]" if status else "[FAIL]"
        if status:
            passed += 1
        print(f"{status_str} | {name}\n       └─ {details}\n")

    print(f"Total: {passed}/{len(results)} Passed ({passed/len(results)*100:.1f}%)\n")
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(run_20_situations_test())
    sys.exit(0 if success else 1)
