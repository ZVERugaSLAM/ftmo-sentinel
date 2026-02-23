import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components # Використовуємо стандартний компонент
from datetime import datetime

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="FTMO Sentinel PRO", layout="wide")

# 1. ТЕХНІЧНІ ДАНІ FTMO (з твоїх скріншотів)
FTMO_SPECS = {
    "XAUUSD": {"contract": 100, "tick": 0.01, "val": 1.00, "curr": "USD"},
    "XAGUSD": {"contract": 5000, "tick": 0.001, "val": 5.00, "curr": "USD"},
    "XCUUSD": {"contract": 100, "tick": 0.01, "val": 1.00, "curr": "USD"},
    "EURUSD": {"contract": 100000, "tick": 0.00001, "val": 1.00, "curr": "USD"},
    "US100":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "USD"},
    "GER40":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "EUR"},
    "DXY":    {"contract": 100, "tick": 0.001, "val": 0.10, "curr": "USD"},
    "JP225":  {"contract": 10, "tick": 0.01, "val": 0.10, "curr": "JPY"}
}

# --- ВЕРХНЯ ПАНЕЛЬ (Real-time Market Pulse) ---
st.title("🛰 FTMO Sentinel: Intelligence & Risk")
cols = st.columns(4)
with cols[0]:
    dxy = yf.Ticker("DX-Y.NYB").fast_info['last_price']
    st.metric("DXY (Долар)", f"{dxy:.2f}")
with cols[1]:
    vix = yf.Ticker("^VIX").fast_info['last_price']
    st.metric("VIX (Індекс страху)", f"{vix:.2f}", delta="-Волатильність" if vix < 20 else "+Ризик", delta_color="inverse")
with cols[2]:
    gold = yf.Ticker("GC=F").fast_info['last_price']
    st.metric("Gold (XAU)", f"${gold:.2f}")
with cols[3]:
    sp500 = yf.Ticker("^GSPC").fast_info['last_price']
    st.metric("S&P 500", f"{sp500:.2f}")

# --- РОЗПОДІЛ НА ВКЛАДКИ ---
tab1, tab2 = st.tabs(["🧮 Calculator", "📊 Macro Intelligence"])

with tab1:
    # Твій перевірений калькулятор
    st.sidebar.header("🛡 Ризик-менеджмент")
    three_losses = st.sidebar.toggle("3 збитки поспіль (Ризик 0.5%)")
    
    col1, col2 = st.columns(2)
    with col1:
        balance = st.number_input("Баланс ($)", value=100000, step=1000)
        risk_pct = st.selectbox("Ризик %", [1.0, 0.5, 0.25], index=0 if not three_losses else 1)
    with col2:
        asset = st.selectbox("Актив", list(FTMO_SPECS.keys()))
        sl_points = st.number_input("Stop Loss (points)", value=100, step=10)

    spec = FTMO_SPECS[asset]
    risk_usd = balance * (0.005 if three_losses else (risk_pct / 100))
    
    # Розрахунок лота
    one_point_val = spec['val'] / spec['tick']
    lot = risk_usd / (sl_points * one_point_val)
    final_lot = max(round(lot, 2), 0.01)

    st.success(f"### Рекомендований лот: **{final_lot}**")
    st.write(f"💵 Ризик у грошах: **${risk_usd:.2f}**")

with tab2:
    st.header("📈 Технічний аналіз (TradingView)")
    
    # Вибір інструменту
    tv_symbol = st.selectbox("Оберіть інструмент:", 
                            ["FX_IDC:DXY", "OANDA:XAUUSD", "OANDA:EURUSD", "CAPITALCOM:US100", "CAPITALCOM:DE40"],
                            key="macro_asset_selector") # Додано унікальний ключ
    
    tradingview_widget = f"""
    <div class="tradingview-widget-container" style="height: 600px;">
      <div id="tradingview_chart" style="height: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "15",
        "timezone": "Europe/Kyiv",
        "theme": "dark",
        "style": "1",
        "locale": "uk",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "hide_side_toolbar": false, 
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    
    # Виклик компонента
    components.html(tradingview_widget, height=600, key=f"tv_chart_{tv_symbol}")
    
    st.markdown("---")
    st.subheader("📅 Macro Calendar")
    # Тут лишаємо твою таблицю новин, яку ми створили раніше
    events = [
        {"Час (EET)": "15:30", "Подія": "Core CPI m/m", "Важливість": "🔴 High", "Валюта": "USD", "Прогноз": "0.3%", "Попереднє": "0.2%"},
        {"Час (EET)": "21:00", "Подія": "FOMC Meeting Minutes", "Важливість": "🔴 High", "Валюта": "USD", "Прогноз": "-", "Попереднє": "-"}
    ]
    st.table(pd.DataFrame(events))