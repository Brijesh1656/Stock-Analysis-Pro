# Stock-Analysis-Pro

# 📈 Stock Analysis Pro

> AI-Powered Technical Analysis & Market Intelligence Platform

A comprehensive stock analysis application that combines real-time market data, advanced technical indicators, and AI-powered insights to help traders make informed decisions.

## 🚀 Live Demo
Check out the live app here 👉 [Stock Analysis Pro on Streamlit](https://stock-analysispro.streamlit.app/)


---

## ✨ Features

### 📊 Advanced Charting
- **Multiple Chart Types**: Candlestick, Line, Area, and OHLC charts
- **Technical Indicators**: 
  - Moving Averages (SMA 20/50/200, EMA 20/50)
  - Bollinger Bands
  - Volume-Weighted Average Price (VWAP)
- **Interactive Visualizations**: Zoom, pan, and hover for detailed data points
- **Custom Date Ranges**: Quick presets or custom date selection

### 🤖 AI-Powered Analysis
- **Llama Vision AI Integration**: Intelligent chart pattern recognition
- **Automated Trading Signals**: AI-generated buy/sell recommendations
- **Risk Assessment**: Automated stop-loss and risk level identification
- **Trend Analysis**: Real-time market trend detection and forecasting

### 📉 Technical Indicators Dashboard
- **RSI (Relative Strength Index)**: Identify overbought/oversold conditions
- **MACD (Moving Average Convergence Divergence)**: Spot trend reversals
- **Bollinger Bands**: Measure market volatility and price levels
- **Visual Signals**: Color-coded indicators for quick decision-making

### ⚡ Strategy Backtesting
- **Multiple Trading Strategies**:
  - SMA Crossover (20/50, 50/200)
  - RSI Mean Reversion
  - MACD Crossover
- **Performance Metrics**:
  - Total Returns & Sharpe Ratio
  - Maximum Drawdown
  - Win Rate & Risk-Adjusted Returns
- **Visual Equity Curves**: Compare strategy vs. buy-and-hold
- **Trade Signal Visualization**: See exact entry/exit points on charts

### 📑 Export & Reporting
- **PDF Reports**: Professional analysis reports with AI insights
- **CSV Data Export**: Download historical price data
- **Custom Branding**: Clean, professional report formatting

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Ollama (for AI analysis features)

### Installation

1. **Clone the repository**
```bash
https://github.com/Brijesh1656/Stock-Analysis-Pro.git
```

2. **Install required packages**
```bash
pip install streamlit yfinance pandas plotly ollama reportlab numpy
```

3. **Install and setup Ollama** (for AI features)
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.2-vision
ollama serve
```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

---

## 📖 Usage Guide

### 1. Fetch Stock Data
- Enter a stock ticker symbol (e.g., AAPL, MSFT, TSLA)
- Select a date range using presets or custom dates
- Click "🚀 Fetch Data" to load market data

### 2. Analyze Charts
- Navigate to the **Advanced Chart** tab
- Choose chart type (Candlestick, Line, Area, OHLC)
- Add technical indicators using the multiselect dropdown
- Toggle volume display on/off

### 3. Get AI Insights
- Go to the **AI Analysis** tab
- Click "🚀 Generate AI Analysis"
- Review AI-powered trading recommendations
- Get specific entry/exit points and risk levels

### 4. Review Technical Indicators
- Check the **Technical Indicators** tab
- View RSI, MACD, and Bollinger Bands
- Interpret color-coded signals (🟢 Bullish, 🔴 Bearish, 🟡 Neutral)

### 5. Backtest Strategies
- Navigate to the **Backtest** tab
- Select a trading strategy
- Set initial capital amount
- Click "🚀 Run Backtest" to see results
- Compare strategy performance vs. buy-and-hold

### 6. Export Reports
- Generate AI analysis first
- Click "📊 Download Full Report (PDF)" for complete analysis
- Or download raw data using "📈 Download Data (CSV)"

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **Streamlit** | Web application framework |
| **yFinance** | Real-time stock data fetching |
| **Plotly** | Interactive chart visualizations |
| **Pandas** | Data manipulation and analysis |
| **NumPy** | Numerical computations |
| **Ollama AI** | AI-powered chart analysis |
| **ReportLab** | PDF report generation |

---

## 📊 Supported Technical Indicators

### Trend Indicators
- Simple Moving Average (SMA): 20, 50, 200 periods
- Exponential Moving Average (EMA): 20, 50 periods
- Volume-Weighted Average Price (VWAP)

### Momentum Indicators
- Relative Strength Index (RSI): 14-period
- Moving Average Convergence Divergence (MACD): 12/26/9

### Volatility Indicators
- Bollinger Bands: 20-period, 2 standard deviations

---

## 🎯 Use Cases

- **Day Traders**: Quick technical analysis and AI-powered entry/exit signals
- **Swing Traders**: Medium-term trend analysis and strategy backtesting
- **Long-term Investors**: Fundamental analysis support and risk assessment
- **Students**: Learn technical analysis and trading strategies
- **Researchers**: Backtest and validate trading hypotheses

---

## ⚠️ Disclaimer

**This application is for educational and informational purposes only.**

- Not financial advice
- Past performance does not guarantee future results
- Always do your own research before making investment decisions
- Consider consulting with a qualified financial advisor

---

### Feature Ideas
- [ ] Add more technical indicators (Fibonacci, Ichimoku Cloud)
- [ ] Support for cryptocurrency analysis
- [ ] Portfolio tracking and management
- [ ] Real-time alerts and notifications
- [ ] Social sentiment analysis integration
- [ ] Multi-timeframe analysis


## 👨‍💻 Author

**Brijesh Singh**

- GitHub: [@Brijesh1656](https://github.com/Brijesh1656)
- LinkedIn: [brijesh-singh-b84275307](https://linkedin.com/in/brijesh-singh-b84275307)
- Email: brijesh7146@gmail.com

---

## 🐛 Known Issues

- AI analysis requires Ollama to be running locally
- PDF generation may fail if analysis is not generated first
- Some indicators require minimum data points (e.g., 200 days for SMA 200)

---

## 📈 Roadmap

- **v1.1**: Add cryptocurrency support
- **v1.2**: Real-time streaming data
- **v1.3**: Portfolio management features
- **v2.0**: Mobile app version

---


**⭐ Star this repo if you find it helpful!**

Made with ❤️ and ☕ by Brijesh Singh
