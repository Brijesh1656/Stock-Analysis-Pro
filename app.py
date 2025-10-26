import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ollama
import tempfile
import base64
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_CENTER
from datetime import datetime, timedelta
import numpy as np
import time


# Cached data fetching with retry logic
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_data(ticker, start_date, end_date, max_retries=3):
    """Fetch stock data with retry logic and rate limit handling"""
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                time.sleep(2 ** attempt)
            
            df = yf.download(
                ticker, 
                start=start_date, 
                end=end_date, 
                progress=False,
                auto_adjust=True
            )
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join([str(i) for i in col]).strip().rstrip('_') for col in df.columns.values]
            
            return df, None
            
        except Exception as e:
            error_msg = str(e)
            if "Rate" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    continue
                else:
                    return None, "⚠️ Yahoo Finance rate limit reached. Please try again in a few minutes."
            else:
                return None, f"❌ Error: {error_msg}"
    
    return None, "❌ Failed to fetch data after multiple attempts."


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ticker_info(ticker):
    """Fetch ticker info with error handling"""
    try:
        stock = yf.Ticker(ticker)
        return stock.info
    except:
        return {}


def calculate_technical_indicators(df, close_col):
    """Calculates RSI, MACD, and Bollinger Bands on a DataFrame."""
    df_copy = df.copy()
    
    # RSI
    delta = df_copy[close_col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan) 
    df_copy['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df_copy[close_col].ewm(span=12, adjust=False).mean()
    exp2 = df_copy[close_col].ewm(span=26, adjust=False).mean()
    df_copy['MACD'] = exp1 - exp2
    df_copy['MACD_Signal'] = df_copy['MACD'].ewm(span=9, adjust=False).mean()
    df_copy['MACD_Hist'] = df_copy['MACD'] - df_copy['MACD_Signal']
    
    # Bollinger Bands
    df_copy['BB_Middle'] = df_copy[close_col].rolling(window=20).mean()
    std = df_copy[close_col].rolling(window=20).std()
    df_copy['BB_Upper'] = df_copy['BB_Middle'] + (2 * std)
    df_copy['BB_Lower'] = df_copy['BB_Middle'] - (2 * std)
    
    return df_copy

# Page config
st.set_page_config(
    page_title="Stock Analysis Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🚀 ULTRA-MODERN SLEEK DESIGN (Matching FinVision)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* Premium Dark Theme */
    .main {
        background: #000000;
        color: #ffffff;
    }
    
    .stApp {
        background: #000000;
    }
    
    .block-container {
        padding: 3rem 2rem !important;
        max-width: 1400px !important;
    }
    
    /* Glassmorphic Hero */
    .hero-section {
        position: relative;
        text-align: center;
        padding: 5rem 3rem;
        margin-bottom: 4rem;
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%);
        border-radius: 32px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        overflow: hidden;
    }
    
    .hero-section::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 50%);
        animation: pulse 8s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 0.8; }
    }
    
    .logo-wrapper {
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        position: relative;
        z-index: 1;
    }
    
    .logo {
        font-size: 3rem;
    }
    
    .brand-name {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.03em;
    }
    
    .hero-tagline {
        font-size: 1.125rem;
        color: rgba(255, 255, 255, 0.6);
        font-weight: 500;
        position: relative;
        z-index: 1;
        letter-spacing: 0.01em;
    }
    
    /* Premium Stat Cards */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.25rem;
        margin-bottom: 4rem;
    }
    
    .stat-card {
        position: relative;
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(20px);
        padding: 2rem 1.5rem;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        overflow: hidden;
    }
    
    .stat-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.6), transparent);
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    
    .stat-card:hover {
        transform: translateY(-8px);
        border-color: rgba(139, 92, 246, 0.3);
        background: rgba(139, 92, 246, 0.03);
        box-shadow: 0 20px 60px rgba(139, 92, 246, 0.15);
    }
    
    .stat-card:hover::before {
        opacity: 1;
    }
    
    .stat-icon {
        font-size: 1.5rem;
        margin-bottom: 1rem;
        opacity: 0.8;
    }
    
    .stat-label {
        font-size: 0.813rem;
        color: rgba(255, 255, 255, 0.5);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.75rem;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 900;
        color: #ffffff;
        line-height: 1;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .stat-delta {
        font-size: 0.875rem;
        font-weight: 600;
        opacity: 0.9;
    }
    
    /* Section Titles */
    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 1.5rem;
        letter-spacing: -0.02em;
    }
    
    /* Premium Input Fields */
    .stTextInput > label, .stSelectbox > label, .stDateInput > label, .stNumberInput > label {
        color: rgba(255, 255, 255, 0.5) !important;
        font-weight: 600 !important;
        font-size: 0.813rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem !important;
    }
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stDateInput > div > div > input,
    .stNumberInput > div > div > input {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        color: white !important;
        font-weight: 500 !important;
        padding: 1rem 1.25rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div:focus-within,
    .stDateInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: rgba(139, 92, 246, 0.6) !important;
        background: rgba(139, 92, 246, 0.05) !important;
        box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1) !important;
    }
    
    /* Ultra-Modern Button */
    .stButton > button, .stDownloadButton > button {
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
        color: white;
        border: none;
        padding: 1rem 2rem;
        border-radius: 16px;
        font-weight: 700;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.165, 0.84, 0.44, 1);
        text-transform: none;
        letter-spacing: 0.02em;
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3);
        width: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before, .stDownloadButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.6s ease;
    }
    
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 48px rgba(139, 92, 246, 0.4);
    }
    
    .stButton > button:hover::before, .stDownloadButton > button:hover::before {
        left: 100%;
    }
    
    /* Sleek Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: rgba(255, 255, 255, 0.02);
        padding: 0.5rem;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        margin-bottom: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: none;
        border-radius: 12px;
        color: rgba(255, 255, 255, 0.5);
        font-weight: 600;
        padding: 0.875rem 1.75rem;
        font-size: 0.938rem;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: rgba(139, 92, 246, 0.15);
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: rgba(255, 255, 255, 0.8);
    }
    
    /* Premium Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2.25rem !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        letter-spacing: -0.02em !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.5) !important;
        font-size: 0.813rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    /* Premium Messages */
    .stSuccess {
        background: rgba(34, 197, 94, 0.1) !important;
        border-left: 3px solid #22c55e !important;
        border-radius: 16px !important;
        color: #fff !important;
        backdrop-filter: blur(10px);
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.1) !important;
        border-left: 3px solid #f59e0b !important;
        border-radius: 16px !important;
        color: #fff !important;
        backdrop-filter: blur(10px);
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.1) !important;
        border-left: 3px solid #3b82f6 !important;
        border-radius: 16px !important;
        color: #fff !important;
        backdrop-filter: blur(10px);
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1) !important;
        border-left: 3px solid #ef4444 !important;
        border-radius: 16px !important;
        color: #fff !important;
        backdrop-filter: blur(10px);
    }
    
    /* Multiselect */
    .stMultiSelect [data-baseweb="tag"] {
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
        border-radius: 8px;
    }
    
    /* Radio buttons */
    .stRadio > div {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    
    .stRadio > div > label {
        background: rgba(255, 255, 255, 0.02);
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .stRadio > div > label:hover {
        background: rgba(139, 92, 246, 0.05);
        border-color: rgba(139, 92, 246, 0.2);
    }
    
    /* Checkbox */
    .stCheckbox {
        background: rgba(255, 255, 255, 0.02);
        padding: 0.75rem 1rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #000000 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #8b5cf6 0%, #6366f1 100%) !important;
        border-radius: 10px;
    }
    
    .stProgress > div > div {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #8b5cf6 !important;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Typography */
    h1, h2, h3, h4 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }
    
    h1 { font-size: 2.25rem !important; }
    h2 { font-size: 1.875rem !important; }
    h3 { font-size: 1.5rem !important; }
    
    p {
        color: rgba(255, 255, 255, 0.7) !important;
        line-height: 1.7 !important;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: rgba(255, 255, 255, 0.06);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'stock_data' not in st.session_state:
    st.session_state['stock_data'] = None
if 'ai_analysis' not in st.session_state:
    st.session_state['ai_analysis'] = None
if 'ticker_info' not in st.session_state:
    st.session_state['ticker_info'] = None

# Hero Section
st.markdown("""
<div class="hero-section">
    <div class="logo-wrapper">
        <span class="logo">📈</span>
        <span class="brand-name">Stock Analysis Pro</span>
    </div>
    <p class="hero-tagline">AI-Powered Technical Analysis • Real-Time Market Intelligence • Advanced Backtesting</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown('<h3 class="section-title">⚙️ Configuration</h3>', unsafe_allow_html=True)
    
    ticker = st.text_input(
        "Stock Ticker",
        value="AAPL",
        placeholder="e.g., AAPL, MSFT, TSLA",
        help="Enter a valid stock ticker symbol"
    ).upper()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    date_preset = st.selectbox(
        "Quick Date Range",
        ["Custom", "1 Week", "1 Month", "3 Months", "6 Months", "1 Year", "YTD", "5 Years"]
    )
    
    today = datetime.today().date()
    
    if date_preset == "1 Week":
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_preset == "1 Month":
        start_date = today - timedelta(days=30)
        end_date = today
    elif date_preset == "3 Months":
        start_date = today - timedelta(days=90)
        end_date = today
    elif date_preset == "6 Months":
        start_date = today - timedelta(days=180)
        end_date = today
    elif date_preset == "1 Year":
        start_date = today - timedelta(days=365)
        end_date = today
    elif date_preset == "YTD":
        start_date = datetime(today.year, 1, 1).date()
        end_date = today
    elif date_preset == "5 Years":
        start_date = today - timedelta(days=1825)
        end_date = today
    else:
        start_date = st.date_input(
            "Start Date",
            value=today - timedelta(days=365),
            max_value=today
        )
        end_date = st.date_input(
            "End Date",
            value=today,
            max_value=today
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    fetch_btn = st.button("🚀 Fetch Data", use_container_width=True)
    
    if fetch_btn:
        with st.spinner(f"Fetching data for {ticker}..."):
            df, error = fetch_stock_data(ticker, start_date, end_date)
            
            if error:
                st.error(error)
                if "rate limit" in error.lower():
                    st.info("💡 **Tip**: Try again in 1-2 minutes or use a different ticker.")
            elif df.empty:
                st.error("❌ No data found for this ticker and date range.")
            else:
                ticker_info = fetch_ticker_info(ticker)
                
                st.session_state['stock_data'] = df
                st.session_state['ticker_info'] = ticker_info
                st.success(f"✅ Loaded {len(df)} days of data!")
    
    if st.session_state['stock_data'] is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 class="section-title">📊 Data Info</h3>', unsafe_allow_html=True)
        data = st.session_state['stock_data']
        st.metric("Days Loaded", len(data))
        st.metric("Date Range", f"{data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")

# Main content
if st.session_state['stock_data'] is not None:
    data = st.session_state['stock_data']
    ticker_info = st.session_state.get('ticker_info', {})
    
    # Determine column names
    close_col = 'Close' if 'Close' in data.columns else f'Close_{ticker}'
    open_col = 'Open' if 'Open' in data.columns else f'Open_{ticker}'
    high_col = 'High' if 'High' in data.columns else f'High_{ticker}'
    low_col = 'Low' if 'Low' in data.columns else f'Low_{ticker}'
    volume_col = 'Volume' if 'Volume' in data.columns else f'Volume_{ticker}'
    
    if len(data) >= 50:
        data = calculate_technical_indicators(data, close_col).dropna()
        if data.empty:
            st.warning("Not enough clean data after calculating technical indicators.")
    
    if data.empty:
        st.warning("Data is empty. Please check your selected date range or ticker.")
        st.stop()
        
    current_price = data[close_col].iloc[-1]
    prev_price = data[close_col].iloc[-2] if len(data) > 1 else current_price
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0
    
    high_52w = data[high_col].tail(252).max() if len(data) >= 252 else data[high_col].max()
    low_52w = data[low_col].tail(252).min() if len(data) >= 252 else data[low_col].min()
    avg_volume = data[volume_col].tail(20).mean()
    
    # Key Metrics
    st.markdown('<h2 class="section-title">📊 Key Metrics</h2>', unsafe_allow_html=True)
    
    change_color = "#22c55e" if price_change >= 0 else "#ef4444"
    
    st.markdown(f"""
    <div class="stat-grid">
        <div class="stat-card">
            <div class="stat-icon">💰</div>
            <div class="stat-label">Current Price</div>
            <div class="stat-value">${current_price:.2f}</div>
            <div class="stat-delta" style="color: {change_color}">
                {'+' if price_change >= 0 else ''}{price_change:.2f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">📈</div>
            <div class="stat-label">52W High</div>
            <div class="stat-value">${high_52w:.2f}</div>
            <div class="stat-delta" style="color: rgba(255,255,255,0.7)">
                {((current_price / high_52w - 1) * 100):.1f}% from high
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">📉</div>
            <div class="stat-label">52W Low</div>
            <div class="stat-value">${low_52w:.2f}</div>
            <div class="stat-delta" style="color: rgba(255,255,255,0.7)">
                {((current_price / low_52w - 1) * 100):.1f}% from low
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-label">Avg Volume (20D)</div>
            <div class="stat-value">{avg_volume/1e6:.2f}M</div>
            <div class="stat-delta" style="color: rgba(255,255,255,0.7)">
                Last: {data[volume_col].iloc[-1]/1e6:.2f}M
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">🏢</div>
            <div class="stat-label">Market Cap</div>
            <div class="stat-value">{'${:.2f}B'.format(ticker_info.get('marketCap', 0)/1e9) if ticker_info.get('marketCap', 0) > 1e9 else 'N/A'}</div>
            <div class="stat-delta" style="color: rgba(255,255,255,0.7)">
                P/E: {'{:.2f}'.format(ticker_info.get('trailingPE', 0)) if isinstance(ticker_info.get('trailingPE'), (int, float)) else 'N/A'}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Advanced Chart", "🤖 AI Analysis", "📊 Technical Indicators", "⚡ Backtest"])
    
    # TAB 1: Advanced Chart
    with tab1:
        st.markdown('<h3 class="section-title">Interactive Price Chart</h3>', unsafe_allow_html=True)
        
        chart_col1, chart_col2 = st.columns([3, 1])
        
        with chart_col1:
            chart_type = st.radio(
                "Chart Type",
                ["Candlestick", "Line", "Area", "OHLC"],
                horizontal=True
            )
        
        with chart_col2:
            show_volume = st.checkbox("Show Volume", value=True)
        
        st.markdown("#### Overlay Indicators")
        indicators = st.multiselect(
            "Select indicators to overlay",
            ["SMA (20)", "SMA (50)", "SMA (200)", "EMA (20)", "EMA (50)", "Bollinger Bands", "VWAP"],
            default=["SMA (20)", "SMA (50)"]
        )
        
        if show_volume:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
                subplot_titles=(f'{ticker} Price Chart', 'Volume')
            )
        else:
            fig = make_subplots(rows=1, cols=1)
        
        # Add price chart
        if chart_type == "Candlestick":
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data[open_col],
                    high=data[high_col],
                    low=data[low_col],
                    close=data[close_col],
                    name="OHLC",
                    increasing_line_color='#22c55e',
                    decreasing_line_color='#ef4444'
                ),
                row=1, col=1
            )
        elif chart_type == "Line":
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data[close_col],
                    mode='lines',
                    name='Close',
                    line=dict(color='#8b5cf6', width=2)
                ),
                row=1, col=1
            )
        elif chart_type == "Area":
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data[close_col],
                    mode='lines',
                    name='Close',
                    fill='tozeroy',
                    line=dict(color='#8b5cf6', width=2),
                    fillcolor='rgba(139, 92, 246, 0.3)'
                ),
                row=1, col=1
            )
        elif chart_type == "OHLC":
            fig.add_trace(
                go.Ohlc(
                    x=data.index,
                    open=data[open_col],
                    high=data[high_col],
                    low=data[low_col],
                    close=data[close_col],
                    name="OHLC"
                ),
                row=1, col=1
            )
        
        # Add indicators
        colors = ['#8b5cf6', '#ec4899', '#f59e0b', '#06b6d4', '#84cc16']
        color_idx = 0
        
        for indicator in indicators:
            if "SMA" in indicator:
                period = int(indicator.split('(')[1].split(')')[0])
                sma = data[close_col].rolling(window=period).mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=sma,
                        mode='lines',
                        name=f'SMA ({period})',
                        line=dict(color=colors[color_idx % len(colors)], width=2)
                    ),
                    row=1, col=1
                )
                color_idx += 1
            
            elif "EMA" in indicator:
                period = int(indicator.split('(')[1].split(')')[0])
                ema = data[close_col].ewm(span=period, adjust=False).mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=ema,
                        mode='lines',
                        name=f'EMA ({period})',
                        line=dict(color=colors[color_idx % len(colors)], width=2)
                    ),
                    row=1, col=1
                )
                color_idx += 1
            
            elif indicator == "Bollinger Bands":
                if 'BB_Upper' in data.columns:
                    bb_upper = data['BB_Upper']
                    bb_lower = data['BB_Lower']
                else:
                    sma = data[close_col].rolling(window=20).mean()
                    std = data[close_col].rolling(window=20).std()
                    bb_upper = sma + 2 * std
                    bb_lower = sma - 2 * std
                
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=bb_upper,
                        mode='lines',
                        name='BB Upper',
                        line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash')
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=bb_lower,
                        mode='lines',
                        name='BB Lower',
                        line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash'),
                        fill='tonexty',
                        fillcolor='rgba(255, 255, 255, 0.05)'
                    ),
                    row=1, col=1
                )
            
            elif indicator == "VWAP":
                vwap = (data[close_col] * data[volume_col]).cumsum() / data[volume_col].cumsum()
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=vwap,
                        mode='lines',
                        name='VWAP',
                        line=dict(color=colors[color_idx % len(colors)], width=2, dash='dot')
                    ),
                    row=1, col=1
                )
                color_idx += 1
        
        if show_volume:
            colors_volume = ['#ef4444' if data[close_col].iloc[i] < data[open_col].iloc[i] else '#22c55e' 
                           for i in range(len(data))]
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data[volume_col],
                    name='Volume',
                    marker_color=colors_volume,
                    opacity=0.5
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            height=700,
            template='plotly_dark',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=50, t=80, b=50),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False
        )
        
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
        
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 2: AI Analysis
    with tab2:
        st.markdown('<h3 class="section-title">🤖 AI-Powered Technical Analysis</h3>', unsafe_allow_html=True)
        
        st.info("⚠️ **Note**: AI Analysis requires Ollama running locally. This feature is disabled on Streamlit Cloud.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 Generate AI Analysis", use_container_width=True):
                st.warning("🔌 AI Analysis is only available when running locally with Ollama installed.")
                st.markdown("""
                **To use AI Analysis:**
                1. Install Ollama: https://ollama.ai
                2. Run: `ollama pull llama3.2-vision`
                3. Run: `ollama serve`
                4. Run this app locally: `streamlit run app.py`
                """)
        
        with col2:
            st.info("💡 **Tip**: Download and run locally for AI-powered insights!")
        
        if st.session_state.get('ai_analysis'):
            st.markdown("#### 💬 AI Analysis Report")
            st.markdown(st.session_state['ai_analysis'])
    
    # TAB 3: Technical Indicators
    with tab3:
        st.markdown('<h3 class="section-title">📊 Technical Indicators Overview</h3>', unsafe_allow_html=True)
        
        if 'RSI' in data.columns and 'MACD' in data.columns and 'BB_Upper' in data.columns:
            
            current_rsi = data['RSI'].iloc[-1]
            rsi_signal = "Oversold 🟢" if current_rsi < 30 else "Overbought 🔴" if current_rsi > 70 else "Neutral 🟡"
            rsi_color = "#22c55e" if current_rsi < 30 else "#ef4444" if current_rsi > 70 else "#f59e0b"
            
            current_macd = data['MACD'].iloc[-1]
            current_signal = data['MACD_Signal'].iloc[-1]
            macd_trend = "Bullish 🟢" if current_macd > current_signal else "Bearish 🔴"
            macd_color = "#22c55e" if current_macd > current_signal else "#ef4444"
            
            current_price_val = data[close_col].iloc[-1]
            bb_upper_val = data['BB_Upper'].iloc[-1]
            bb_lower_val = data['BB_Lower'].iloc[-1]
            bb_position = ((current_price_val - bb_lower_val) / (bb_upper_val - bb_lower_val)) * 100
            bb_signal = "Near Upper 🔴" if bb_position > 80 else "Near Lower 🟢" if bb_position < 20 else "Mid Range 🟡"
            bb_color = "#ef4444" if bb_position > 80 else "#22c55e" if bb_position < 20 else "#f59e0b"
            
            st.markdown(f"""
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-icon">📈</div>
                    <div class="stat-label">RSI (14)</div>
                    <div class="stat-value">{current_rsi:.2f}</div>
                    <div class="stat-delta" style="color: {rsi_color}">
                        {rsi_signal}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-label">MACD</div>
                    <div class="stat-value">{current_macd:.2f}</div>
                    <div class="stat-delta" style="color: {macd_color}">
                        {macd_trend}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📉</div>
                    <div class="stat-label">Bollinger Bands</div>
                    <div class="stat-value">{bb_position:.1f}%</div>
                    <div class="stat-delta" style="color: {bb_color}">
                        {bb_signal}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # RSI Chart
            st.markdown("#### RSI (Relative Strength Index)")
            rsi_fig = go.Figure()
            rsi_fig.add_trace(go.Scatter(
                x=data.index,
                y=data['RSI'],
                mode='lines',
                name='RSI',
                line=dict(color='#8b5cf6', width=2)
            ))
            rsi_fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", annotation_text="Overbought (70)")
            rsi_fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", annotation_text="Oversold (30)")
            rsi_fig.add_hrect(y0=70, y1=100, fillcolor="#ef4444", opacity=0.1, line_width=0)
            rsi_fig.add_hrect(y0=0, y1=30, fillcolor="#22c55e", opacity=0.1, line_width=0)
            
            rsi_fig.update_layout(
                height=300,
                template='plotly_dark',
                hovermode='x unified',
                showlegend=False,
                margin=dict(l=50, r=50, t=30, b=30),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(range=[0, 100])
            )
            rsi_fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            rsi_fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            st.plotly_chart(rsi_fig, use_container_width=True)
            
            # MACD Chart
            st.markdown("#### MACD (Moving Average Convergence Divergence)")
            macd_fig = go.Figure()
            macd_fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MACD'],
                mode='lines',
                name='MACD',
                line=dict(color='#8b5cf6', width=2)
            ))
            macd_fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MACD_Signal'],
                mode='lines',
                name='Signal',
                line=dict(color='#f59e0b', width=2)
            ))
            
            colors_hist = ['#22c55e' if val >= 0 else '#ef4444' for val in data['MACD_Hist']]
            macd_fig.add_trace(go.Bar(
                x=data.index,
                y=data['MACD_Hist'],
                name='Histogram',
                marker_color=colors_hist,
                opacity=0.5
            ))
            
            macd_fig.update_layout(
                height=300,
                template='plotly_dark',
                hovermode='x unified',
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=50, r=50, t=30, b=30),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            macd_fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            macd_fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
            st.plotly_chart(macd_fig, use_container_width=True)
        else:
            st.warning("Not enough data points to calculate all technical indicators (need at least 26 days).")
    
    # TAB 4: Backtest
    with tab4:
        st.markdown('<h3 class="section-title">⚡ Strategy Backtesting</h3>', unsafe_allow_html=True)
        
        bt_col1, bt_col2 = st.columns([2, 1])
        
        with bt_col1:
            strategy_type = st.selectbox(
                "Select Strategy",
                ["SMA Crossover (20/50)", "SMA Crossover (50/200)", "RSI Mean Reversion", "MACD Crossover"]
            )
        
        with bt_col2:
            initial_capital = st.number_input("Initial Capital ($)", value=10000, step=1000)
        
        if st.button("🚀 Run Backtest", use_container_width=True):
            with st.spinner("Running backtest simulation..."):
                bt_data = data.copy()
                
                if strategy_type == "SMA Crossover (20/50)":
                    bt_data['SMA_Fast'] = bt_data[close_col].rolling(20).mean()
                    bt_data['SMA_Slow'] = bt_data[close_col].rolling(50).mean()
                    bt_data['Signal'] = 0
                    bt_data.loc[bt_data['SMA_Fast'] > bt_data['SMA_Slow'], 'Signal'] = 1
                    
                elif strategy_type == "SMA Crossover (50/200)":
                    bt_data['SMA_Fast'] = bt_data[close_col].rolling(50).mean()
                    bt_data['SMA_Slow'] = bt_data[close_col].rolling(200).mean()
                    bt_data['Signal'] = 0
                    bt_data.loc[bt_data['SMA_Fast'] > bt_data['SMA_Slow'], 'Signal'] = 1
                    
                elif strategy_type == "RSI Mean Reversion":
                    if 'RSI' not in bt_data.columns:
                        delta = bt_data[close_col].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss.replace(0, np.nan)
                        bt_data['RSI'] = 100 - (100 / (1 + rs))
                    
                    bt_data['Signal'] = 0
                    bt_data.loc[bt_data['RSI'] < 30, 'Signal'] = 1
                    bt_data.loc[bt_data['RSI'] > 70, 'Signal'] = -1
                    
                elif strategy_type == "MACD Crossover":
                    if 'MACD' not in bt_data.columns:
                        exp1 = bt_data[close_col].ewm(span=12, adjust=False).mean()
                        exp2 = bt_data[close_col].ewm(span=26, adjust=False).mean()
                        bt_data['MACD'] = exp1 - exp2
                        bt_data['MACD_Signal'] = bt_data['MACD'].ewm(span=9, adjust=False).mean()
                        
                    bt_data['Signal'] = 0
                    bt_data.loc[bt_data['MACD'] > bt_data['MACD_Signal'], 'Signal'] = 1
                
                bt_data['Returns'] = bt_data[close_col].pct_change()
                bt_data['Strategy_Returns'] = bt_data['Signal'].shift(1) * bt_data['Returns']
                
                bt_data['Cumulative_Market'] = (1 + bt_data['Returns']).cumprod()
                bt_data['Cumulative_Strategy'] = (1 + bt_data['Strategy_Returns']).cumprod()
                
                bt_data = bt_data.dropna()
                
                if not bt_data.empty:
                    total_return_market = (bt_data['Cumulative_Market'].iloc[-1] - 1) * 100
                    total_return_strategy = (bt_data['Cumulative_Strategy'].iloc[-1] - 1) * 100
                    
                    final_capital_market = initial_capital * bt_data['Cumulative_Market'].iloc[-1]
                    final_capital_strategy = initial_capital * bt_data['Cumulative_Strategy'].iloc[-1]
                    
                    sharpe_market = (bt_data['Returns'].mean() / bt_data['Returns'].std()) * np.sqrt(252) if bt_data['Returns'].std() != 0 else 0
                    sharpe_strategy = (bt_data['Strategy_Returns'].mean() / bt_data['Strategy_Returns'].std()) * np.sqrt(252) if bt_data['Strategy_Returns'].std() != 0 else 0
                    
                    cumulative_market = bt_data['Cumulative_Market']
                    running_max_market = cumulative_market.expanding().max()
                    drawdown_market = ((cumulative_market - running_max_market) / running_max_market).min() * 100
                    
                    cumulative_strategy = bt_data['Cumulative_Strategy']
                    running_max_strategy = cumulative_strategy.expanding().max()
                    drawdown_strategy = ((cumulative_strategy - running_max_strategy) / running_max_strategy).min() * 100
                    
                    st.markdown("#### 📊 Backtest Results")
                    
                    result_color = "#22c55e" if total_return_strategy > total_return_market else "#ef4444"
                    
                    st.markdown(f"""
                    <div class="stat-grid">
                        <div class="stat-card" style="border-color: {result_color};">
                            <div class="stat-icon">💰</div>
                            <div class="stat-label">Strategy Return</div>
                            <div class="stat-value">{total_return_strategy:.2f}%</div>
                            <div class="stat-delta" style="color: {result_color}">
                                ${final_capital_strategy:,.2f}
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon">📈</div>
                            <div class="stat-label">Buy & Hold Return</div>
                            <div class="stat-value">{total_return_market:.2f}%</div>
                            <div class="stat-delta" style="color: rgba(255,255,255,0.7)">
                                ${final_capital_market:,.2f}
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon">📊</div>
                            <div class="stat-label">Strategy Sharpe</div>
                            <div class="stat-value">{sharpe_strategy:.2f}</div>
                            <div class="stat-delta" style="color: rgba(255,255,255,0.7)">
                                Market: {sharpe_market:.2f}
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon">📉</div>
                            <div class="stat-label">Max Drawdown</div>
                            <div class="stat-value">{drawdown_strategy:.2f}%</div>
                            <div class="stat-delta" style="color: rgba(255,255,255,0.7)">
                                Market: {drawdown_market:.2f}%
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    equity_fig = go.Figure()
                    
                    equity_fig.add_trace(go.Scatter(
                        x=bt_data.index,
                        y=bt_data['Cumulative_Strategy'] * initial_capital,
                        mode='lines',
                        name='Strategy',
                        line=dict(color='#8b5cf6', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(139, 92, 246, 0.2)'
                    ))
                    
                    equity_fig.add_trace(go.Scatter(
                        x=bt_data.index,
                        y=bt_data['Cumulative_Market'] * initial_capital,
                        mode='lines',
                        name='Buy & Hold',
                        line=dict(color='#f59e0b', width=2, dash='dash')
                    ))
                    
                    equity_fig.update_layout(
                        title="Equity Curve Comparison",
                        height=400,
                        template='plotly_dark',
                        hovermode='x unified',
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=50, r=50, t=80, b=30),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        yaxis_title="Portfolio Value ($)"
                    )
                    equity_fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
                    equity_fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
                    
                    st.plotly_chart(equity_fig, use_container_width=True)
                    
                    st.markdown("#### 📍 Trade Signals on Price Chart")
                    
                    signals_fig = go.Figure()
                    signals_fig.add_trace(go.Scatter(
                        x=bt_data.index,
                        y=bt_data[close_col],
                        mode='lines',
                        name='Price',
                        line=dict(color='#8b5cf6', width=2)
                    ))
                    
                    buy_signals = bt_data[bt_data['Signal'].diff() == 1]
                    signals_fig.add_trace(go.Scatter(
                        x=buy_signals.index,
                        y=buy_signals[close_col],
                        mode='markers',
                        name='Buy',
                        marker=dict(color='#22c55e', size=12, symbol='triangle-up')
                    ))
                    
                    sell_signals = bt_data[bt_data['Signal'].diff() == -1]
                    signals_fig.add_trace(go.Scatter(
                        x=sell_signals.index,
                        y=sell_signals[close_col],
                        mode='markers',
                        name='Sell',
                        marker=dict(color='#ef4444', size=12, symbol='triangle-down')
                    ))
                    
                    signals_fig.update_layout(
                        height=400,
                        template='plotly_dark',
                        hovermode='x unified',
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=50, r=50, t=30, b=30),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        yaxis_title="Price ($)"
                    )
                    signals_fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
                    signals_fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)')
                    
                    st.plotly_chart(signals_fig, use_container_width=True)
                else:
                    st.warning("Not enough data to run backtest with selected parameters.")
    
    # Export Report Section
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    st.markdown('<h3 class="section-title">📥 Export Analysis</h3>', unsafe_allow_html=True)
    
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        csv = data.to_csv()
        st.download_button(
            "📊 Download Data (CSV)",
            csv,
            file_name=f"{ticker}_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with export_col2:
        if st.button("📈 Generate Report", use_container_width=True):
            st.info("💡 PDF reports available with AI analysis!")
    
    with export_col3:
        st.info("💡 Run locally for full export features")

else:
    # Welcome Screen
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <h2 style="color: #8b5cf6; margin-bottom: 1rem; font-size: 2.5rem;">👋 Welcome to Stock Analysis Pro</h2>
        <p style="font-size: 1.2rem; color: rgba(255,255,255,0.6); margin-bottom: 3rem;">
            Get started by entering a stock ticker in the sidebar
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: rgba(139, 92, 246, 0.05); padding: 3rem 2rem; border-radius: 24px; border: 1px solid rgba(139, 92, 246, 0.2); text-align: center;">
            <div style="font-size: 3.5rem; margin-bottom: 1.5rem;">📈</div>
            <h3 style="color: #8b5cf6; margin-bottom: 1rem;">Advanced Charts</h3>
            <p style="color: rgba(255,255,255,0.6); line-height: 1.7;">Interactive candlestick charts with multiple technical indicators and real-time data</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: rgba(139, 92, 246, 0.05); padding: 3rem 2rem; border-radius: 24px; border: 1px solid rgba(139, 92, 246, 0.2); text-align: center;">
            <div style="font-size: 3.5rem; margin-bottom: 1.5rem;">🤖</div>
            <h3 style="color: #8b5cf6; margin-bottom: 1rem;">AI Analysis</h3>
            <p style="color: rgba(255,255,255,0.6); line-height: 1.7;">Get intelligent insights powered by Llama Vision AI (local deployment)</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: rgba(139, 92, 246, 0.05); padding: 3rem 2rem; border-radius: 24px; border: 1px solid rgba(139, 92, 246, 0.2); text-align: center;">
            <div style="font-size: 3.5rem; margin-bottom: 1.5rem;">⚡</div>
            <h3 style="color: #8b5cf6; margin-bottom: 1rem;">Backtesting</h3>
            <p style="color: rgba(255,255,255,0.6); line-height: 1.7;">Test trading strategies with historical data and performance metrics</p>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
st.markdown("""
<div style="text-align: center; color: rgba(255,255,255,0.5); padding: 2rem;">
    <p style="font-size: 1rem; margin-bottom: 0.5rem;">Built with ❤️ using Streamlit • Powered by yFinance & Ollama AI</p>
    <p style="font-size: 0.9rem;">⚠️ For educational purposes only. Not financial advice.</p>
</div>
""", unsafe_allow_html=True)
