"""
一次性資料搬移程式：把本機 assets.db 的資料轉移到 Supabase
使用方式：在「資產追蹤」資料夾的終端機輸入 python migrate.py
"""

import sqlite3
from supabase_client import get_supabase

TARGET_EMAIL = "a0920230573@gmail.com"
DB_FILE = "assets.db"


def main():
    supabase = get_supabase()

    # ── 找到目標使用者的 user_id ─────────────────────────────
    user_result = supabase.table("users").select("id").eq("email", TARGET_EMAIL).execute()
    if not user_result.data:
        print(f"找不到帳號 {TARGET_EMAIL}，請先在雲端 app 上註冊這個帳號")
        return
    user_id = user_result.data[0]["id"]
    print(f"找到使用者 user_id = {user_id}")

    # ── 連接本機 SQLite ──────────────────────────────────────
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # ── 搬移銀行帳戶，並記錄舊id -> 新id 的對應 ──────────────
    bank_id_map = {}
    banks = c.execute("SELECT id, name FROM banks").fetchall()
    for old_id, name in banks:
        result = supabase.table("banks").insert({"user_id": user_id, "name": name}).execute()
        new_id = result.data[0]["id"]
        bank_id_map[old_id] = new_id
        print(f"搬移銀行帳戶：{name}")

    # ── 搬移現金子帳戶 ───────────────────────────────────────
    account_id_map = {}
    accounts = c.execute("SELECT id, bank_id, currency, balance FROM cash_accounts").fetchall()
    for old_id, bank_id, currency, balance in accounts:
        new_bank_id = bank_id_map[bank_id]
        result = supabase.table("cash_accounts").insert({
            "bank_id": new_bank_id, "currency": currency, "balance": balance
        }).execute()
        new_id = result.data[0]["id"]
        account_id_map[old_id] = new_id
        print(f"搬移子帳戶：{currency}")

    # ── 搬移持股 ─────────────────────────────────────────────
    holdings = c.execute("SELECT account_id, ticker, shares, avg_cost FROM stock_holdings").fetchall()
    for account_id, ticker, shares, avg_cost in holdings:
        new_account_id = account_id_map[account_id]
        supabase.table("stock_holdings").insert({
            "account_id": new_account_id, "ticker": ticker, "shares": shares, "avg_cost": avg_cost
        }).execute()
        print(f"搬移持股：{ticker} {shares}股")

    # ── 搬移現金流水帳 ───────────────────────────────────────
    cash_tx = c.execute("SELECT date, account_id, type, amount, note FROM cash_transactions").fetchall()
    for date, account_id, tx_type, amount, note in cash_tx:
        new_account_id = account_id_map[account_id]
        supabase.table("cash_transactions").insert({
            "date": date, "account_id": new_account_id, "type": tx_type, "amount": amount, "note": note
        }).execute()
    print(f"搬移現金流水帳：{len(cash_tx)} 筆")

    # ── 搬移股票交易記錄 ─────────────────────────────────────
    stock_tx = c.execute("SELECT date, account_id, action, ticker, price, shares, fee, note FROM stock_transactions").fetchall()
    for date, account_id, action, ticker, price, shares, fee, note in stock_tx:
        new_account_id = account_id_map[account_id]
        supabase.table("stock_transactions").insert({
            "date": date, "account_id": new_account_id, "action": action, "ticker": ticker,
            "price": price, "shares": shares, "fee": fee, "note": note
        }).execute()
    print(f"搬移股票交易記錄：{len(stock_tx)} 筆")

    # ── 搬移轉移記錄 ─────────────────────────────────────────
    transfers = c.execute(
        "SELECT date, type, from_account_id, to_account_id, amount, ticker, shares, note FROM transfers"
    ).fetchall()
    for date, t_type, from_id, to_id, amount, ticker, shares, note in transfers:
        new_from_id = account_id_map.get(from_id)
        new_to_id = account_id_map.get(to_id)
        supabase.table("transfers").insert({
            "date": date, "type": t_type, "from_account_id": new_from_id, "to_account_id": new_to_id,
            "amount": amount, "ticker": ticker, "shares": shares, "note": note
        }).execute()
    print(f"搬移轉移記錄：{len(transfers)} 筆")

    # ── 搬移淨值快照 ─────────────────────────────────────────
    snapshots = c.execute("SELECT date, net_worth FROM net_worth_snapshots").fetchall()
    for date, net_worth in snapshots:
        supabase.table("net_worth_snapshots").insert({
            "user_id": user_id, "date": date, "net_worth": net_worth
        }).execute()
    print(f"搬移淨值快照：{len(snapshots)} 筆")

    conn.close()
    print("\n✅ 搬移完成！請到雲端 app 確認資料是否正確")


if __name__ == "__main__":
    main()