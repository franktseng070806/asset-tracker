import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_banks, get_cash_accounts, get_cash_transactions,
    add_cash_transaction, update_account_balance, delete_cash_transaction,
    save_snapshot,
)
from market import calc_total_net_worth_twd


def show(user_id: str):
    st.header("現金流水帳")

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

    st.subheader("新增記錄")

    with st.form("cash_entry", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tx_date = st.date_input("日期", value=date.today())
            tx_type = st.selectbox("類型", ["入金", "出金"])
            selected_label = st.selectbox("帳戶", list(account_options.keys()))
        with col2:
            amount = st.number_input("金額", min_value=0.0, step=1000.0)
            note = st.text_input("備註（選填）")

        submitted = st.form_submit_button("儲存", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("請輸入正確金額")
            else:
                acc = account_options[selected_label]
                account_id = int(acc["id"])
                delta = amount if tx_type == "入金" else -amount

                if tx_type == "出金" and acc["balance"] < amount:
                    st.error(f"餘額不足！目前餘額 {acc['currency']} {acc['balance']:,.2f}")
                else:
                    update_account_balance(account_id, delta)
                    add_cash_transaction(account_id, str(tx_date), tx_type, amount, note)
                    save_snapshot(user_id, calc_total_net_worth_twd(user_id))
                    st.success(f"已記錄 {tx_type} {acc['currency']} {amount:,.2f}")
                    st.rerun()

    st.markdown("---")

    st.subheader("流水帳記錄")

    tx = get_cash_transactions(user_id)

    if tx.empty:
        st.info("尚無現金記錄")
        return

    display_df = tx[["id", "date", "bank_name", "currency", "type", "amount", "note"]].copy()
    display_df.columns = ["ID", "日期", "銀行", "幣別", "類型", "金額", "備註"]

    st.dataframe(display_df.drop(columns=["ID"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    with st.expander("⚠️ 刪除現金記錄"):
        st.warning("刪除後會自動還原對應的帳戶餘額")

        tx_options = {
            f"{row['日期']}｜{row['類型']} {row['幣別']} {row['金額']:,.0f}　{row['備註']}": row["ID"]
            for _, row in display_df.iterrows()
        }
        selected_tx = st.selectbox("選擇要刪除的記錄", list(tx_options.keys()))

        if st.button("確認刪除", key="del_cash_tx"):
            tx_id = tx_options[selected_tx]
            delete_cash_transaction(tx_id)
            save_snapshot(user_id, calc_total_net_worth_twd(user_id))
            st.success("已刪除並還原對應的帳戶餘額")
            st.rerun()