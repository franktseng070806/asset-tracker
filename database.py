import pandas as pd
import datetime
from supabase_client import get_supabase


def get_banks(user_id: str) -> pd.DataFrame:
    supabase = get_supabase()
    result = supabase.table("banks").select("*").eq("user_id", user_id).execute()
    return pd.DataFrame(result.data) if result.data else pd.DataFrame(columns=["id", "user_id", "name"])


def add_bank(user_id: str, name: str):
    supabase = get_supabase()
    bank_result = supabase.table("banks").insert({"user_id": user_id, "name": name}).execute()
    bank_id = bank_result.data[0]["id"]
    return bank_id


def add_cash_account(bank_id: int, currency: str, balance: float):
    supabase = get_supabase()
    supabase.table("cash_accounts").insert({
        "bank_id": bank_id, "currency": currency, "balance": balance
    }).execute()


def get_cash_accounts(user_id: str) -> pd.DataFrame:
    supabase = get_supabase()
    banks = get_banks(user_id)
    if banks.empty:
        return pd.DataFrame(columns=["id", "bank_id", "currency", "balance"])
    bank_ids = banks["id"].tolist()
    result = supabase.table("cash_accounts").select("*").in_("bank_id", bank_ids).execute()
    return pd.DataFrame(result.data) if result.data else pd.DataFrame(columns=["id", "bank_id", "currency", "balance"])


def update_account_balance(account_id: int, delta: float):
    supabase = get_supabase()
    current = supabase.table("cash_accounts").select("balance").eq("id", account_id).execute()
    new_balance = float(current.data[0]["balance"]) + delta
    supabase.table("cash_accounts").update({"balance": new_balance}).eq("id", account_id).execute()


def get_holdings(account_id: int) -> pd.DataFrame:
    supabase = get_supabase()
    result = supabase.table("stock_holdings").select("*").eq("account_id", account_id).gt("shares", 0).execute()
    return pd.DataFrame(result.data) if result.data else pd.DataFrame(columns=["id", "account_id", "ticker", "shares", "avg_cost"])


def buy_holding(account_id: int, ticker: str, shares: float, price: float):
    """買入：用加權平均法重新計算均價"""
    supabase = get_supabase()
    existing = supabase.table("stock_holdings").select("*").eq("account_id", account_id).eq("ticker", ticker).execute()
    if existing.data:
        old = existing.data[0]
        old_shares = float(old["shares"])
        old_avg = float(old["avg_cost"])
        new_shares = old_shares + shares
        new_avg = (old_shares * old_avg + shares * price) / new_shares if new_shares > 0 else price
        supabase.table("stock_holdings").update({"shares": new_shares, "avg_cost": new_avg}).eq("id", old["id"]).execute()
    else:
        supabase.table("stock_holdings").insert({
            "account_id": account_id, "ticker": ticker, "shares": shares, "avg_cost": price
        }).execute()


def sell_holding(account_id: int, ticker: str, shares: float):
    """賣出：均價不變，只減少股數"""
    supabase = get_supabase()
    existing = supabase.table("stock_holdings").select("*").eq("account_id", account_id).eq("ticker", ticker).execute()
    if existing.data:
        old = existing.data[0]
        new_shares = float(old["shares"]) - shares
        if new_shares <= 0:
            supabase.table("stock_holdings").delete().eq("id", old["id"]).execute()
        else:
            supabase.table("stock_holdings").update({"shares": new_shares}).eq("id", old["id"]).execute()


def upsert_holding(account_id: int, ticker: str, shares: float, avg_cost: float):
    """保留給帳戶管理頁面的初始持股輸入使用（直接設定股數與均價）"""
    supabase = get_supabase()
    existing = supabase.table("stock_holdings").select("*").eq("account_id", account_id).eq("ticker", ticker).execute()
    if existing.data:
        old = existing.data[0]
        old_shares = float(old["shares"])
        old_avg = float(old["avg_cost"])
        new_shares = old_shares + shares
        new_avg = (old_shares * old_avg + shares * avg_cost) / new_shares if new_shares > 0 else avg_cost
        supabase.table("stock_holdings").update({"shares": new_shares, "avg_cost": new_avg}).eq("id", old["id"]).execute()
    else:
        supabase.table("stock_holdings").insert({
            "account_id": account_id, "ticker": ticker, "shares": shares, "avg_cost": avg_cost
        }).execute()


def set_holding(holding_id: int, shares: float, avg_cost: float):
    supabase = get_supabase()
    if shares <= 0:
        supabase.table("stock_holdings").delete().eq("id", holding_id).execute()
    else:
        supabase.table("stock_holdings").update({"shares": shares, "avg_cost": avg_cost}).eq("id", holding_id).execute()


def delete_holding(holding_id: int):
    supabase = get_supabase()
    supabase.table("stock_holdings").delete().eq("id", holding_id).execute()


def add_cash_transaction(account_id: int, date: str, tx_type: str, amount: float, note: str):
    supabase = get_supabase()
    supabase.table("cash_transactions").insert({
        "account_id": account_id, "date": date, "type": tx_type, "amount": amount, "note": note
    }).execute()


def get_cash_transactions(user_id: str) -> pd.DataFrame:
    supabase = get_supabase()
    accounts = get_cash_accounts(user_id)
    banks = get_banks(user_id)
    if accounts.empty:
        return pd.DataFrame(columns=["id", "date", "account_id", "type", "amount", "note", "currency", "bank_name"])

    account_ids = accounts["id"].tolist()
    result = supabase.table("cash_transactions").select("*").in_("account_id", account_ids).order("date", desc=True).execute()
    df = pd.DataFrame(result.data) if result.data else pd.DataFrame(columns=["id", "date", "account_id", "type", "amount", "note"])

    if not df.empty:
        df = df.merge(accounts[["id", "currency", "bank_id"]], left_on="account_id", right_on="id", suffixes=("", "_acc"))
        df = df.merge(banks[["id", "name"]], left_on="bank_id", right_on="id", suffixes=("", "_bank"))
        df = df.rename(columns={"name": "bank_name"})
    return df


def delete_cash_transaction(tx_id: int):
    supabase = get_supabase()
    result = supabase.table("cash_transactions").select("*").eq("id", tx_id).execute()
    if result.data:
        row = result.data[0]
        delta = -row["amount"] if row["type"] == "入金" else row["amount"]
        update_account_balance(row["account_id"], delta)
        supabase.table("cash_transactions").delete().eq("id", tx_id).execute()


def add_stock_transaction(account_id: int, date: str, action: str, ticker: str, price: float, shares: float, fee: float, note: str):
    supabase = get_supabase()
    supabase.table("stock_transactions").insert({
        "account_id": account_id, "date": date, "action": action, "ticker": ticker,
        "price": price, "shares": shares, "fee": fee, "note": note
    }).execute()


def get_stock_transactions(user_id: str) -> pd.DataFrame:
    supabase = get_supabase()
    accounts = get_cash_accounts(user_id)
    banks = get_banks(user_id)
    if accounts.empty:
        return pd.DataFrame(columns=["id", "date", "account_id", "action", "ticker", "price", "shares", "fee", "note", "currency", "bank_name"])

    account_ids = accounts["id"].tolist()
    result = supabase.table("stock_transactions").select("*").in_("account_id", account_ids).order("date", desc=True).execute()
    df = pd.DataFrame(result.data) if result.data else pd.DataFrame(columns=["id", "date", "account_id", "action", "ticker", "price", "shares", "fee", "note"])

    if not df.empty:
        df = df.merge(accounts[["id", "currency", "bank_id"]], left_on="account_id", right_on="id", suffixes=("", "_acc"))
        df = df.merge(banks[["id", "name"]], left_on="bank_id", right_on="id", suffixes=("", "_bank"))
        df = df.rename(columns={"name": "bank_name"})
    return df


def delete_stock_transaction(tx_id: int):
    supabase = get_supabase()
    result = supabase.table("stock_transactions").select("*").eq("id", tx_id).execute()
    if not result.data:
        return
    row = result.data[0]
    account_id, action, ticker, price, shares, fee = row["account_id"], row["action"], row["ticker"], row["price"], row["shares"], row["fee"]
    subtotal = price * shares

    if action == "買入":
        update_account_balance(account_id, subtotal + fee)
        existing = supabase.table("stock_holdings").select("*").eq("account_id", account_id).eq("ticker", ticker).execute()
        if existing.data:
            old = existing.data[0]
            new_shares = float(old["shares"]) - shares
            if new_shares <= 0:
                supabase.table("stock_holdings").delete().eq("id", old["id"]).execute()
            else:
                supabase.table("stock_holdings").update({"shares": new_shares}).eq("id", old["id"]).execute()

    elif action == "賣出":
        update_account_balance(account_id, -(subtotal - fee))
        existing = supabase.table("stock_holdings").select("*").eq("account_id", account_id).eq("ticker", ticker).execute()
        if existing.data:
            old = existing.data[0]
            new_shares = float(old["shares"]) + shares
            supabase.table("stock_holdings").update({"shares": new_shares}).eq("id", old["id"]).execute()
        else:
            supabase.table("stock_holdings").insert({
                "account_id": account_id, "ticker": ticker, "shares": shares, "avg_cost": price
            }).execute()

    supabase.table("stock_transactions").delete().eq("id", tx_id).execute()


def add_transfer(date: str, transfer_type: str, from_id: int, to_id: int, amount: float = None, ticker: str = None, shares: float = None, note: str = None):
    supabase = get_supabase()
    supabase.table("transfers").insert({
        "date": date, "type": transfer_type, "from_account_id": from_id, "to_account_id": to_id,
        "amount": amount, "ticker": ticker, "shares": shares, "note": note
    }).execute()


def get_all_transfers(user_id: str) -> pd.DataFrame:
    supabase = get_supabase()
    accounts = get_cash_accounts(user_id)
    if accounts.empty:
        return pd.DataFrame(columns=["id", "date", "type", "from_account_id", "to_account_id", "amount", "ticker", "shares", "note"])
    account_ids = accounts["id"].tolist()
    result = supabase.table("transfers").select("*").in_("from_account_id", account_ids).order("date", desc=True).execute()
    return pd.DataFrame(result.data) if result.data else pd.DataFrame(columns=["id", "date", "type", "from_account_id", "to_account_id", "amount", "ticker", "shares", "note"])


def delete_transfer(tx_id: int):
    supabase = get_supabase()
    result = supabase.table("transfers").select("*").eq("id", tx_id).execute()
    if not result.data:
        return
    row = result.data[0]
    tx_type, from_id, to_id, amount, ticker, shares, note = (
        row["type"], row["from_account_id"], row["to_account_id"],
        row["amount"], row["ticker"], row["shares"], row["note"]
    )

    if tx_type == "現金轉帳":
        update_account_balance(from_id, amount)
        update_account_balance(to_id, -amount)
    elif tx_type == "換匯TWD→USD":
        usd_amount = float(note.split("換得USD")[1])
        update_account_balance(from_id, amount)
        update_account_balance(to_id, -usd_amount)
    elif tx_type == "換匯USD→TWD":
        twd_amount = float(note.split("換得TWD")[1])
        update_account_balance(from_id, amount)
        update_account_balance(to_id, -twd_amount)
    elif tx_type == "股票轉移":
        existing_from = supabase.table("stock_holdings").select("*").eq("account_id", from_id).eq("ticker", ticker).execute()
        if existing_from.data:
            old = existing_from.data[0]
            supabase.table("stock_holdings").update({"shares": float(old["shares"]) + shares}).eq("id", old["id"]).execute()
        else:
            supabase.table("stock_holdings").insert({"account_id": from_id, "ticker": ticker, "shares": shares, "avg_cost": 0}).execute()

        existing_to = supabase.table("stock_holdings").select("*").eq("account_id", to_id).eq("ticker", ticker).execute()
        if existing_to.data:
            old = existing_to.data[0]
            new_shares = float(old["shares"]) - shares
            if new_shares <= 0:
                supabase.table("stock_holdings").delete().eq("id", old["id"]).execute()
            else:
                supabase.table("stock_holdings").update({"shares": new_shares}).eq("id", old["id"]).execute()

    supabase.table("transfers").delete().eq("id", tx_id).execute()


def delete_bank(bank_id: int):
    supabase = get_supabase()
    accounts = supabase.table("cash_accounts").select("id").eq("bank_id", bank_id).execute()
    account_ids = [a["id"] for a in accounts.data] if accounts.data else []

    for account_id in account_ids:
        supabase.table("stock_holdings").delete().eq("account_id", account_id).execute()
        supabase.table("cash_transactions").delete().eq("account_id", account_id).execute()
        supabase.table("stock_transactions").delete().eq("account_id", account_id).execute()
        supabase.table("transfers").delete().eq("from_account_id", account_id).execute()
        supabase.table("transfers").delete().eq("to_account_id", account_id).execute()

    supabase.table("cash_accounts").delete().eq("bank_id", bank_id).execute()
    supabase.table("banks").delete().eq("id", bank_id).execute()


def save_snapshot(user_id: str, net_worth_twd: float):
    supabase = get_supabase()
    today = datetime.date.today().isoformat()
    supabase.table("net_worth_snapshots").delete().eq("user_id", user_id).eq("date", today).execute()
    supabase.table("net_worth_snapshots").insert({
        "user_id": user_id, "date": today, "net_worth": net_worth_twd
    }).execute()


def get_snapshots(user_id: str) -> pd.DataFrame:
    supabase = get_supabase()
    result = supabase.table("net_worth_snapshots").select("*").eq("user_id", user_id).order("date").execute()
    return pd.DataFrame(result.data) if result.data else pd.DataFrame(columns=["id", "user_id", "date", "net_worth"])