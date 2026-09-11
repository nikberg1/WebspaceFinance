from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_staff
from app.db import CATEGORIES, get_conn
from app.logic import fetch_accounts, fetch_summary, refresh_overdue, row_to_dict

router = APIRouter(prefix="/api")

OPS_SELECT = """
    SELECT operations.*, accounts.name AS account_name
    FROM operations
    LEFT JOIN accounts ON accounts.id = operations.account_id
"""


class OperationIn(BaseModel):
    type: str = Field(pattern="^(income|expense)$")
    status: str = Field(pattern="^(plan|paid)$")
    category: str
    amount_rub: int = Field(gt=0, le=10_000_000_000)
    comment: str = ""
    op_date: str
    account_id: int


class StatusIn(BaseModel):
    status: str = Field(pattern="^(plan|paid)$")


class BalanceIn(BaseModel):
    balance: int = Field(ge=-10_000_000_000, le=10_000_000_000)


def _account_exists(conn, account_id: int) -> bool:
    row = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    return bool(row)


def _validate_payload(payload: OperationIn) -> None:
    if payload.category not in CATEGORIES:
        raise HTTPException(400, "Неизвестная статья")
    try:
        date.fromisoformat(payload.op_date)
    except ValueError as exc:
        raise HTTPException(400, "Некорректная дата") from exc


@router.get("/me")
def me(user: dict = Depends(require_staff)):
    return {"user": user}


@router.get("/meta")
def meta(user: dict = Depends(require_staff)):
    return {"categories": CATEGORIES, "currency": "RUB", "accounts": fetch_accounts()}


@router.get("/accounts")
def accounts(user: dict = Depends(require_staff)):
    return fetch_accounts()


@router.patch("/accounts/{account_id}")
def set_balance(account_id: int, payload: BalanceIn, user: dict = Depends(require_staff)):
    conn = get_conn()
    acc = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not acc:
        conn.close()
        raise HTTPException(404, "Счёт не найден")
    flow = conn.execute(
        """
        SELECT type, SUM(amount_rub) AS total
        FROM operations
        WHERE account_id = ? AND status = 'paid'
        GROUP BY type
        """,
        (account_id,),
    ).fetchall()
    income = sum(row["total"] or 0 for row in flow if row["type"] == "income")
    expense = sum(row["total"] or 0 for row in flow if row["type"] == "expense")
    opening = payload.balance - income + expense
    conn.execute("UPDATE accounts SET opening_balance = ? WHERE id = ?", (opening, account_id))
    conn.commit()
    conn.close()
    return fetch_accounts()


@router.get("/summary")
def summary(month: str, user: dict = Depends(require_staff)):
    if len(month) != 7:
        raise HTTPException(400, "Месяц в формате YYYY-MM")
    return fetch_summary(month)


@router.get("/operations")
def list_operations(month: str, user: dict = Depends(require_staff)):
    refresh_overdue()
    year, mon = month.split("-")
    start = f"{year}-{mon}-01"
    if mon == "12":
        end = f"{int(year) + 1}-01-01"
    else:
        end = f"{year}-{int(mon) + 1:02d}-01"
    conn = get_conn()
    rows = conn.execute(
        OPS_SELECT
        + """
        WHERE op_date >= ? AND op_date < ?
        ORDER BY op_date DESC, id DESC
        """,
        (start, end),
    ).fetchall()
    conn.close()
    return [row_to_dict(row) for row in rows]


@router.post("/operations")
def create_operation(payload: OperationIn, user: dict = Depends(require_staff)):
    _validate_payload(payload)
    status = payload.status
    if status == "plan" and date.fromisoformat(payload.op_date) < date.today():
        status = "overdue"
    conn = get_conn()
    if not _account_exists(conn, payload.account_id):
        conn.close()
        raise HTTPException(400, "Неизвестный счёт")
    cur = conn.execute(
        """
        INSERT INTO operations (type, status, category, amount_rub, comment, op_date, created_by, account_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.type,
            status,
            payload.category,
            payload.amount_rub,
            payload.comment.strip(),
            payload.op_date,
            user["id"],
            payload.account_id,
        ),
    )
    conn.commit()
    row = conn.execute(OPS_SELECT + " WHERE operations.id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_to_dict(row)


@router.patch("/operations/{op_id}")
def update_status(op_id: int, payload: StatusIn, user: dict = Depends(require_staff)):
    conn = get_conn()
    row = conn.execute("SELECT * FROM operations WHERE id = ?", (op_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Операция не найдена")
    status = payload.status
    if status == "plan" and date.fromisoformat(row["op_date"]) < date.today():
        status = "overdue"
    conn.execute(
        "UPDATE operations SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, op_id),
    )
    conn.commit()
    row = conn.execute(OPS_SELECT + " WHERE operations.id = ?", (op_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


@router.delete("/operations/{op_id}")
def delete_operation(op_id: int, user: dict = Depends(require_staff)):
    conn = get_conn()
    cur = conn.execute("DELETE FROM operations WHERE id = ?", (op_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(404, "Операция не найдена")
    return {"ok": True}
