"""Track the service's daily estimated LLM costs in Redis."""
from datetime import datetime, timezone

from fastapi import HTTPException

from .config import settings
from .redis_client import r

# Example prices used to estimate costs for the mock LLM.
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _budget_key() -> str:
    day = datetime.now(timezone.utc).date()
    return f"day14:cost:{settings.environment}:{day}"


def check_budget() -> None:
    spent = float(r.get(_budget_key()) or 0)
    if spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    key = _budget_key()
    with r.pipeline() as transaction:
        transaction.incrbyfloat(key, cost)
        transaction.expire(key, 2 * 24 * 60 * 60)
        transaction.execute()
    return cost
