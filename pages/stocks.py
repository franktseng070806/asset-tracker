import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_banks, get_cash_accounts, get_holdings,
    get_stock_transactions, add_stock_transaction,
    update_account_balance, buy_holding, sell_holding, delete_stock_transaction,
    save_snapshot,
)
from market import calc_total_net_worth_twd


def show(user_id: str):
    st.header("股票交易")

    banks = get_banks(user_id)
    all_accounts = get_cash_accounts(user_id)

    if banks.empty:
        st.info("請先到「帳戶管理」新增銀行帳戶")
        return

    account_options = {}
    for _, bank in banks.iterrows():
        for _, acc in all_accounts[all_accounts["bank_id"] == bank["id"]].iterrows():
            label = f"{bank['name']} - {acc['currency']}"
            account_options[label] = acc

    st.subheader("新增交易")

    with st.form("stock_trade", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            trade_date = st.date_input("交易日期", value=date.today())
            action = st.selectbox("買入／賣出", ["買入", "賣出"])
            ticker = st.text_input("股票代號（台股：0050.TW　美股：AAPL）")
        with col2:
            selected_label = st.selectbox("歸屬帳戶", list(account_options.keys()))
            price = st.number_input("交易價格（每股）", min_value=0.0, step=0.01)
            shares = st.number_input("數量（股）", min_value=0.0, step=1.0)
        fee = st.number_input("手續費", min_value=0.0, step=1.0, value=0.0)
        note = st.text_input("備註（選填）")
        submitted = st.form_submit_button("確認交易", use_container_width=True)

        if submitted:
            if not ticker:
                st.error("請輸入股票代號")
            elif price <= 0:
                st.error("請輸入正確的交易價格")
            elif shares <= 0:
                st.error("請輸入正確的股數")
            else:
                acc = account_options[selected_label]
                account_id = int(acc["id"])
                subtotal = price * shares
                total_cost = subtotal + fee if action == "買入" else subtotal - fee

                if action == "買入":
                    if acc["balance"] < total_cost:
                        st.error(
                            f"現金不足！目前餘額 {acc['currency']} {acc['balance']:,.2f}，"
                            f"需要 {acc['currency']} {total_cost:,.2f}（含手續費 {fee:,.2f}）"
                        )
                    else:
                        update_account_balance(account_id, -total_cost)
                        buy_holding(account_id, ticker.upper(), shares, price)
                        add_stock_transaction(account_id, str(trade_date), action, ticker.upper(), price, shares, fee, note)
                        save_snapshot(user_id, calc_total_net_worth_twd(user_id))
                        st.success(
                            f"買入 {ticker.upper()} {shares:.0f} 股，"
                            f"股票款 {acc['currency']} {subtotal:,.2f} + "
                            f"手續費 {acc['currency']} {fee:,.2f} = "
                            f"共扣款 {acc['currency']} {total_cost:,.2f}"
                        )
                        st.rerun()

                elif action == "賣出":
                    holdings = get_holdings(account_id)
                    existing = holdings[holdings["ticker"] == ticker.upper()]
                    current_shares = float(existing.iloc[0]["shares"]) if not existing.empty else 0

                    if current_shares < shares:
                        st.error(f"持股數量不足！目前持有 {current_shares:.0f} 股")
                    else:
                        update_account_balance(account_id, total_cost)
                        sell_holding(account_id, ticker.upper(),shares)
                        add_stock_transaction(account_id, str(trade_date), action, ticker.upper(), price, shares, fee, note)
                        save_snapshot(user_id, calc_total_net_worth_twd(user_id))
                        st.success(
                            f"賣出 {ticker.upper()} {shares:.0f} 股，"
                            f"股票款 {acc['currency']} {subtotal:,.2f} - "
                            f"手續費 {acc['currency']} {fee:,.2f} = "
                            f"實入帳 {acc['currency']} {total_cost:,.2f}"
                        )
                        st.rerun()

    st.markdown("---")

    st.subheader("交易記錄")

    tx = get_stock_transactions(user_id)

    if tx.empty:
        st.info("尚無交易記錄")
        return

    display_df = tx[["id", "date", "bank_name", "currency", "action", "ticker", "price", "shares", "fee", "note"]].copy()
    display_df.columns = ["ID", "日期", "銀行", "幣別", "買賣", "標的", "價格", "股數", "手續費", "備註"]
    display_df["總金額"] = (display_df["價格"] * display_df["股數"]).round(2)

    st.dataframe(display_df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    with st.expander("⚠️ 刪除交易記錄"):
        st.warning("刪除後會自動還原對應的現金與持股")

        tx_options = {
            f"{row['日期']}｜{row['買賣']} {row['標的']} {row['股數']:.0f}股 @{row['價格']}": row["ID"]
            for _, row in display_df.iterrows()
        }
        selected_tx = st.selectbox("選擇要刪除的記錄", list(tx_options.keys()))

        if st.button("確認刪除", key="del_stock_tx"):
            tx_id = tx_options[selected_tx]
            delete_stock_transaction(tx_id)
            save_snapshot(user_id, calc_total_net_worth_twd(user_id))
            st.success("已刪除並還原對應的現金與持股")
            st.rerun()