AGENT_TOOLS = [
    {
        "name": "search_catalog",
        "description": "Search the product catalog for items matching a query. Returns products with name, description, price, and availability. Use this when the user asks to find or browse products.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — product name, type, or description keywords",
                },
                "category": {
                    "type": "string",
                    "description": "Product category to filter by (e.g., 'Footwear', 'Electronics')",
                },
                "max_price": {
                    "type": "integer",
                    "description": "Maximum price in paise (e.g., 200000 for ₹2,000)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_product_details",
        "description": "Get full details of a specific product by its ID. Use when the user asks about a specific product or you need to confirm details before adding to cart.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID (e.g., 'prod_nike_pegasus_41')",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "check_budget",
        "description": "Check if a proposed purchase amount fits within the session's remaining budget. ALWAYS call this before adding items to cart or executing payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "proposed_amount": {
                    "type": "integer",
                    "description": "The amount to check in paise",
                },
            },
            "required": ["proposed_amount"],
        },
    },
    {
        "name": "add_to_cart",
        "description": "Add a product to the shopping cart. Only call this after the user has confirmed they want to buy the product and you've verified budget with check_budget.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID to add",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to add (default 1)",
                    "default": 1,
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "view_cart",
        "description": "View the current contents of the shopping cart including total price and remaining budget.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "remove_from_cart",
        "description": "Remove an item from the shopping cart by product ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID to remove",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "execute_payment",
        "description": "Execute payment for the current cart. This creates AP2 mandates, a Razorpay order, and a payment link. ONLY call this after the user explicitly confirms they want to pay. The mandate system will block the payment if it violates any constraints.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "check_payment_status",
        "description": "Check the real-time status of a Razorpay payment via MCP. Use this to verify if a payment link has been paid, or to check the status of any order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "razorpay_order_id": {
                    "type": "string",
                    "description": "The Razorpay order ID (e.g., 'order_xxx')",
                },
            },
            "required": ["razorpay_order_id"],
        },
    },
    {
        "name": "create_upi_qr",
        "description": "Create a UPI QR code for payment as an alternative to payment links. Powered by Razorpay MCP Server. Use when the user prefers QR-based UPI payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_paise": {
                    "type": "integer",
                    "description": "Amount in paise",
                },
                "description": {
                    "type": "string",
                    "description": "Payment description",
                },
            },
            "required": ["amount_paise", "description"],
        },
    },
    {
        "name": "request_refund",
        "description": "Request a refund for a captured payment via Razorpay MCP. Use when the user wants to return an item or cancel after payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "payment_id": {
                    "type": "string",
                    "description": "The Razorpay payment ID to refund",
                },
                "amount_paise": {
                    "type": "integer",
                    "description": "Refund amount in paise (partial or full)",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for refund",
                },
            },
            "required": ["payment_id", "amount_paise"],
        },
    },
]
