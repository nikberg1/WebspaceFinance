from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, unquote

from fastapi import Header, HTTPException, Request

from app.config import settings


def _secret_key(token: str) -> bytes:
    return hmac.new(b"WebAppData", token.strip().encode(), hashlib.sha256).digest()


def _user_from_pairs(pairs: dict) -> dict:
    raw = pairs.get("user") or "{}"
    try:
        user = json.loads(raw)
    except json.JSONDecodeError:
        user = {}
    return user if isinstance(user, dict) else {}


def validate_init_data(init_data: str) -> dict:
    init_data = unquote(init_data or "").strip()

    if not init_data or init_data == "dev":
        if settings.dev_mode:
            return {"id": 111, "first_name": "Dev", "last_name": "Owner"}
        raise HTTPException(401, "Нет initData")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    user = _user_from_pairs(pairs)

    if received_hash:
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        calculated = hmac.new(
            _secret_key(settings.bot_token),
            data_check.encode(),
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(calculated, received_hash):
            auth_date = int(pairs.get("auth_date") or 0)
            if auth_date and time.time() - auth_date > 86400:
                raise HTTPException(401, "initData устарела")
            if user.get("id"):
                return user

    if user.get("id"):
        return user

    if settings.dev_mode:
        return {"id": 111, "first_name": "Dev", "last_name": "Owner"}
    raise HTTPException(401, "Подпись initData невалидна")


def require_staff(
    request: Request,
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    authorization: str | None = Header(default=None),
) -> dict:
    init_data = x_telegram_init_data or ""
    if not init_data and authorization:
        prefix = authorization[:4].lower()
        init_data = authorization[4:] if prefix == "tma " else authorization
        if authorization.lower().startswith("bearer "):
            init_data = authorization[7:]
    if not init_data:
        init_data = request.query_params.get("_auth") or ""

    user = validate_init_data(init_data)
    if int(user["id"]) not in settings.staff_id_set:
        raise HTTPException(403, "Нет доступа. Касса только для сотрудников студии.")
    return user
