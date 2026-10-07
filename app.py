import streamlit as st

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

st.caption(
    "A+ Squeeze Scanner • Swing-trade research tool • "
    "Signals are not financial advice."
)
