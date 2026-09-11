from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from app.config import settings


def _secret_key(token: str) -> bytes:
    return hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str) -> dict:
    if settings.dev_mode and (not init_data or init_data == "dev"):
        return {"id": 111, "first_name": "Dev", "last_name": "Owner"}

    if not init_data:
        raise HTTPException(401, "Нет initData")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "Нет подписи initData")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    calculated = hmac.new(
        _secret_key(settings.bot_token),
        data_check.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        if settings.dev_mode:
            return {"id": 111, "first_name": "Dev", "last_name": "Owner"}
        raise HTTPException(401, "Подпись initData невалидна")

    auth_date = int(pairs.get("auth_date") or 0)
    if auth_date and time.time() - auth_date > 86400:
        raise HTTPException(401, "initData устарела")

    user = json.loads(pairs.get("user") or "{}")
    if not user.get("id"):
        raise HTTPException(401, "В initData нет пользователя")
    return user


def require_staff(init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data")) -> dict:
    user = validate_init_data(init_data or "")
    if user["id"] not in settings.staff_id_set:
        raise HTTPException(403, "Нет доступа. Касса только для сотрудников студии.")
    return user
