from typing import Optional


class ConstraintViolation(Exception):
    def __init__(self, reason: str, details: dict):
        self.reason = reason
        self.details = details
        super().__init__(reason)


def check_budget(proposed_amount: int, budget_limit: int, budget_spent: int = 0) -> dict:
    remaining = budget_limit - budget_spent
    if proposed_amount > remaining:
        return {
            "passed": False,
            "reason": "budget_exceeded",
            "proposed": proposed_amount,
            "limit": budget_limit,
            "spent": budget_spent,
            "remaining": remaining,
        }
    return {
        "passed": True,
        "proposed": proposed_amount,
        "limit": budget_limit,
        "spent": budget_spent,
        "remaining": remaining - proposed_amount,
    }


def check_merchant(merchant_id: str, allowed_merchants: list[dict]) -> dict:
    if not allowed_merchants:
        return {"passed": True, "merchant_id": merchant_id}

    allowed_ids = [m.get("id") for m in allowed_merchants]
    if merchant_id in allowed_ids:
        return {"passed": True, "merchant_id": merchant_id}

    return {
        "passed": False,
        "reason": "merchant_not_allowed",
        "merchant_id": merchant_id,
        "allowed": allowed_ids,
    }


def check_amount_range(amount: int, min_amount: int = 0, max_amount: int = 0) -> dict:
    if max_amount is not None and max_amount > 0 and amount > max_amount:
        return {
            "passed": False,
            "reason": "amount_exceeds_max",
            "amount": amount,
            "max": max_amount,
        }
    if min_amount is not None and min_amount > 0 and amount < min_amount:
        return {
            "passed": False,
            "reason": "amount_below_min",
            "amount": amount,
            "min": min_amount,
        }
    return {"passed": True, "amount": amount}


def validate_closed_against_open(closed_payload: dict, open_constraints: list[dict], budget_spent: int = 0) -> dict:
    """Validate a closed mandate against its parent open mandate constraints."""
    violations = []

    for constraint in open_constraints:
        c_type = constraint.get("type", "")

        if c_type in ("checkout.amount_range", "payment.amount_range"):
            amount = closed_payload.get("total_price") or closed_payload.get("payment_amount", {}).get("amount", 0)
            result = check_amount_range(amount, constraint.get("min", 0), constraint.get("max", 0))
            if not result["passed"]:
                violations.append(result)

        elif c_type == "payment.budget":
            amount = closed_payload.get("total_price") or closed_payload.get("payment_amount", {}).get("amount", 0)
            result = check_budget(amount, constraint["max"], budget_spent)
            if not result["passed"]:
                violations.append(result)

        elif c_type == "checkout.allowed_merchants":
            merchant = closed_payload.get("merchant") or closed_payload.get("payee")
            if merchant:
                result = check_merchant(merchant.get("id", ""), constraint.get("allowed", []))
                if not result["passed"]:
                    violations.append(result)

    if violations:
        return {
            "passed": False,
            "violations": violations,
            "reason": violations[0]["reason"],
        }

    return {"passed": True}
