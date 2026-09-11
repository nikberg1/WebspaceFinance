from __future__ import annotations

from datetime import date

from app.db import get_conn


def refresh_overdue() -> None:
    today = date.today().isoformat()
    conn = get_conn()
    conn.execute(
        """
        UPDATE operations
        SET status = 'overdue', updated_at = datetime('now')
        WHERE status = 'plan' AND op_date < ?
        """,
        (today,),
    )
    conn.commit()
    conn.close()


def month_bounds(month: str) -> tuple[str, str]:
    year, mon = month.split("-")
    start = f"{year}-{mon}-01"
    if mon == "12":
        end = f"{int(year) + 1}-01-01"
    else:
        end = f"{year}-{int(mon) + 1:02d}-01"
    return start, end


def fetch_accounts() -> list[dict]:
    conn = get_conn()
    accounts = conn.execute("SELECT * FROM accounts ORDER BY id").fetchall()
    moves = conn.execute(
        """
        SELECT account_id, type, SUM(amount_rub) AS total
        FROM operations
        WHERE status = 'paid'
        GROUP BY account_id, type
        """
    ).fetchall()
    conn.close()

    by_acc: dict[int, dict[str, int]] = {}
    for row in moves:
        by_acc.setdefault(row["account_id"], {"income": 0, "expense": 0})
        by_acc[row["account_id"]][row["type"]] = row["total"] or 0

    result = []
    total = 0
    for acc in accounts:
        flow = by_acc.get(acc["id"], {"income": 0, "expense": 0})
        balance = acc["opening_balance"] + flow["income"] - flow["expense"]
        total += balance
        result.append(
            {
                "id": acc["id"],
                "slug": acc["slug"],
                "name": acc["name"],
                "opening_balance": acc["opening_balance"],
                "balance": balance,
            }
        )
    return result


def fetch_summary(month: str) -> dict:
    refresh_overdue()
    start, end = month_bounds(month)
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT type, status, SUM(amount_rub) AS total
        FROM operations
        WHERE op_date >= ? AND op_date < ?
        GROUP BY type, status
        """,
        (start, end),
    ).fetchall()
    conn.close()

    data = {
        "paid_income": 0,
        "paid_expense": 0,
        "plan_income": 0,
        "plan_expense": 0,
        "overdue_income": 0,
        "overdue_expense": 0,
    }
    for row in rows:
        key = f"{row['status']}_{row['type']}"
        if key in data:
            data[key] = row["total"] or 0

    accounts = fetch_accounts()
    data["profit"] = data["paid_income"] - data["paid_expense"]
    data["expected_in"] = data["plan_income"] + data["overdue_income"]
    data["expected_out"] = data["plan_expense"] + data["overdue_expense"]
    data["month"] = month
    data["accounts"] = accounts
    data["total_balance"] = sum(a["balance"] for a in accounts)
    return data


def row_to_dict(row) -> dict:
    keys = row.keys()
    return {
        "id": row["id"],
        "type": row["type"],
        "status": row["status"],
        "category": row["category"],
        "amount_rub": row["amount_rub"],
        "comment": row["comment"],
        "op_date": row["op_date"],
        "account_id": row["account_id"] if "account_id" in keys else None,
        "account_name": row["account_name"] if "account_name" in keys else None,
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
