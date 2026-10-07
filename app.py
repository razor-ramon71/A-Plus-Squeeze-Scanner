import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from stock_universe import STOCK_UNIVERSE,SECTORS, get_sector
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
# TECHNICAL INDICATORS
# -------------------------------------------------

def calculate_indicators(df):
    """
    Calculate:
    - 21 EMA
    - 50 SMA
    - 200 SMA
    - Bollinger Bands
    - Keltner Channels
    - Squeeze ON/OFF
    - Momentum
    - Relative Volume
    """

    df = df.copy()

    # -------------------------
    # MOVING AVERAGES
    # -------------------------
    df["EMA21"] = df["close"].ewm(
        span=21,
        adjust=False
    ).mean()

    df["SMA50"] = df["close"].rolling(50).mean()

    df["SMA200"] = df["close"].rolling(200).mean()

    # -------------------------
    # BOLLINGER BANDS
    # 20 period / 2 std dev
    # -------------------------
    bb_length = 20

    df["BB_MID"] = df["close"].rolling(bb_length).mean()

    bb_std = df["close"].rolling(bb_length).std()

    df["BB_UPPER"] = df["BB_MID"] + (2.0 * bb_std)
    df["BB_LOWER"] = df["BB_MID"] - (2.0 * bb_std)

    # -------------------------
    # TRUE RANGE / ATR
    # -------------------------
    previous_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - previous_close).abs()
    tr3 = (df["low"] - previous_close).abs()

    df["TR"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["ATR20"] = df["TR"].rolling(20).mean()

    # -------------------------
    # KELTNER CHANNEL
    # 20 period / 1.5 ATR
    # -------------------------
    df["KC_MID"] = df["close"].rolling(20).mean()

    df["KC_UPPER"] = (
        df["KC_MID"] +
        (1.5 * df["ATR20"])
    )

    df["KC_LOWER"] = (
        df["KC_MID"] -
        (1.5 * df["ATR20"])
    )

    # -------------------------
    # SQUEEZE
    # Bollinger Bands inside
    # Keltner Channel
    # -------------------------
    df["SQUEEZE_ON"] = (
        (df["BB_LOWER"] > df["KC_LOWER"]) &
        (df["BB_UPPER"] < df["KC_UPPER"])
    )

    # First bar after squeeze releases
    df["SQUEEZE_FIRED"] = (
        (~df["SQUEEZE_ON"]) &
        (df["SQUEEZE_ON"].shift(1) == True)
    )

    # Count consecutive squeeze bars
    squeeze_count = []
    count = 0

    for value in df["SQUEEZE_ON"]:
        if value:
            count += 1
        else:
            count = 0

        squeeze_count.append(count)

    df["SQUEEZE_BARS"] = squeeze_count

    # -------------------------
    # MOMENTUM
    # Approximate directional
    # squeeze momentum
    # -------------------------
    highest_high = df["high"].rolling(20).max()
    lowest_low = df["low"].rolling(20).min()
    average_close = df["close"].rolling(20).mean()

    midpoint = (
        ((highest_high + lowest_low) / 2)
        + average_close
    ) / 2

    raw_momentum = df["close"] - midpoint

    # Linear regression momentum
    def linreg_last(values):
        if len(values) < 20:
            return np.nan

        x = np.arange(len(values))

        slope, intercept = np.polyfit(
            x,
            values,
            1
        )

        return (
            slope * (len(values) - 1)
            + intercept
        )

    df["MOMENTUM"] = raw_momentum.rolling(20).apply(
        linreg_last,
        raw=True
    )

    df["MOMENTUM_RISING"] = (
        df["MOMENTUM"] >
        df["MOMENTUM"].shift(1)
    )

    # -------------------------
    # VOLUME
    # -------------------------
    df["AVG_VOLUME20"] = (
        df["volume"].rolling(20).mean()
    )

    df["REL_VOLUME"] = (
        df["volume"] /
        df["AVG_VOLUME20"]
    )

    # -------------------------
    # MA SLOPES
    # Compare today vs 5 bars ago
    # -------------------------
    df["EMA21_RISING"] = (
        df["EMA21"] >
        df["EMA21"].shift(5)
    )

    df["SMA50_RISING"] = (
        df["SMA50"] >
        df["SMA50"].shift(5)
    )

    return df

# -------------------------------------------------
# A+ SCORING ENGINE
# -------------------------------------------------

def score_setup(df):
    """
    Score the latest daily bar for bullish and bearish setups.
    Maximum score = 100.
    """

    if df is None or len(df) < 200:
        return None

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    long_score = 0
    short_score = 0

    long_reasons = []
    short_reasons = []

    # -------------------------------------------------
    # 1. MA ALIGNMENT - 30 POINTS
    # -------------------------------------------------

    # Bullish: Price > 21 EMA > 50 SMA > 200 SMA
    if (
        latest["close"] > latest["EMA21"] >
        latest["SMA50"] > latest["SMA200"]
    ):
        long_score += 30
        long_reasons.append("Perfect bullish MA stack")

    # Bearish: Price < 21 EMA < 50 SMA < 200 SMA
    if (
        latest["close"] < latest["EMA21"] <
        latest["SMA50"] < latest["SMA200"]
    ):
        short_score += 30
        short_reasons.append("Perfect bearish MA stack")

    # -------------------------------------------------
    # 2. MA DIRECTION - 15 POINTS
    # -------------------------------------------------

    if latest["EMA21_RISING"] and latest["SMA50_RISING"]:
        long_score += 15
        long_reasons.append("21 EMA & 50 SMA rising")

    if (
        not latest["EMA21_RISING"] and
        not latest["SMA50_RISING"]
    ):
        short_score += 15
        short_reasons.append("21 EMA & 50 SMA falling")

    # -------------------------------------------------
    # 3. SQUEEZE - 20 POINTS
    # -------------------------------------------------

    # Active squeeze
    if latest["SQUEEZE_ON"]:
        long_score += 15
        short_score += 15

        long_reasons.append("Squeeze compression active")
        short_reasons.append("Squeeze compression active")

        # Reward mature compression
        if latest["SQUEEZE_BARS"] >= 3:
            long_score += 5
            short_score += 5

            long_reasons.append("3+ squeeze bars")
            short_reasons.append("3+ squeeze bars")

    # Fresh release gets full squeeze points
    elif latest["SQUEEZE_FIRED"]:
        long_score += 20
        short_score += 20

        long_reasons.append("Fresh squeeze release")
        short_reasons.append("Fresh squeeze release")

    # -------------------------------------------------
    # 4. MOMENTUM - 20 POINTS
    # -------------------------------------------------

    # Bullish momentum
    if latest["MOMENTUM"] > 0:
        long_score += 10
        long_reasons.append("Momentum above zero")

        if latest["MOMENTUM_RISING"]:
            long_score += 10
            long_reasons.append("Momentum accelerating")

    # Bearish momentum
    if latest["MOMENTUM"] < 0:
        short_score += 10
        short_reasons.append("Momentum below zero")

        if not latest["MOMENTUM_RISING"]:
            short_score += 10
            short_reasons.append("Bearish momentum accelerating")

    # -------------------------------------------------
    # 5. VOLUME - 10 POINTS
    # -------------------------------------------------

    if latest["REL_VOLUME"] >= 1.20:
        long_score += 10
        short_score += 10

        long_reasons.append("Strong relative volume")
        short_reasons.append("Strong relative volume")

    elif latest["REL_VOLUME"] >= 1.00:
        long_score += 5
        short_score += 5

        long_reasons.append("Volume confirmation")
        short_reasons.append("Volume confirmation")

    # -------------------------------------------------
    # 6. PRICE STRUCTURE - 5 POINTS
    # -------------------------------------------------

    if latest["close"] > previous["high"]:
        long_score += 5
        long_reasons.append("Bullish price expansion")

    if latest["close"] < previous["low"]:
        short_score += 5
        short_reasons.append("Bearish price expansion")

    # Never exceed 100
    long_score = min(long_score, 100)
    short_score = min(short_score, 100)

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------

    if latest["SQUEEZE_ON"]:
        squeeze_status = "🔴 SQUEEZE ON"

    elif latest["SQUEEZE_FIRED"]:
        squeeze_status = "🟢 JUST FIRED"

    else:
        squeeze_status = "⚪ NO SQUEEZE"

    # -------------------------------------------------
    # RETURN RESULT
    # -------------------------------------------------

    return {
        "symbol": None,

        "price": round(float(latest["close"]), 2),

        "long_score": int(long_score),
        "short_score": int(short_score),

        "squeeze": squeeze_status,

        "squeeze_bars": int(latest["SQUEEZE_BARS"]),

        "momentum": round(
            float(latest["MOMENTUM"]), 2
        ),

        "relative_volume": round(
            float(latest["REL_VOLUME"]), 2
        ),

        "ema21": round(float(latest["EMA21"]), 2),
        "sma50": round(float(latest["SMA50"]), 2),
        "sma200": round(float(latest["SMA200"]), 2),

        "long_reasons": long_reasons,
        "short_reasons": short_reasons
    }

# ============================================================
# A+ SQUEEZE SCANNER
# LIQUID U.S. STOCK UNIVERSE
# ============================================================

SECTORS = {

    "Technology": [
        "AAPL", "ACN", "ADBE", "ADI", "ADSK", "AKAM", "AMD",
        "ANET", "APP", "AVGO", "CDNS", "CRM", "CRWD", "CSCO",
        "CTSH", "DELL", "FTNT", "GLW", "HPE", "HPQ", "IBM",
        "INTC", "INTU", "KLAC", "LRCX", "MCHP", "MPWR", "MSFT",
        "MU", "NOW", "NVDA", "NXPI", "ON", "ORCL", "PANW",
        "PLTR", "QCOM", "SMCI", "SNPS", "STX", "SWKS", "TEAM",
        "TEL", "TER", "TSM", "TXN", "WDAY", "WDC", "ZS"
    ],

    "Communication Services": [
        "CHTR", "CMCSA", "DIS", "EA", "GOOG", "GOOGL", "LYV",
        "META", "NFLX", "NWSA", "OMC", "PARA", "PINS", "RBLX",
        "RDDT", "ROKU", "SNAP", "SPOT", "T", "TMUS", "TTWO",
        "VZ", "WBD"
    ],

    "Consumer Discretionary": [
        "ABNB", "AMZN", "APTV", "AZO", "BBY", "BKNG", "CCL",
        "CMG", "CZR", "DHI", "DKNG", "DPZ", "DRI", "EBAY",
        "ETSY", "EXPE", "F", "GM", "HD", "LEN", "LOW", "LULU",
        "MAR", "MCD", "MGM", "NCLH", "NKE", "ORLY", "PHM",
        "RCL", "SBUX", "TGT", "TJX", "TSLA", "ULTA", "WYNN",
        "YUM"
    ],

    "Consumer Staples": [
        "ADM", "BG", "CL", "CLX", "COST", "CPB", "DG", "DLTR",
        "GIS", "HSY", "K", "KHC", "KMB", "KO", "KR", "MDLZ",
        "MNST", "MO", "PEP", "PG", "PM", "SJM", "STZ", "SYY",
        "TAP", "TSN", "WMT"
    ],

    "Financials": [
        "AFL", "AIG", "AXP", "BAC", "BK", "BLK", "BX", "C",
        "CBOE", "CB", "CME", "COF", "DFS", "FITB", "GS", "HBAN",
        "ICE", "JPM", "KEY", "KKR", "MA", "MET", "MS", "MTB",
        "PNC", "PRU", "PYPL", "RF", "SCHW", "SOFI", "STT",
        "SYF", "TFC", "USB", "V", "WFC"
    ],

    "Healthcare": [
        "ABBV", "ABT", "ALGN", "AMGN", "BAX", "BDX", "BIIB",
        "BMY", "BSX", "CAH", "CI", "CNC", "COO", "CVS", "DHR",
        "DXCM", "EW", "GILD", "HCA", "HOLX", "HUM", "IDXX",
        "ILMN", "ISRG", "JNJ", "LLY", "MDT", "MRK", "PFE",
        "REGN", "RMD", "SYK", "TMO", "UNH", "VRTX", "ZBH",
        "ZTS"
    ],

    "Industrials": [
        "BA", "CAT", "CHRW", "CSX", "CTAS", "DAL", "DE", "EMR",
        "ETN", "EXPD", "FDX", "GD", "GE", "GEV", "HON", "HWM",
        "JCI", "LHX", "LMT", "MMM", "NOC", "NSC", "PCAR", "PH",
        "RTX", "SNA", "TXT", "UAL", "UNP", "UPS", "URI",
        "WM", "XYL"
    ],

    "Energy": [
        "APA", "BKR", "COP", "CTRA", "CVX", "DVN", "EOG",
        "EQT", "FANG", "HAL", "HES", "KMI", "MPC", "MRO",
        "OXY", "PSX", "SLB", "TRGP", "VLO", "WMB", "XOM"
    ],

    "Materials": [
        "AA", "ALB", "APD", "CF", "CLF", "CTVA", "DD", "DOW",
        "ECL", "FCX", "FMC", "LIN", "LYB", "MOS", "NEM",
        "NUE", "PPG", "SHW", "STLD", "VMC"
    ],

    "Utilities": [
        "AEP", "AES", "CEG", "CMS", "D", "DTE", "DUK", "ED",
        "EIX", "ETR", "EVRG", "EXC", "FE", "NEE", "NRG",
        "PCG", "PEG", "PNW", "SO", "SRE", "VST", "XEL"
    ],

    "Real Estate": [
        "AMT", "ARE", "AVB", "BXP", "CBRE", "CCI", "CPT",
        "DLR", "EQR", "EXR", "IRM", "KIM", "MAA", "O", "PLD",
        "PSA", "SBAC", "SPG", "VICI", "VTR", "WELL"
    ],

    "Growth & High Beta": [
        "AFRM", "ASTS", "BILL", "CELH", "COIN", "CVNA", "DOCU",
        "HOOD", "IONQ", "MARA", "NET", "OKLO", "PATH", "RKLB",
        "RIVN", "SHOP", "SNOW", "SOUN", "TEM", "UPST"
    ]
}


# Build one master list automatically
STOCK_UNIVERSE = sorted(
    set(
        ticker
        for stocks in SECTORS.values()
        for ticker in stocks
    )
)


def get_sector(symbol):
    """Return sector for a ticker."""

    for sector, stocks in SECTORS.items():
        if symbol in stocks:
            return sector

    return "Other"

# -------------------------------------------------
# SCAN ONE STOCK
# -------------------------------------------------

def scan_symbol(symbol):

    df = get_daily_history(symbol)

    if df is None or len(df) < 200:
        return None

    df = calculate_indicators(df)

    result = score_setup(df)

    if result is None:
        return None

    result["symbol"] = symbol

    return result


# -------------------------------------------------
# RUN SCANNER
# -------------------------------------------------

def run_scanner(symbols):

    results = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(symbols)

    for i, symbol in enumerate(symbols):

        status_text.write(
            f"Scanning {symbol}... "
            f"{i + 1} of {total}"
        )

        try:

            result = scan_symbol(symbol)

            if result:
                results.append(result)

        except Exception:
            # Don't let one bad ticker stop the scan
            pass

        progress_bar.progress(
            (i + 1) / total
        )

    status_text.empty()
    progress_bar.empty()

    return results

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

st.write(
    "Scans daily charts for A+ squeeze setups using "
    "trend, momentum, volume and price structure."
)

if st.button(
    "🚀 RUN A+ SCANNER",
    type="primary",
    use_container_width=True
):

    scan_results = run_scanner(STOCK_UNIVERSE)

    if not scan_results:

        st.warning("No valid market data was returned.")

    else:

        longs = [
            x for x in scan_results
            if x["long_score"] >= minimum_score
        ]

        shorts = [
            x for x in scan_results
            if x["short_score"] >= minimum_score
        ]

        longs = sorted(
            longs,
            key=lambda x: x["long_score"],
            reverse=True
        )

        shorts = sorted(
            shorts,
            key=lambda x: x["short_score"],
            reverse=True
        )

        # -----------------------------------------
        # RESULTS SUMMARY
        # -----------------------------------------

        c1, c2, c3 = st.columns(3)

        c1.metric("Stocks Scanned", len(scan_results))
        c2.metric("🟢 A+ Longs", len(longs))
        c3.metric("🔴 A+ Shorts", len(shorts))

        # -----------------------------------------
        # A+ LONGS
        # -----------------------------------------

        st.markdown("## 🟢 A+ LONG SETUPS")

        if longs:

            long_table = pd.DataFrame([
                {
                    "Rank": i + 1,
                    "Symbol": x["symbol"],
                    "Score": x["long_score"],
                    "Price": x["price"],
                    "Squeeze": x["squeeze"],
                    "Sqz Bars": x["squeeze_bars"],
                    "Momentum": x["momentum"],
                    "Rel Vol": x["relative_volume"],
                    "21 EMA": x["ema21"],
                    "50 SMA": x["sma50"],
                    "200 SMA": x["sma200"]
                }
                for i, x in enumerate(longs)
            ])

            st.dataframe(
                long_table,
                use_container_width=True,
                hide_index=True
            )

            st.success(
                f"🔥 #1 LONG: {longs[0]['symbol']} — "
                f"{longs[0]['long_score']}/100"
            )

            with st.expander(
                f"Why {longs[0]['symbol']} is A+"
            ):
                for reason in longs[0]["long_reasons"]:
                    st.write("✅", reason)

        else:

            st.info(
                f"No bullish setups reached "
                f"{minimum_score}/100."
            )

        # -----------------------------------------
        # A+ SHORTS
        # -----------------------------------------

        st.markdown("## 🔴 A+ SHORT SETUPS")

        if shorts:

            short_table = pd.DataFrame([
                {
                    "Rank": i + 1,
                    "Symbol": x["symbol"],
                    "Score": x["short_score"],
                    "Price": x["price"],
                    "Squeeze": x["squeeze"],
                    "Sqz Bars": x["squeeze_bars"],
                    "Momentum": x["momentum"],
                    "Rel Vol": x["relative_volume"],
                    "21 EMA": x["ema21"],
                    "50 SMA": x["sma50"],
                    "200 SMA": x["sma200"]
                }
                for i, x in enumerate(shorts)
            ])

            st.dataframe(
                short_table,
                use_container_width=True,
                hide_index=True
            )

            st.error(
                f"🎯 #1 SHORT: {shorts[0]['symbol']} — "
                f"{shorts[0]['short_score']}/100"
            )

            with st.expander(
                f"Why {shorts[0]['symbol']} is A+"
            ):
                for reason in shorts[0]["short_reasons"]:
                    st.write("✅", reason)

        else:

            st.info(
                f"No bearish setups reached "
                f"{minimum_score}/100."
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
