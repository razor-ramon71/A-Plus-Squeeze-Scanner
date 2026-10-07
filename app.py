import streamlit as st
import requests
import pandas as pd
import numpy as np
# -------------------------------------------------
# TRADIER CONNECTION
# -------------------------------------------------

TRADIER_BASE_URL = "https://api.tradier.com/v1"

try:
    TRADIER_TOKEN = st.secrets["TRADIER_TOKEN"]
except Exception:
    TRADIER_TOKEN = None


def tradier_headers():
    return {
        "Authorization": f"Bearer {TRADIER_TOKEN}",
        "Accept": "application/json"
    }


def get_daily_history(symbol, days=300):
    """Download daily OHLCV history from Tradier."""

    if not TRADIER_TOKEN:
        return None

    end_date = pd.Timestamp.today()
    start_date = end_date - pd.Timedelta(days=days * 1.6)

    url = f"{TRADIER_BASE_URL}/markets/history"

    params = {
        "symbol": symbol.upper(),
        "interval": "daily",
        "start": start_date.strftime("%Y-%m-%d"),
        "end": end_date.strftime("%Y-%m-%d")
    }

    try:
        response = requests.get(
            url,
            headers=tradier_headers(),
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        history = data.get("history")

        if not history:
            return None

        days_data = history.get("day")

        if not days_data:
            return None

        if isinstance(days_data, dict):
            days_data = [days_data]

        df = pd.DataFrame(days_data)

        for column in ["open", "high", "low", "close", "volume"]:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df["date"] = pd.to_datetime(df["date"])

        df = (
            df.sort_values("date")
            .dropna()
            .reset_index(drop=True)
        )

        return df

    except Exception as e:
        st.error(f"Tradier error for {symbol}: {e}")
        return None

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="A+ Squeeze Scanner",
    page_icon="🎯",
    layout="wide"
)

# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.title("🎯 A+ Squeeze Scanner")

st.subheader(
    "21 EMA • 50 SMA • 200 SMA • Squeeze • Momentum • Volume"
)

st.info(
    "Built to identify only high-quality A+ bullish and bearish "
    "swing-trade setups."
)

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.header("Scanner Settings")

direction = st.sidebar.selectbox(
    "Trade Direction",
    ["Both", "Bullish", "Bearish"]
)

minimum_score = st.sidebar.slider(
    "Minimum A+ Score",
    min_value=80,
    max_value=100,
    value=90,
    step=1
)

st.sidebar.markdown("---")

st.sidebar.write("### Moving Averages")

st.sidebar.write("🔴 21 EMA")
st.sidebar.write("⚪ 50 SMA")
st.sidebar.write("🔴 200 SMA")

st.sidebar.markdown("---")

st.sidebar.write("### A+ Requirements")

st.sidebar.write("✓ Trend alignment")
st.sidebar.write("✓ Squeeze compression")
st.sidebar.write("✓ Momentum confirmation")
st.sidebar.write("✓ Volume confirmation")
st.sidebar.write("✓ Clean price structure")

# -------------------------------------------------
# MAIN DASHBOARD
# -------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Stocks Scanned", "0")

with col2:
    st.metric("A+ Longs", "0")

with col3:
    st.metric("A+ Shorts", "0")

with col4:
    st.metric("Minimum Score", minimum_score)

st.markdown("---")

st.subheader("🏆 A+ Trade Candidates")

st.warning(
    "Scanner engine not connected yet. "
    "Next step: add market data and the A+ scoring engine."
)

# -------------------------------------------------
# STRATEGY DESCRIPTION
# -------------------------------------------------
with st.expander("📖 A+ Scanner Rules"):

    st.write("### 🟢 Bullish A+")

    st.code(
        """
Price > 21 EMA
21 EMA > 50 SMA
50 SMA > 200 SMA

Squeeze active or recently fired
Momentum positive and increasing
Volume confirmation
Bullish price structure
        """
    )

    st.write("### 🔴 Bearish A+")

    st.code(
        """
Price < 21 EMA
21 EMA < 50 SMA
50 SMA < 200 SMA

Squeeze active or recently fired
Momentum negative and decreasing
Volume confirmation
Bearish price structure
        """
    )
st.markdown("---")
st.subheader("🔌 Tradier Data Test")

test_symbol = st.text_input(
    "Test ticker",
    value="AAPL"
).upper()

if st.button("Test Tradier Connection"):

    with st.spinner(f"Loading {test_symbol}..."):

        test_data = get_daily_history(test_symbol)

        if test_data is not None and len(test_data) > 0:

            latest = test_data.iloc[-1]

            st.success(
                f"Tradier connected! ✅ "
                f"{test_symbol} latest close: "
                f"${latest['close']:.2f}"
            )

            st.dataframe(
                test_data.tail(5),
                use_container_width=True
            )

        else:
            st.error(
                "No market data received. Check the Tradier token."
            )
st.caption(
    "A+ Squeeze Scanner • Swing-trade research tool • "
    "Signals are not financial advice."
)
