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
