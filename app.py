import requests
import pandas as pd
import streamlit as st
import yfinance as yf  # Додано імпорт
from datetime import datetime

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="FTMO Sentinel PRO", layout="wide")

# 1. ТЕХНІЧНІ ДАНІ FTMO
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

# Виправлена функція отримання ціни
@st.cache_data(ttl=5) # Збільшив до 5 сек для стабільності
def get_price_safe(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        # Використовуємо history замість fast_info, це надійніше на Streamlit Cloud
        data = t.history(period="1d", interval="1m")
        if not data.empty:
            return data['Close'].iloc[-1]
        return None
    except:
        return None

# НОВА СТАБІЛЬНА ФУНКЦІЯ НОВИН
@st.cache_data(ttl=600)
def get_sentinel_macro_stable():
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        events = []
        for item in data:
            if item['country'] in ["USD", "JPY", "EUR", "GBP"]:
                impact_map = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}
                impact_icon = impact_map.get(item['impact'], "⚪")
                
                # Коректне форматування часу
                dt_obj = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
                event_time = dt_obj.strftime("%H:%M")
                event_date = dt_obj.strftime("%m-%d")
                
                events.append({
                    "Дата": event_date,
                    "Час": event_time,
                    "Валюта": item['country'],
                    "Подія": item['title'],
                    "Вплив": impact_icon,
                    "Прогноз": item.get('forecast', '-'),
                    "Попереднє": item.get('previous', '-')
                })
        
        df = pd.DataFrame(events)
        return df
    except Exception as e:
        return pd.DataFrame()

# --- ВЕРХНЯ ПАНЕЛЬ ---
st.title("🛰 FTMO Sentinel: Intelligence & Risk")
cols = st.columns(4)
with cols[0]:
    val = get_price_safe("DX-Y.NYB")
    st.metric("DXY (Долар)", f"{val:.2f}" if val else "---")
with cols[1]:
    val = get_price_safe("^VIX")
    st.metric("VIX (Страх)", f"{val:.2f}" if val else "---")
with cols[2]:
    val = get_price_safe("GC=F")
    st.metric("Gold (XAU)", f"${val:.2f}" if val else "---")
with cols[3]:
    val = get_price_safe("^GSPC")
    st.metric("S&P 500", f"{val:.2f}" if val else "---")

tab1, tab2 = st.tabs(["🧮 Calculator", "📊 Macro Intelligence"])

with tab1:
    PRICE_TICKERS = {
        "XAUUSD": "GC=F", "XAGUSD": "SI=F", "XCUUSD": "HG=F",
        "EURUSD": "EURUSD=X", "US100": "NQ=F", "GER40": "YM=F",
        "DXY": "DX-Y.NYB", "JP225": "NK=F"
    }

    st.sidebar.header("🛡 Ризик-менеджмент")
    three_losses = st.sidebar.toggle("3 поспіль SL (Ризик 0.5%)")
    
    col1, col2 = st.columns(2)
    with col1:
        balance = st.number_input("Баланс ($)", value=100000.0, step=1000.0)
        risk_pct = 0.5 if three_losses else 1.0
        st.info(f"Ризик: **{risk_pct}%**")
        
    with col2:
        asset = st.selectbox("Актив", list(FTMO_SPECS.keys()))
        sl_points = st.number_input("Stop Loss (points)", value=100.0, step=1.0)

    current_price = get_price_safe(PRICE_TICKERS.get(asset))
    if current_price:
        prec = 5 if asset == "EURUSD" else (3 if asset in ["XAGUSD", "DXY"] else 2)
        st.markdown(f"### ⚡ Поточна ціна {asset}: `{current_price:.{prec}f}`")

    spec = FTMO_SPECS[asset]
    risk_usd = balance * (risk_pct / 100)
    one_point_val = spec['val'] / spec['tick']
    
    conv_rate = 1.0
    if spec['curr'] != "USD":
        val_conv = get_price_safe(f"{spec['curr']}USD=X")
        conv_rate = val_conv if val_conv else 1.0

    raw_lot = risk_usd / (sl_points * one_point_val * conv_rate)
    final_lot = max(round(raw_lot, 2), 0.01)

    st.divider()
    st.success(f"## Рекомендований лот: **{final_lot}**")

with tab2:
    st.header("📈 Macro Intelligence Hub")
    
    TV_TICKERS = {
        "DXY (Index)": "CAPITALCOM:DXY",
        "XAUUSD (Gold)": "OANDA:XAUUSD",
        "JP225 (Nikkei)": "CAPITALCOM:JP225",
        "US100 (Nasdaq)": "CAPITALCOM:US100",
        "EURUSD": "OANDA:EURUSD"
    }
    selected_asset = st.selectbox("Інструмент для аналізу:", list(TV_TICKERS.keys()))
    
    tv_widget = f"""
    <div style="height: 500px;">
      <div id="tradingview_chart" style="height: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true, "symbol": "{TV_TICKERS[selected_asset]}", "interval": "15",
        "timezone": "Europe/Kyiv", "theme": "dark", "style": "1", "locale": "uk",
        "toolbar_bg": "#f1f3f6", "enable_publishing": false, "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    st.components.v1.html(tv_widget, height=500)

    st.divider()
    st.subheader("🤖 Sentinel AI: Аналіз")
    ca1, ca2 = st.columns(2)
    with ca1:
        st.info("🎯 **Сценарій XAUUSD:** Слідкуй за DXY. CPI > прогноз = Gold 📉.")
    with ca2:
        st.warning("🏮 **Сценарій JP225:** USDJPY вгору = Nikkei 🚀. Слабкість єни — союзник.")

    st.divider()
    st.subheader("📡 Sentinel Macro Stream (Verified)")
    
    macro_df = get_sentinel_macro_stable()
    
    if not macro_df.empty:
        st.dataframe(
            macro_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Вплив": st.column_config.TextColumn("Impact", width="small"),
                "Дата": st.column_config.TextColumn("Date", width="small"),
                "Час": st.column_config.TextColumn("Time", width="small"),
            }
        )
    else:
        st.error("🔌 Помилка зв'язку з сервером новин.")

    st.caption("✅ Джерело: JSON Stream. Фільтр: USD, JPY, EUR, GBP.")