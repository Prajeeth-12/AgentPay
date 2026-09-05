import json
import logging
import os
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agentpay")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
os.environ["AWS_CONFIG_FILE"] = ""
os.environ["AWS_SHARED_CREDENTIALS_FILE"] = ""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_settings
from db.database import init_db, get_db
from db.models import AuditEventType, SessionStatus
from audit.logger import audit_logger
from agent.shopping_agent import ShoppingAgent
from catalog.service import search_products, get_product, list_products, get_categories
from mandates.manager import mandate_manager
from mandates.constraints import check_budget
from payments.razorpay_client import create_order, create_payment_link, verify_webhook_signature
from payments.webhook_handler import handle_webhook
from uap.registry import uap_registry
from mcp.razorpay_mcp import fetch_payment_status, create_qr_code, initiate_refund, fetch_settlements, detect_payment_method_preference

# Active WebSocket connections and agent instances per session
active_connections: dict[str, WebSocket] = {}
active_agents: dict[str, ShoppingAgent] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    agent = await uap_registry.register_agent(
        agent_id="agent_uap_001",
        name="AgentPay Shopping Assistant",
        max_budget=10000000,  # ₹1,00,000 max
    )
    app.state.default_agent = agent
    yield


app = FastAPI(
    title="AgentPay",
    description="India's First UAP-Compatible Agentic Commerce Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        os.environ.get("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────

class CreateSessionRequest(BaseModel):
    budget_limit: int  # paise

class ConstraintCheckRequest(BaseModel):
    session_id: str
    proposed_amount: int  # paise


# ── Session Endpoints ────────────────────────────────────

@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest):
    agent = app.state.default_agent
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    verification = await uap_registry.verify_agent(agent["agent_id"], req.budget_limit)
    if not verification["authorized"]:
        raise HTTPException(status_code=403, detail=verification)

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO sessions (id, agent_id, budget_limit, budget_spent, status, created_at, updated_at)
               VALUES (?, ?, ?, 0, 'active', ?, ?)""",
            (session_id, agent["agent_id"], req.budget_limit, now, now),
        )
        await db.commit()
    finally:
        await db.close()

    await audit_logger.log(
        session_id=session_id,
        event_type=AuditEventType.UAP_AGENT_VERIFIED,
        details={"verification": verification, "budget_limit": req.budget_limit},
        agent_id=agent["agent_id"],
    )

    open_mandates = await mandate_manager.create_open_mandates(
        session_id=session_id,
        agent_id=agent["agent_id"],
        budget_limit=req.budget_limit,
        agent_public_key_jwk=agent["public_key_jwk"],
        private_key_pem=agent["private_key_pem"],
    )

    return {
        "session_id": session_id,
        "agent_id": agent["agent_id"],
        "budget_limit": req.budget_limit,
        "open_mandates": open_mandates,
        "status": "active",
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        session_dict = dict(row)

        cart_cursor = await db.execute("SELECT * FROM cart_items WHERE session_id = ?", (session_id,))
        cart_rows = await cart_cursor.fetchall()
        cart_items = [dict(r) for r in cart_rows]
        cart_total = sum(r["price"] * r["quantity"] for r in cart_items)

        session_dict["cart_total"] = cart_total
        session_dict["cart_count"] = len(cart_items)
        session_dict["cart_items"] = cart_items
    finally:
        await db.close()
    return session_dict


@app.get("/api/sessions/{session_id}/mandates")
async def get_session_mandates(session_id: str):
    return await mandate_manager.get_session_mandates(session_id)


@app.get("/api/sessions/{session_id}/audit")
async def get_session_audit(session_id: str):
    return await audit_logger.get_trail(session_id)


# ── Catalog Endpoints ────────────────────────────────────

@app.get("/api/catalog/products")
async def api_list_products(limit: int = 50):
    return list_products(limit)


@app.get("/api/catalog/products/{product_id}")
async def api_get_product(product_id: str):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/catalog/search")
async def api_search_products(
    q: str = "",
    category: str = "",
    max_price: int = 0,
    min_price: int = 0,
    limit: int = 10,
):
    return search_products(q, category, max_price, min_price, limit)


@app.get("/api/catalog/categories")
async def api_get_categories():
    return get_categories()


# ── Mandate Endpoints ────────────────────────────────────

@app.get("/api/mandates/{mandate_id}")
async def api_get_mandate(mandate_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM mandates WHERE id = ?", (mandate_id,))
        row = await cursor.fetchone()
    finally:
        await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Mandate not found")
    result = dict(row)
    if result["payload"]:
        result["payload"] = json.loads(result["payload"])
    if result["constraints"]:
        result["constraints"] = json.loads(result["constraints"])
    return result


@app.post("/api/mandates/check")
async def api_check_constraint(req: ConstraintCheckRequest):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT budget_limit, budget_spent FROM sessions WHERE id = ?",
            (req.session_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return check_budget(req.proposed_amount, row["budget_limit"], row["budget_spent"])


# ── Payment Endpoints ────────────────────────────────────

@app.get("/api/payments/{session_id}")
async def api_get_payments(session_id: str):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM payments WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()
    return [dict(row) for row in rows]


@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    settings = get_settings()
    if settings.razorpay_webhook_secret:
        if not signature or not verify_webhook_signature(body.decode(), signature):
            raise HTTPException(status_code=400, detail="Invalid or missing webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    event_type = payload.get("event", "")
    result = await handle_webhook(event_type, payload)
    return result


# ── MCP-Powered Endpoints ───────────────────────────────

@app.get("/api/mcp/payment-status/{razorpay_order_id}")
async def mcp_payment_status(razorpay_order_id: str):
    return await fetch_payment_status(razorpay_order_id)


@app.post("/api/mcp/qr-code")
async def mcp_create_qr(amount_paise: int, description: str = "AgentPay", session_id: str = ""):
    return await create_qr_code(amount_paise, description, session_id)


@app.post("/api/mcp/refund")
async def mcp_refund(payment_id: str, amount_paise: int, reason: str = "customer_request"):
    return await initiate_refund(payment_id, amount_paise, reason)


@app.get("/api/mcp/settlements")
async def mcp_settlements(count: int = 10):
    return await fetch_settlements(count)


@app.get("/api/mcp/payment-methods")
async def mcp_payment_methods(session_id: str = ""):
    return await detect_payment_method_preference(session_id)


@app.get("/api/mcp/info")
async def mcp_info():
    return {
        "mcp_server": "razorpay/mcp",
        "version": "1.0",
        "capabilities": [
            "payment_status_tracking",
            "upi_qr_generation",
            "refund_processing",
            "settlement_queries",
            "payment_method_detection",
        ],
        "protocol": "Model Context Protocol (MCP)",
        "provider": "Razorpay",
        "integration": "AgentPay UAP + AP2 + MCP",
    }


# ── UAP Registry Endpoints ───────────────────────────────

@app.get("/api/uap/agents")
async def api_list_agents():
    return await uap_registry.list_agents()


@app.get("/api/uap/agents/{agent_id}")
async def api_get_agent(agent_id: str):
    agent = await uap_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.post("/api/uap/agents/{agent_id}/verify")
async def api_verify_agent(agent_id: str, requested_budget: int = 0):
    return await uap_registry.verify_agent(agent_id, requested_budget)


# ── WebSocket Chat Endpoint ──────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    active_connections[session_id] = websocket

    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = await cursor.fetchone()
    finally:
        await db.close()

    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    agent_data = app.state.default_agent
    agent = ShoppingAgent(
        session_id=session_id,
        agent_id=agent_data["agent_id"],
        private_key_pem=agent_data["private_key_pem"],
    )
    active_agents[session_id] = agent

    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "agent_id": agent_data["agent_id"],
        "budget_limit": session["budget_limit"],
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "user_message":
                user_text = data.get("text", "")
                if not user_text:
                    continue

                await audit_logger.log(
                    session_id=session_id,
                    event_type=AuditEventType.INTENT_REGISTERED,
                    details={"user_input": user_text},
                    agent_id=agent_data["agent_id"],
                )

                try:
                    async for event in agent.process_message(user_text):
                        await websocket.send_json(event)

                        for sub_event in event.get("result", {}).get("events", []):
                            await websocket.send_json(sub_event)
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Agent error: {str(e)}",
                    })

    except (WebSocketDisconnect, Exception):
        active_connections.pop(session_id, None)
        active_agents.pop(session_id, None)


# ── Health ───────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "agentpay", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("main:app", host=settings.app_host, port=settings.app_port, reload=True)
