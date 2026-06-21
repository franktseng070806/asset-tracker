import streamlit as st
from database import (
    get_banks, get_cash_accounts, get_holdings,
    add_bank, add_cash_account, upsert_holding,
    set_holding, delete_holding, delete_bank,
)
from market import get_price


def show(user_id: str):
    st.header("帳戶管理")

    # ── 新增銀行帳戶 ────────────────────────────────────────
    st.subheader("新增銀行帳戶")

    with st.form("add_bank"):
        bank_name = st.text_input("銀行名稱（例：玉山銀行）")
        twd_init = st.number_input("台幣現金初始餘額", min_value=0.0, step=1000.0)
        usd_init = st.number_input("美元現金初始餘額", min_value=0.0, step=100.0)
        submitted = st.form_submit_button("新增帳戶")

        if submitted and bank_name:
            try:
                bank_id = add_bank(user_id, bank_name)
                add_cash_account(bank_id, "TWD", twd_init)
                add_cash_account(bank_id, "USD", usd_init)
                st.success(f"已新增「{bank_name}」")
                st.rerun()
            except Exception as e:
                st.error(f"新增失敗：{e}")

    st.markdown("---")

    # ── 現有帳戶一覽 ────────────────────────────────────────
    st.subheader("現有帳戶")

    banks = get_banks(user_id)
    all_accounts = get_cash_accounts(user_id)

    if banks.empty:
        st.info("尚無帳戶，請在上方新增")
        return

    for _, bank in banks.iterrows():
        st.markdown(f"### 🏦 {bank['name']}")
        bank_accounts = all_accounts[all_accounts["bank_id"] == bank["id"]]

        col1, col2 = st.columns(2)
        for i, (_, acc) in enumerate(bank_accounts.iterrows()):
            holdings = get_holdings(acc["id"])
            stock_value = sum(
                get_price(h["ticker"]) * h["shares"]
                for _, h in holdings.iterrows()
            )
            total = acc["balance"] + stock_value

            with (col1 if i == 0 else col2):
                st.metric(
                    f"{acc['currency']} 子帳戶",
                    f"{acc['currency']} {total:,.2f}",
                    delta=f"現金 {acc['balance']:,.2f}　股票 {stock_value:,.2f}",
                )

        st.markdown("---")

        # ── 持股管理 ────────────────────────────────────────
        st.markdown(f"#### 持股管理（{bank['name']}）")

        all_holdings = []
        for _, acc in bank_accounts.iterrows():
            holdings = get_holdings(acc["id"])
            for _, h in holdings.iterrows():
                all_holdings.append({
                    "id": int(h["id"]),
                    "account_id": int(acc["id"]),
                    "currency": acc["currency"],
                    "ticker": h["ticker"],
                    "shares": h["shares"],
                    "avg_cost": h["avg_cost"],
                })

        with st.expander(f"➕ 新增持股"):
            with st.form(f"init_stock_{bank['id']}"):
                acc_options = {
                    acc["currency"]: int(acc["id"])
                    for _, acc in bank_accounts.iterrows()
                }
                selected_currency = st.selectbox(
                    "幣別", list(acc_options.keys()), key=f"cur_{bank['id']}"
                )
                ticker = st.text_input(
                    "股票代號（台股：0050.TW　美股：AAPL）",
                    key=f"ticker_{bank['id']}",
                )
                shares = st.number_input(
                    "持有股數", min_value=0.0, step=1.0, key=f"shares_{bank['id']}"
                )
                avg_cost = st.number_input(
                    "平均成本（每股）",
                    min_value=0.0,
                    step=0.01,
                    key=f"cost_{bank['id']}",
                )
                submitted = st.form_submit_button("新增持股")

                if submitted and ticker and shares > 0:
                    account_id = acc_options[selected_currency]
                    upsert_holding(account_id, ticker.upper(), shares, avg_cost)
                    st.success(f"已新增 {ticker.upper()} {shares:.0f} 股")
                    st.rerun()

        if all_holdings:
            st.markdown("**編輯／刪除現有持股**")

            holding_options = {
                f"{h['ticker']}｜{h['shares']:.0f} 股｜均價 {h['avg_cost']:.2f}｜{h['currency']}": h
                for h in all_holdings
            }

            selected_label = st.selectbox(
                "選擇持股",
                list(holding_options.keys()),
                key=f"select_holding_{bank['id']}",
            )
            selected_holding = holding_options[selected_label]

            action_col, _ = st.columns([2, 3])
            with action_col:
                action = st.radio(
                    "操作",
                    ["編輯", "刪除"],
                    horizontal=True,
                    key=f"action_{bank['id']}",
                )

            if action == "刪除":
                if st.button("確認刪除", key=f"confirm_del_{bank['id']}"):
                    delete_holding(selected_holding["id"])
                    st.success(f"已刪除 {selected_holding['ticker']}")
                    st.rerun()

            elif action == "編輯":
                with st.form(key=f"edit_holding_{bank['id']}"):
                    new_shares = st.number_input(
                        "修改股數",
                        min_value=0.0,
                        step=1.0,
                        value=float(selected_holding["shares"]),
                    )
                    new_avg_cost = st.number_input(
                        "修改平均成本",
                        min_value=0.0,
                        step=0.01,
                        value=float(selected_holding["avg_cost"]),
                    )
                    save_col, cancel_col = st.columns(2)
                    with save_col:
                        save = st.form_submit_button("✅ 儲存", use_container_width=True)
                    with cancel_col:
                        cancel = st.form_submit_button("❌ 取消", use_container_width=True)

                    if save:
                        set_holding(selected_holding["id"], new_shares, new_avg_cost)
                        st.success(f"已更新 {selected_holding['ticker']}")
                        st.rerun()

                    if cancel:
                        st.rerun()
        else:
            st.info("尚無持股，請在上方新增")

        st.markdown("---")

    # ── 刪除銀行帳戶 ────────────────────────────────────────
    st.markdown("---")
    st.subheader("刪除銀行帳戶")

    with st.expander("⚠️ 刪除帳戶（不可復原）"):
        st.warning("刪除後該帳戶所有資料將永久清除，包含持股、交易記錄、流水帳")

        bank_options = {bank["name"]: int(bank["id"]) for _, bank in banks.iterrows()}
        selected_bank_name = st.selectbox("選擇要刪除的銀行帳戶", list(bank_options.keys()), key="del_bank_select")

        confirm_name = st.text_input("請輸入銀行名稱確認刪除", placeholder=f"輸入「{selected_bank_name}」確認")

        if st.button("確認刪除帳戶", key="del_bank_btn"):
            if confirm_name != selected_bank_name:
                st.error("名稱不符，請重新輸入")
            else:
                bank_id = bank_options[selected_bank_name]
                delete_bank(bank_id)
                st.success(f"已刪除「{selected_bank_name}」及所有相關資料")
                st.rerun()