import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_banks, get_cash_accounts, get_holdings,
    get_all_transfers, add_transfer, update_account_balance,
    upsert_holding, delete_transfer, save_snapshot,
)
from market import get_usd_twd, calc_total_net_worth_twd


def show(user_id: str):
    st.header("資產轉移")

    banks = get_banks(user_id)
    all_accounts = get_cash_accounts(user_id)

    if banks.empty:
        st.info("請先到「帳戶管理」新增銀行帳戶")
        return

    usd_twd = get_usd_twd()

    account_options = {}
    for _, bank in banks.iterrows():
        for _, acc in all_accounts[all_accounts["bank_id"] == bank["id"]].iterrows():
            label = f"{bank['name']} - {acc['currency']}"
            account_options[label] = acc

    transfer_type = st.selectbox("轉移類型", ["現金轉帳", "換匯（台幣⇄美元）", "股票轉移"])

    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # 現金轉帳
    # ════════════════════════════════════════════════════════
    if transfer_type == "現金轉帳":
        st.subheader("現金轉帳")

        with st.form("cash_transfer", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                from_label = st.selectbox("從", list(account_options.keys()), key="from")
                amount = st.number_input("金額", min_value=0.0, step=1000.0)
            with col2:
                to_label = st.selectbox("到", list(account_options.keys()), key="to")
                note = st.text_input("備註（選填）")
            tx_date = st.date_input("日期", value=date.today())
            submitted = st.form_submit_button("確認轉帳", use_container_width=True)

            if submitted:
                from_acc = account_options[from_label]
                to_acc = account_options[to_label]

                if int(from_acc["id"]) == int(to_acc["id"]):
                    st.error("來源和目標帳戶不能相同")
                elif amount <= 0:
                    st.error("請輸入正確金額")
                elif from_acc["balance"] < amount:
                    st.error(f"餘額不足！目前餘額 {from_acc['currency']} {from_acc['balance']:,.2f}")
                else:
                    update_account_balance(int(from_acc["id"]), -amount)
                    update_account_balance(int(to_acc["id"]), amount)
                    add_transfer(str(tx_date), "現金轉帳", int(from_acc["id"]), int(to_acc["id"]), amount=amount, note=note)
                    save_snapshot(user_id, calc_total_net_worth_twd(user_id))
                    st.success(f"轉帳完成：{from_label} → {to_label}　{from_acc['currency']} {amount:,.2f}")
                    st.rerun()

    # ════════════════════════════════════════════════════════
    # 換匯
    # ════════════════════════════════════════════════════════
    elif transfer_type == "換匯（台幣⇄美元）":
        st.subheader("換匯")

        banks_list = banks["name"].tolist()
        selected_bank = st.selectbox("選擇銀行", banks_list)
        bank_id = int(banks[banks["name"] == selected_bank]["id"].values[0])
        bank_accounts = all_accounts[all_accounts["bank_id"] == bank_id]
        twd_acc = bank_accounts[bank_accounts["currency"] == "TWD"].iloc[0]
        usd_acc = bank_accounts[bank_accounts["currency"] == "USD"].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            st.metric("台幣餘額", f"TWD {twd_acc['balance']:,.2f}")
        with col2:
            st.metric("美元餘額", f"USD {usd_acc['balance']:,.2f}")

        with st.form("fx_transfer", clear_on_submit=True):
            direction = st.selectbox("換匯方向", ["台幣 → 美元", "美元 → 台幣"])
            rate = st.number_input("換匯匯率（1 USD = ? TWD）", value=float(usd_twd), step=0.01)
            amount = st.number_input("換出金額", min_value=0.0, step=1000.0)
            tx_date = st.date_input("日期", value=date.today())

            if direction == "台幣 → 美元" and amount > 0:
                st.caption(f"預計換得 USD {amount / rate:,.2f}")
            elif direction == "美元 → 台幣" and amount > 0:
                st.caption(f"預計換得 TWD {amount * rate:,.2f}")

            submitted = st.form_submit_button("確認換匯", use_container_width=True)

            if submitted:
                if amount <= 0:
                    st.error("請輸入正確金額")
                elif direction == "台幣 → 美元":
                    usd_amount = amount / rate
                    if twd_acc["balance"] < amount:
                        st.error(f"台幣餘額不足！目前餘額 TWD {twd_acc['balance']:,.2f}")
                    else:
                        update_account_balance(int(twd_acc["id"]), -amount)
                        update_account_balance(int(usd_acc["id"]), usd_amount)
                        add_transfer(str(tx_date), "換匯TWD→USD", int(twd_acc["id"]), int(usd_acc["id"]),
                                     amount=amount, note=f"匯率{rate}｜換得USD{usd_amount:.2f}")
                        save_snapshot(user_id, calc_total_net_worth_twd(user_id))
                        st.success(f"換匯完成：TWD {amount:,.0f} → USD {usd_amount:,.2f}")
                        st.rerun()
                else:
                    twd_amount = amount * rate
                    if usd_acc["balance"] < amount:
                        st.error(f"美元餘額不足！目前餘額 USD {usd_acc['balance']:,.2f}")
                    else:
                        update_account_balance(int(usd_acc["id"]), -amount)
                        update_account_balance(int(twd_acc["id"]), twd_amount)
                        add_transfer(str(tx_date), "換匯USD→TWD", int(usd_acc["id"]), int(twd_acc["id"]),
                                     amount=amount, note=f"匯率{rate}｜換得TWD{twd_amount:.0f}")
                        save_snapshot(user_id, calc_total_net_worth_twd(user_id))
                        st.success(f"換匯完成：USD {amount:,.2f} → TWD {twd_amount:,.0f}")
                        st.rerun()

    # ════════════════════════════════════════════════════════
    # 股票轉移
    # ════════════════════════════════════════════════════════
    elif transfer_type == "股票轉移":
        st.subheader("股票轉移")

        with st.form("stock_transfer", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                from_label = st.selectbox("從", list(account_options.keys()), key="sfrom")
            with col2:
                to_label = st.selectbox("到", list(account_options.keys()), key="sto")
            ticker = st.text_input("股票代號")
            shares = st.number_input("股數", min_value=0.0, step=1.0)
            tx_date = st.date_input("日期", value=date.today())
            submitted = st.form_submit_button("確認轉移", use_container_width=True)

            if submitted:
                if not ticker:
                    st.error("請輸入股票代號")
                elif shares <= 0:
                    st.error("請輸入正確股數")
                else:
                    from_acc = account_options[from_label]
                    to_acc = account_options[to_label]

                    if int(from_acc["id"]) == int(to_acc["id"]):
                        st.error("來源和目標帳戶不能相同")
                    else:
                        holdings = get_holdings(int(from_acc["id"]))
                        existing = holdings[holdings["ticker"] == ticker.upper()]
                        current_shares = float(existing.iloc[0]["shares"]) if not existing.empty else 0
                        avg_cost = float(existing.iloc[0]["avg_cost"]) if not existing.empty else 0

                        if current_shares < shares:
                            st.error(f"持股不足！目前持有 {current_shares:.0f} 股")
                        else:
                            upsert_holding(int(from_acc["id"]), ticker.upper(), -shares, avg_cost)
                            upsert_holding(int(to_acc["id"]), ticker.upper(), shares, avg_cost)
                            add_transfer(str(tx_date), "股票轉移", int(from_acc["id"]), int(to_acc["id"]),
                                         ticker=ticker.upper(), shares=shares)
                            save_snapshot(user_id, calc_total_net_worth_twd(user_id))
                            st.success(f"已轉移 {ticker.upper()} {shares:.0f} 股")
                            st.rerun()

    # ════════════════════════════════════════════════════════
    # 轉移記錄與刪除
    # ════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("轉移記錄")

    transfers = get_all_transfers(user_id)

    if transfers.empty:
        st.info("尚無轉移記錄")
        return

    st.dataframe(transfers.drop(columns=["id"]), use_container_width=True, hide_index=True)

    with st.expander("⚠️ 刪除轉移記錄"):
        st.warning("刪除後會自動還原對應的帳戶餘額或持股")

        tx_options = {}
        for _, row in transfers.iterrows():
            if row["type"] == "股票轉移":
                label = f"{row['date']}｜{row['type']} {row['ticker']} {row['shares']:.0f}股"
            else:
                label = f"{row['date']}｜{row['type']} {row['amount']:,.0f}　{row['note'] or ''}"
            tx_options[label] = row["id"]

        selected_tx = st.selectbox("選擇要刪除的記錄", list(tx_options.keys()))

        if st.button("確認刪除", key="del_transfer"):
            tx_id = tx_options[selected_tx]
            delete_transfer(tx_id)
            save_snapshot(user_id, calc_total_net_worth_twd(user_id))
            st.success("已刪除並還原對應資產")
            st.rerun()