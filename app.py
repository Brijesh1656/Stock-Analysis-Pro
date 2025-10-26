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
@st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
def fetch_stock_data(ticker, start_date, end_date, max_retries=3):
    """Fetch stock data with retry logic and rate limit handling"""
    for attempt in range(max_retries):
        try:
            # Add delay between attempts
            if attempt > 0:
                time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
            
            df = yf.download(
                ticker, 
                start=start_date, 
                end=end_date, 
                progress=False,
                auto_adjust=True  # Fix the FutureWarning
            )
            
            # Flatten MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join([str(i) for i in col]).strip().rstrip('_') for col in df.columns.values]
            
            return df, None  # Success
            
        except Exception as e:
            error_msg = str(e)
            if "Rate" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    continue  # Retry
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
    
    # 1. RSI (Relative Strength Index)
    delta = df_copy[close_col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan) 
    df_copy['RSI'] = 100 - (100 / (1 + rs))
    
    # 2. MACD (Moving Average Convergence Divergence)
    exp1 = df_copy[close_col].ewm(span=12, adjust=False).mean()
    exp2 = df_copy[close_col].ewm(span=26, adjust=False).mean()
    df_copy['MACD'] = exp1 - exp2
    df_copy['MACD_Signal'] = df_copy['MACD'].ewm(span=9, adjust=False).mean()
    df_copy['MACD_Hist'] = df_copy['MACD'] - df_copy['MACD_Signal']
    
    # 3. Bollinger Bands (20 period, 2 stdev)
    df_copy['BB_Middle'] = df_copy[close_col].rolling(window=20).mean()
    std = df_copy[close_col].rolling(window=20).std()
    df_copy['BB_Upper'] = df_copy['BB_Middle'] + (2 * std)
    df_copy['BB_Lower'] = df_copy['BB_Middle'] - (2 * std)
    
    return df_copy

# Page config with custom theme
st.set_page_config(
    page_title="Stock Analysis Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --success-color: #10b981;
        --danger-color: #ef4444;
        --warning-color: #f59e0b;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 48px rgba(0,0,0,0.15);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: white;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.8);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-change {
        font-size: 1rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1e1e2e 0%, #2d2d44 100%);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(99, 102, 241, 0.1);
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(99, 102, 241, 0.2);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid;
    }
    
    /* Chart container */
    .chart-container {
        background: rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    /* Loading animation */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Multiselect styling */
    .stMultiSelect [data-baseweb="tag"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📈 Stock Analysis Pro</h1>
    <p>AI-Powered Technical Analysis & Market Intelligence</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'stock_data' not in st.session_state:
    st.session_state['stock_data'] = None
if 'ai_analysis' not in st.session_state:
    st.session_state['ai_analysis'] = None
if 'ticker_info' not in st.session_state:
    st.session_state['ticker_info'] = None

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    ticker = st.text_input(
        "Stock Ticker",
        value="AAPL",
        placeholder="e.g., AAPL, MSFT, TSLA",
        help="Enter a valid stock ticker symbol"
    ).upper()
    
    st.markdown("---")
    
    # Date range with presets
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
    
    st.markdown("---")
    
    fetch_btn = st.button("🚀 Fetch Data", use_container_width=True)
    
    if fetch_btn:
        with st.spinner(f"Fetching data for {ticker}..."):
            # Fetch stock data with retry logic
            df, error = fetch_stock_data(ticker, start_date, end_date)
            
            if error:
                st.error(error)
                if "rate limit" in error.lower():
                    st.info("💡 **Tip**: Try again in 1-2 minutes or use a different ticker.")
            elif df.empty:
                st.error("❌ No data found for this ticker and date range.")
            else:
                # Fetch ticker info
                ticker_info = fetch_ticker_info(ticker)
                
                st.session_state['stock_data'] = df
                st.session_state['ticker_info'] = ticker_info
                st.success(f"✅ Loaded {len(df)} days of data!")
    
    # Show data info if available
    if st.session_state['stock_data'] is not None:
        st.markdown("---")
        st.markdown("### 📊 Data Info")
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
            st.warning("Not enough clean data after calculating technical indicators. Charts may be incomplete.")
    
    # Key Metrics Row
    st.markdown("### 📊 Key Metrics")
    
    if data.empty:
        st.warning("Data is empty. Please check your selected date range or ticker.")
        st.stop()
        
    current_price = data[close_col].iloc[-1]
    prev_price = data[close_col].iloc[-2] if len(data) > 1 else current_price
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0
    
    # Calculate additional metrics
    high_52w = data[high_col].tail(252).max() if len(data) >= 252 else data[high_col].max()
    low_52w = data[low_col].tail(252).min() if len(data) >= 252 else data[low_col].min()
    avg_volume = data[volume_col].tail(20).mean()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Current Price</div>
            <div class="metric-value">${current_price:.2f}</div>
            <div class="metric-change" style="color: {'#10b981' if price_change >= 0 else '#ef4444'}">
                {'+' if price_change >= 0 else ''}{price_change:.2f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">52W High</div>
            <div class="metric-value">${high_52w:.2f}</div>
            <div class="metric-change" style="color: rgba(255,255,255,0.7)">
                {((current_price / high_52w - 1) * 100):.1f}% from high
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">52W Low</div>
            <div class="metric-value">${low_52w:.2f}</div>
            <div class="metric-change" style="color: rgba(255,255,255,0.7)">
                {((current_price / low_52w - 1) * 100):.1f}% from low
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Volume (20D)</div>
            <div class="metric-value">{avg_volume/1e6:.2f}M</div>
            <div class="metric-change" style="color: rgba(255,255,255,0.7)">
                Last: {data[volume_col].iloc[-1]/1e6:.2f}M
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        market_cap = ticker_info.get('marketCap', 0)
        if market_cap > 0:
            market_cap_str = f"${market_cap/1e9:.2f}B" if market_cap > 1e9 else f"${market_cap/1e6:.2f}M"
        else:
            market_cap_str = "N/A"
        
        pe_ratio = ticker_info.get('trailingPE', 'N/A')
        pe_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Market Cap</div>
            <div class="metric-value">{market_cap_str}</div>
            <div class="metric-change" style="color: rgba(255,255,255,0.7)">
                P/E: {pe_str}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Advanced Chart", "🤖 AI Analysis", "📊 Technical Indicators", "⚡ Backtest"])
    
    # TAB 1: Advanced Chart
    with tab1:
        st.markdown("### Interactive Price Chart")
        
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
                    increasing_line_color='#10b981',
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
                    line=dict(color='#667eea', width=2)
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
                    line=dict(color='#667eea', width=2),
                    fillcolor='rgba(102, 126, 234, 0.3)'
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
            colors_volume = ['#ef4444' if data[close_col].iloc[i] < data[open_col].iloc[i] else '#10b981' 
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
        st.markdown("### 🤖 AI-Powered Technical Analysis")
        
        # Check if Ollama is likely available (local only)
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
        st.markdown("### 📊 Technical Indicators Overview")
        
        if 'RSI' in data.columns and 'MACD' in data.columns and 'BB_Upper' in data.columns:
            
            ind_col1, ind_col2, ind_col3 = st.columns(3)

            with ind_col1:
                current_rsi = data['RSI'].iloc[-1]
                rsi_signal = "Oversold 🟢" if current_rsi < 30 else "Overbought 🔴" if current_rsi > 70 else "Neutral 🟡"
                rsi_color = "#10b981" if current_rsi < 30 else "#ef4444" if current_rsi > 70 else "#f59e0b"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">RSI (14)</div>
                    <div class="metric-value">{current_rsi:.2f}</div>
                    <div class="metric-change" style="color: {rsi_color}">
                        {rsi_signal}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with ind_col2:
                current_macd = data['MACD'].iloc[-1]
                current_signal = data['MACD_Signal'].iloc[-1]
                macd_trend = "Bullish 🟢" if current_macd > current_signal else "Bearish 🔴"
                macd_color = "#10b981" if current_macd > current_signal else "#ef4444"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">MACD</div>
                    <div class="metric-value">{current_macd:.2f}</div>
                    <div class="metric-change" style="color: {macd_color}">
                        {macd_trend}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with ind_col3:
                current_price_val = data[close_col].iloc[-1]
                bb_upper_val = data['BB_Upper'].iloc[-1]
                bb_lower_val = data['BB_Lower'].iloc[-1]
                bb_position = ((current_price_val - bb_lower_val) / (bb_upper_val - bb_lower_val)) * 100
                bb_signal = "Near Upper 🔴" if bb_position > 80 else "Near Lower 🟢" if bb_position < 20 else "Mid Range 🟡"
                bb_color = "#ef4444" if bb_position > 80 else "#10b981" if bb_position < 20 else "#f59e0b"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Bollinger Bands</div>
                    <div class="metric-value">{bb_position:.1f}%</div>
                    <div class="metric-change" style="color: {bb_color}">
                        {bb_signal}
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
                line=dict(color='#667eea', width=2)
            ))
            rsi_fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", annotation_text="Overbought (70)")
            rsi_fig.add_hline(y=30, line_dash="dash", line_color="#10b981", annotation_text="Oversold (30)")
            rsi_fig.add_hrect(y0=70, y1=100, fillcolor="#ef4444", opacity=0.1, line_width=0)
            rsi_fig.add_hrect(y0=0, y1=30, fillcolor="#10b981", opacity=0.1, line_width=0)
            
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
                line=dict(color='#667eea', width=2)
            ))
            macd_fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MACD_Signal'],
                mode='lines',
                name='Signal',
                line=dict(color='#f59e0b', width=2)
            ))
            
            colors_hist = ['#10b981' if val >= 0 else '#ef4444' for val in data['MACD_Hist']]
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
            st.warning("Not enough data points to calculate all technical indicators (need at least 26 days). Please select a longer date range.")

    # TAB 4: Backtest
    with tab4:
        st.markdown("### ⚡ Strategy Backtesting")
        
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
                    
                    result_col1, result_col2, result_col3, result_col4 = st.columns(4)
                    
                    with result_col1:
                        st.markdown(f"""
                        <div class="metric-card" style="background: linear-gradient(135deg, {'#10b981' if total_return_strategy > total_return_market else '#ef4444'} 0%, {'#059669' if total_return_strategy > total_return_market else '#dc2626'} 100%);">
                            <div class="metric-label">Strategy Return</div>
                            <div class="metric-value">{total_return_strategy:.2f}%</div>
                            <div class="metric-change" style="color: white">
                                ${final_capital_strategy:,.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with result_col2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Buy & Hold Return</div>
                            <div class="metric-value">{total_return_market:.2f}%</div>
                            <div class="metric-change" style="color: rgba(255,255,255,0.7)">
                                ${final_capital_market:,.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with result_col3:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Strategy Sharpe</div>
                            <div class="metric-value">{sharpe_strategy:.2f}</div>
                            <div class="metric-change" style="color: rgba(255,255,255,0.7)">
                                Market: {sharpe_market:.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with result_col4:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Max Drawdown</div>
                            <div class="metric-value">{drawdown_strategy:.2f}%</div>
                            <div class="metric-change" style="color: rgba(255,255,255,0.7)">
                                Market: {drawdown_market:.2f}%
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
                        line=dict(color='#667eea', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(102, 126, 234, 0.2)'
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
                        line=dict(color='#667eea', width=2)
                    ))
                    
                    buy_signals = bt_data[bt_data['Signal'].diff() == 1]
                    signals_fig.add_trace(go.Scatter(
                        x=buy_signals.index,
                        y=buy_signals[close_col],
                        mode='markers',
                        name='Buy',
                        marker=dict(color='#10b981', size=12, symbol='triangle-up')
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
    st.markdown("---")
    st.markdown("### 📑 Export Analysis Report")
    
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        if st.button("📊 Download Full Report (PDF)", use_container_width=True):
            if st.session_state.get('ai_analysis'):
                try:
                    doc = SimpleDocTemplate("stock_analysis_report.pdf", pagesize=letter)
                    styles = getSampleStyleSheet()
                    
                    title_style = ParagraphStyle(
                        'CustomTitle',
                        parent=styles['Heading1'],
                        fontSize=24,
                        textColor='#667eea',
                        spaceAfter=30,
                        alignment=TA_CENTER
                    )
                    
                    content = []
                    content.append(Paragraph(f"Stock Analysis Report: {ticker}", title_style))
                    content.append(Spacer(1, 12))
                    content.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
                    content.append(Spacer(1, 12))
                    content.append(Paragraph(f"Date Range: {start_date} to {end_date}", styles['Normal']))
                    content.append(Spacer(1, 24))
                    
                    content.append(Paragraph("Key Metrics", styles['Heading2']))
                    content.append(Paragraph(f"Current Price: ${current_price:.2f}", styles['Normal']))
                    content.append(Paragraph(f"Price Change: {price_change:+.2f} ({price_change_pct:+.2f}%)", styles['Normal']))
                    content.append(Paragraph(f"52-Week High: ${high_52w:.2f}", styles['Normal']))
                    content.append(Paragraph(f"52-Week Low: ${low_52w:.2f}", styles['Normal']))
                    content.append(Spacer(1, 24))
                    
                    content.append(Paragraph("AI Analysis", styles['Heading2']))
                    analysis_text = st.session_state['ai_analysis'].replace('\n', '<br/>')
                    content.append(Paragraph(analysis_text, styles['Normal']))
                    
                    doc.build(content)
                    
                    with open("stock_analysis_report.pdf", "rb") as pdf_file:
                        st.download_button(
                            "📥 Download PDF",
                            pdf_file,
                            file_name=f"{ticker}_analysis_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    os.remove("stock_analysis_report.pdf")
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
            else:
                st.warning("Please generate AI analysis first!")
    
    with export_col2:
        if st.button("📈 Download Data (CSV)", use_container_width=True):
            csv = data.to_csv()
            st.download_button(
                "📥 Download CSV",
                csv,
                file_name=f"{ticker}_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with export_col3:
        st.info("💡 Generate AI analysis to unlock PDF reports!")

else:
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem;">
        <h2 style="color: #667eea; margin-bottom: 1rem;">👋 Welcome to Stock Analysis Pro</h2>
        <p style="font-size: 1.2rem; color: rgba(255,255,255,0.7); margin-bottom: 2rem;">
            Get started by entering a stock ticker and fetching data from the sidebar
        </p>
        <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 3rem;">
            <div style="background: rgba(102, 126, 234, 0.1); padding: 2rem; border-radius: 12px; max-width: 300px;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📈</div>
                <h3 style="color: #667eea;">Advanced Charts</h3>
                <p style="color: rgba(255,255,255,0.6)">Interactive candlestick charts with multiple technical indicators</p>
            </div>
            <div style="background: rgba(102, 126, 234, 0.1); padding: 2rem; border-radius: 12px; max-width: 300px;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🤖</div>
                <h3 style="color: #667eea;">AI Analysis</h3>
                <p style="color: rgba(255,255,255,0.6)">Get intelligent insights powered by Llama Vision AI</p>
            </div>
            <div style="background: rgba(102, 126, 234, 0.1); padding: 2rem; border-radius: 12px; max-width: 300px;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">⚡</div>
                <h3 style="color: #667eea;">Backtesting</h3>
                <p style="color: rgba(255,255,255,0.6)">Test trading strategies with historical data</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: rgba(255,255,255,0.5); padding: 2rem;">
    <p>Built with ❤️ using Streamlit • Powered by yFinance & Ollama AI</p>
    <p style="font-size: 0.9rem; margin-top: 0.5rem;">⚠️ For educational purposes only. Not financial advice.</p>
</div>
""", unsafe_allow_html=True)
