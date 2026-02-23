import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
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

@st.cache_data(ttl=2)
def get_price_safe(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        return ticker.fast_info['last_price']
    except:
        return None

# --- SENTINEL MACRO ENGINE (Парсинг новин) ---
@st.cache_data(ttl=300) # Оновлення кожні 5 хвилин
def get_sentinel_macro():
    try:
        url = "https://www.dailyfx.com/economic-calendar"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        # Пошук рядків подій у календарі DailyFX
        rows = soup.find_all('div', class_='dfx-economicCalendar__eventRow')
        
        for row in rows:
            try:
                curr_element = row.find('span', class_='dfx-economicCalendar__currency')
                curr = curr_element.text.strip() if curr_element else ""
                
                # Фільтр для твоїх основних активів
                if curr in ["USD", "JPY", "EUR", "GBP"]:
                    time = row.find('div', class_='dfx-economicCalendar__time').text.strip()
                    title = row.find('div', class_='dfx-economicCalendar__eventTitle').text.strip()
                    
                    # Визначення важливості
                    importance_div = row.find('div', class_='dfx-economicCalendar__importance')
                    imp_text = importance_div.get('class', []) if importance_div else []
                    importance = "🔴" if "high" in str(imp_text).lower() else "🟠"
                    
                    events.append({
                        "Час": time,
                        "Валюта": curr,
                        "Подія": title,
                        "Вплив": importance
                    })
            except:
                continue
        
        return pd.DataFrame(events)
    except Exception as e:
        return pd.DataFrame(columns=["Статус"], data=[["Помилка завантаження даних"]])

# --- ВЕРХНЯ ПАНЕЛЬ ---
st.title("🛰 FTMO Sentinel: Intelligence & Risk")
cols = st.columns(4)
# (Метрики залишаються як були)
with cols[0]:
    val = get_price_safe("DX-Y.NYB")
    st.metric("DXY (Долар)", f"{val:.2f}" if val else "---")
with cols[1]:
    val = get_price_safe("^VIX")
    st.metric("VIX (Індекс страху)", f"{val:.2f}" if val else "---")
with cols[2]:
    val = get_price_safe("GC=F")
    st.metric("Gold (XAU)", f"${val:.2f}" if val else "---")
with cols[3]:
    val = get_price_safe("^GSPC")
    st.metric("S&P 500", f"{val:.2f}" if val else "---")

# --- ВКЛАДКИ ---
tab1, tab2 = st.tabs(["🧮 Calculator", "📊 Macro Intelligence"])

with tab1:
    # (Блок калькулятора залишається без змін)
    PRICE_TICKERS = {
        "XAUUSD": "GC=F", "XAGUSD": "SI=F", "XCUUSD": "HG=F",
        "EURUSD": "EURUSD=X", "US100": "NQ=F", "GER40": "YM=F",
        "DXY": "DX-Y.NYB", "JP225": "NK=F"
    }

    st.sidebar.header("🛡 Ризик-менеджмент")
    three_losses = st.sidebar.toggle("3 поспіль SL (Ризик 0.5%)")
    
    col1, col2 = st.columns(2)
    with col1:
        balance = st.number_input("Баланс ($)", value=100000.0, step=1000.0, format="%.2f")
        risk_pct = 0.5 if three_losses else 1.0
        st.info(f"Ризик: **{risk_pct}%**")
        
    with col2:
        asset = st.selectbox("Актив", list(FTMO_SPECS.keys()), key="calc_asset")
        sl_points = st.number_input("Stop Loss (points)", value=100.0, step=1.0, format="%.1f")

    current_price = get_price_safe(PRICE_TICKERS.get(asset))
    if current_price:
        prec = 5 if asset == "EURUSD" else (3 if asset in ["XAGUSD", "DXY"] else 2)
        st.markdown(f"### ⚡ Поточна ціна {asset}: `{current_price:.{prec}f}`")

    spec = FTMO_SPECS[asset]
    risk_usd = balance * (risk_pct / 100)
    one_point_val = spec['val'] / spec['tick']
    
    conv_rate = 1.0
    if spec['curr'] != "USD":
        val = get_price_safe(f"{spec['curr']}USD=X")
        conv_rate = val if val else 1.0

    raw_lot = risk_usd / (sl_points * one_point_val * conv_rate)
    final_lot = max(round(raw_lot, 2), 0.01)

    st.divider()
    st.success(f"## Рекомендований лот: **{final_lot}**")

with tab2:
    st.header("📈 Macro Intelligence Hub")
    
    # 1. ТЕХНІЧНИЙ ГРАФІК
    TV_TICKERS = {
        "DXY (Index)": "CAPITALCOM:DXY",
        "XAUUSD (Gold)": "OANDA:XAUUSD",
        "JP225 (Nikkei)": "CAPITALCOM:JP225",
        "US100 (Nasdaq)": "CAPITALCOM:US100",
        "EURUSD": "OANDA:EURUSD"
    }
    selected_asset = st.selectbox("Інструмент для аналізу:", list(TV_TICKERS.keys()), key="tv_select")
    
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

    # 2. SENTINEL AI
    st.subheader("🤖 Sentinel AI: Аналіз")
    ca1, ca2 = st.columns(2)
    with ca1:
        st.info("🎯 **Сценарій XAUUSD:** Слідкуй за DXY. CPI > прогноз = Gold 📉.")
    with ca2:
        st.warning("🏮 **Сценарій JP225:** USDJPY вгору = Nikkei 🚀. Слабкість єни — твій союзник.")

    st.divider()

    # 3. SENTINEL MACRO ENGINE (Власна таблиця)
    st.subheader("📡 Sentinel Macro Stream (Auto-Filtered)")
    st.write("Автоматичний моніторинг новин по **USD, JPY, EUR, GBP**.")
    
    macro_df = get_sentinel_macro()
    
    if not macro_df.empty and "Статус" not in macro_df.columns:
        # Відображення нативної таблиці Streamlit (Dark Mode)
        st.dataframe(
            macro_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Вплив": st.column_config.TextColumn("Важливість", width="small"),
                "Час": st.column_config.TextColumn("Час (EET)", width="small")
            }
        )
    else:
        st.info("🔄 Дані оновлюються або тимчасово недоступні. Перевірте з'єднання.")

    st.caption("💡 Дані автоматично фільтруються для ваших пріоритетних активів.")