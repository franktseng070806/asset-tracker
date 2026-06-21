import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from database import get_banks, get_cash_accounts, get_holdings, get_cash_transactions, get_snapshots
from market import get_usd_twd, get_price, calc_total_net_worth_twd


def show(user_id: str):
    st.header("總覽")

    usd_twd = get_usd_twd()
    banks = get_banks(user_id)

    if banks.empty:
        st.info("還沒有帳戶，請先到「帳戶管理」新增銀行帳戶")
        return

    all_accounts = get_cash_accounts(user_id)

    # ── 預先批次抓取所有股票價格 ───────────────────────────
    all_tickers = set()
    holdings_cache = {}
    for _, acc in all_accounts.iterrows():
        holdings = get_holdings(int(acc["id"]))
        holdings_cache[int(acc["id"])] = holdings
        all_tickers.update(holdings["ticker"].tolist())

    from market import get_prices_batch
    price_cache = get_prices_batch(tuple(all_tickers))

    def price_lookup(ticker):
        return price_cache.get(ticker, 0.0)

    # ── 側邊欄統計範圍 ──────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("統計範圍")

    scope_options = ["總資產"]
    scope_map = {}

    for _, bank in banks.iterrows():
        scope_options.append(bank["name"])
        scope_map[bank["name"]] = {"type": "bank", "bank_id": int(bank["id"])}
        bank_accounts = all_accounts[all_accounts["bank_id"] == bank["id"]]
        for _, acc in bank_accounts.iterrows():
            label = f"{bank['name']} - {acc['currency']}"
            scope_options.append(label)
            scope_map[label] = {
                "type": "account",
                "account_id": int(acc["id"]),
                "currency": acc["currency"],
            }

    selected_scope = st.sidebar.selectbox("選擇範圍", scope_options)

    is_usd_only = (
        selected_scope in scope_map and
        scope_map[selected_scope]["type"] == "account" and
        scope_map[selected_scope]["currency"] == "USD"
    )

    if selected_scope == "總資產":
        scoped_rows = [row for _, row in all_accounts.iterrows()]
    elif scope_map[selected_scope]["type"] == "bank":
        bank_id = scope_map[selected_scope]["bank_id"]
        scoped_rows = [row for _, row in all_accounts.iterrows() if int(row["bank_id"]) == bank_id]
    else:
        account_id = scope_map[selected_scope]["account_id"]
        scoped_rows = [row for _, row in all_accounts.iterrows() if int(row["id"]) == account_id]

    scoped_total_twd = 0.0
    scoped_total_usd = 0.0
    pie_data = []
    holding_details = []

    for acc in scoped_rows:
        cash = float(acc["balance"])
        holdings = holdings_cache[int(acc["id"])]
        stock_value = 0.0

        for _, h in holdings.iterrows():
            price = price_lookup(h["ticker"])
            value = price * float(h["shares"])
            stock_value += value

            if is_usd_only:
                pie_data.append({"標的": h["ticker"], "市值": value})
            else:
                value_twd = value * usd_twd if acc["currency"] == "USD" else value
                pie_data.append({"標的": h["ticker"], "市值": value_twd})

            holding_details.append({
                "標的": h["ticker"],
                "幣別": acc["currency"],
                "股數": float(h["shares"]),
                "均價": float(h["avg_cost"]),
                "現價": price,
                "市值_原幣": value,
                "市值_twd": value * usd_twd if acc["currency"] == "USD" else value,
                "損益_原幣": (price - float(h["avg_cost"])) * float(h["shares"]),
                "損益%": (price / float(h["avg_cost"]) - 1) * 100 if float(h["avg_cost"]) > 0 else 0.0,
            })

        if is_usd_only:
            pie_data.append({"標的": "現金（USD）", "市值": cash})
        else:
            cash_twd = cash * usd_twd if acc["currency"] == "USD" else cash
            if cash_twd > 0:
                pie_data.append({"標的": f"現金（{acc['currency']}）", "市值": cash_twd})

        sub_total_usd = cash + stock_value if acc["currency"] == "USD" else (cash + stock_value) / usd_twd
        sub_total_twd = (cash + stock_value) * usd_twd if acc["currency"] == "USD" else cash + stock_value
        scoped_total_twd += sub_total_twd
        scoped_total_usd += sub_total_usd

    if is_usd_only:
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric(f"{selected_scope} 總值（台幣）", f"NT$ {scoped_total_twd:,.0f}")
        with col_b:
            st.metric(f"{selected_scope} 總值（美元）", f"USD {scoped_total_usd:,.2f}")
    else:
        st.metric(f"{selected_scope} 總值", f"NT$ {scoped_total_twd:,.0f}")

    st.caption(f"即時匯率 USD/TWD：{usd_twd}")
    st.markdown("---")

    if selected_scope == "總資產":
        bank_totals = {}
        for _, bank in banks.iterrows():
            bank_accounts = all_accounts[all_accounts["bank_id"] == bank["id"]]
            bank_total = 0.0
            for _, acc in bank_accounts.iterrows():
                holdings = holdings_cache[int(acc["id"])]
                stock_value = sum(price_lookup(h["ticker"]) * float(h["shares"]) for _, h in holdings.iterrows())
                sub_total = float(acc["balance"]) + stock_value
                if acc["currency"] == "USD":
                    sub_total *= usd_twd
                bank_total += sub_total
            bank_totals[bank["name"]] = bank_total

        cols = st.columns(len(bank_totals))
        for i, (bank_name, total) in enumerate(bank_totals.items()):
            with cols[i]:
                st.metric(bank_name, f"NT$ {total:,.0f}")
        st.markdown("---")

    tab1, tab2 = st.tabs(["📊 資產配置", "📈 報酬率分析"])

    with tab1:
        chart_mode = st.radio("顯示模式", ["圓餅圖", "持股明細", "兩者都顯示"], horizontal=True)

        if not pie_data:
            st.info("尚無資產資料")
        else:
            pie_df = pd.DataFrame(pie_data)
            pie_df = pie_df.groupby("標的")["市值"].sum().reset_index()
            pie_df = pie_df[pie_df["市值"] > 0]
            pie_unit = "USD" if is_usd_only else "NT$"

            def render_pie():
                fig = px.pie(pie_df, values="市值", names="標的", hole=0.5)
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=400, paper_bgcolor="rgba(0,0,0,0)")
                fig.update_traces(textinfo="percent+label")
                st.caption(f"市值單位：{pie_unit}")
                st.plotly_chart(fig, use_container_width=True)

            def render_holdings():
                if holding_details:
                    detail_df = pd.DataFrame(holding_details)
                    detail_df["股數"] = detail_df["股數"].apply(lambda x: f"{x:.0f}")
                    detail_df["均價"] = detail_df["均價"].apply(lambda x: f"{x:.2f}")
                    detail_df["現價"] = detail_df["現價"].apply(lambda x: f"{x:.2f}")

                    if is_usd_only:
                        detail_df["市值"] = detail_df["市值_原幣"].apply(lambda x: f"USD {float(x):,.2f}")
                        detail_df["損益"] = detail_df.apply(
                            lambda r: f"USD {float(r['損益_原幣']):+,.2f}（{float(r['損益%']):+.1f}%）", axis=1
                        )
                    else:
                        detail_df["市值"] = detail_df.apply(
                            lambda r: f"{'USD' if r['幣別']=='USD' else 'NT$'} {float(r['市值_原幣']):,.2f}", axis=1
                        )
                        detail_df["損益"] = detail_df.apply(
                            lambda r: f"{'USD' if r['幣別']=='USD' else 'NT$'} {float(r['損益_原幣']):+,.2f}（{float(r['損益%']):+.1f}%）", axis=1
                        )

                    st.dataframe(
                        detail_df[["標的", "幣別", "股數", "均價", "現價", "市值", "損益"]],
                        use_container_width=True, hide_index=True,
                    )
                else:
                    st.info("此範圍內沒有持股")

            if chart_mode == "圓餅圖":
                render_pie()
            elif chart_mode == "持股明細":
                render_holdings()
            else:
                left, right = st.columns([1, 1])
                with left:
                    render_pie()
                with right:
                    st.markdown("**持股明細**")
                    render_holdings()

    with tab2:
        return_mode = st.radio("顯示模式", ["淨值變化率", "交易報酬率", "兩者都顯示"], horizontal=True)

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("起始日", value=date(date.today().year, 1, 1))
        with col2:
            end_date = st.date_input("結束日", value=date.today())

        snapshots = get_snapshots(user_id)
        filtered = pd.DataFrame()

        if not snapshots.empty:
            snapshots["date"] = pd.to_datetime(snapshots["date"])
            filtered = snapshots[
                (snapshots["date"] >= pd.Timestamp(start_date)) &
                (snapshots["date"] <= pd.Timestamp(end_date))
            ].copy()

        cash_tx = get_cash_transactions(user_id)
        dietz_return = 0.0
        dietz_series = pd.DataFrame()
        flows = pd.DataFrame()

        if not cash_tx.empty:
            cash_tx["date"] = pd.to_datetime(cash_tx["date"])
            flows = cash_tx[
                (cash_tx["type"].isin(["入金", "出金"])) &
                (cash_tx["date"] >= pd.Timestamp(start_date)) &
                (cash_tx["date"] <= pd.Timestamp(end_date))
            ].copy()
            if not flows.empty:
                flows["flow"] = flows.apply(lambda r: r["amount"] if r["type"] == "入金" else -r["amount"], axis=1)

        if not snapshots.empty:
            before = snapshots[snapshots["date"] <= pd.Timestamp(start_date)]
            start_value = float(before.iloc[-1]["net_worth"]) if not before.empty else scoped_total_twd
        else:
            start_value = scoped_total_twd

        end_value = scoped_total_twd
        total_flow = flows["flow"].sum() if not flows.empty else 0.0
        total_days = max((pd.Timestamp(end_date) - pd.Timestamp(start_date)).days, 1)

        weighted_flows = 0.0
        if not flows.empty:
            for _, row in flows.iterrows():
                days_remaining = (pd.Timestamp(end_date) - row["date"]).days
                weight = days_remaining / total_days
                weighted_flows += row["flow"] * weight

        denominator = start_value + weighted_flows
        if denominator > 0:
            dietz_return = (end_value - start_value - total_flow) / denominator * 100

        if not filtered.empty and start_value > 0:
            dietz_series = filtered.copy().reset_index(drop=True)
            if not flows.empty:
                dietz_series["交易報酬率(%)"] = dietz_series.apply(
                    lambda row: (
                        (row["net_worth"] - start_value - flows[flows["date"] <= row["date"]]["flow"].sum())
                        / max(start_value + flows[flows["date"] <= row["date"]].apply(
                            lambda r: r["flow"] * (pd.Timestamp(end_date) - r["date"]).days / total_days, axis=1
                        ).sum(), 1) * 100
                    ), axis=1,
                )
            else:
                dietz_series["交易報酬率(%)"] = dietz_series.apply(
                    lambda row: (row["net_worth"] - start_value) / start_value * 100, axis=1
                )

        def render_nav():
            if snapshots.empty:
                st.info("尚無歷史快照，每次交易後會自動記錄")
                return
            if filtered.empty:
                st.info("選取的時間範圍內沒有快照資料")
                return
            base_value = filtered.iloc[0]["net_worth"]
            nav_df = filtered.copy()
            nav_df["淨值變化率(%)"] = (nav_df["net_worth"] / base_value - 1) * 100
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=nav_df["date"], y=nav_df["淨值變化率(%)"], mode="lines+markers",
                line=dict(color="#378ADD", width=2), marker=dict(size=5),
                fill="tozeroy", fillcolor="rgba(55,138,221,0.08)",
                hovertemplate="日期：%{x|%Y/%m/%d}<br>淨值變化率：%{y:.2f}%<extra></extra>",
            ))
            fig1.update_layout(
                title="淨值變化率（含入出金）", yaxis=dict(ticksuffix="%"), height=350,
                margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig1, use_container_width=True)

        def render_dietz():
            if dietz_series.empty:
                st.metric("交易報酬率（Modified Dietz）", f"{dietz_return:.2f}%")
                st.caption("快照資料不足，僅顯示區間總報酬率")
                return
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=dietz_series["date"], y=dietz_series["交易報酬率(%)"], mode="lines+markers",
                line=dict(color="#1D9E75", width=2), marker=dict(size=5),
                fill="tozeroy", fillcolor="rgba(29,158,117,0.08)",
                hovertemplate="日期：%{x|%Y/%m/%d}<br>交易報酬率：%{y:.2f}%<extra></extra>",
            ))
            fig2.update_layout(
                title=f"交易報酬率（Modified Dietz）：{dietz_return:.2f}%", yaxis=dict(ticksuffix="%"), height=350,
                margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)

        if return_mode == "淨值變化率":
            render_nav()
        elif return_mode == "交易報酬率":
            render_dietz()
        else:
            render_nav()
            render_dietz()