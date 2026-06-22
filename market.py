import yfinance as yf
import streamlit as st


@st.cache_data(ttl=300)
def get_usd_twd():
    try:
        ticker = yf.Ticker("USDTWD=X")
        rate = ticker.fast_info["lastPrice"]
        return round(rate, 2)
    except:
        return 31.5


@st.cache_data(ttl=300)
def get_price(ticker: str) -> float:
    try:
        t = yf.Ticker(ticker)
        return t.fast_info["lastPrice"]
    except:
        return 0.0


@st.cache_data(ttl=300)
def get_prices_batch(tickers: tuple) -> dict:
    """一次性批次抓取多個股票價格，失敗時改用單支逐一補救"""
    if not tickers:
        return {}

    prices = {}
    try:
        data = yf.download(list(tickers), period="1d", progress=False, group_by="ticker")
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    val = float(data["Close"].iloc[-1])
                else:
                    val = float(data[ticker]["Close"].iloc[-1])
                if val and val > 0:
                    prices[ticker] = val
            except:
                pass
    except:
        pass

    # 任何沒抓到的股票，逐一用單支方式重試
    missing = [t for t in tickers if t not in prices or prices[t] == 0]
    for ticker in missing:
        try:
            t = yf.Ticker(ticker)
            val = t.fast_info["lastPrice"]
            prices[ticker] = float(val) if val else 0.0
        except:
            prices[ticker] = 0.0

    return prices


def calc_total_net_worth_twd(user_id: str) -> float:
    from database import get_banks, get_cash_accounts, get_holdings
    usd_twd = get_usd_twd()
    banks = get_banks(user_id)
    all_accounts = get_cash_accounts(user_id)
    total = 0.0

    all_tickers = set()
    holdings_by_account = {}
    for _, acc in all_accounts.iterrows():
        holdings = get_holdings(int(acc["id"]))
        holdings_by_account[int(acc["id"])] = holdings
        all_tickers.update(holdings["ticker"].tolist())

    prices = get_prices_batch(tuple(all_tickers))

    for _, bank in banks.iterrows():
        bank_accounts = all_accounts[all_accounts["bank_id"] == bank["id"]]
        for _, acc in bank_accounts.iterrows():
            cash = acc["balance"]
            holdings = holdings_by_account[int(acc["id"])]
            stock_value = sum(
                prices.get(h["ticker"], 0.0) * h["shares"]
                for _, h in holdings.iterrows()
            )
            sub_total = cash + stock_value
            if acc["currency"] == "USD":
                sub_total *= usd_twd
            total += sub_total

    return total