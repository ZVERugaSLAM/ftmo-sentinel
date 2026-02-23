import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser
from datetime import datetime
# Функція з мінімальним кешем (2 секунди), щоб уникнути помилок ліміту
@st.cache_data(ttl=3600) # Оновлюємо календар раз на годину
def get_macro_calendar():
    try:
        # Використовуємо надійний RSS потік новин
        url = "https://www.dailyfx.com/feeds/economic-calendar"
        feed = feedparser.parse(url)
        entries = []
        for entry in feed.entries:
            # Фільтруємо лише твої валюти
            if any(curr in entry.title for curr in ["USD", "JPY", "EUR", "GBP"]):
                entries.append({
                    "Дата/Час": entry.published[5:16],
                    "Подія": entry.title,
                    "Деталі": entry.summary[:100] + "..."
                })
        return pd.DataFrame(entries).head(10)
    except:
        return pd.DataFrame([{"Статус": "Календар тимчасово недоступний"}])

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
    # 1. Мапінг для отримання цін
    PRICE_TICKERS = {
        "XAUUSD": "GC=F",
        "XAGUSD": "SI=F",
        "XCUUSD": "HG=F",
        "EURUSD": "EURUSD=X",
        "US100":  "NQ=F",
        "GER40":  "YM=F",
        "DXY":    "DX-Y.NYB",
        "JP225":  "NK=F"
    }

    st.sidebar.header("🛡 Ризик-менеджмент")
    three_losses = st.sidebar.toggle("3 поспіль SL (Ризик 0.5%)")
    
    col1, col2 = st.columns(2)
    with col1:
        balance = st.number_input("Баланс рахунку ($)", value=100000.0, step=1000.0, format="%.2f")
        risk_pct = 0.5 if three_losses else 1.0
        st.info(f"Поточний ризик: **{risk_pct}%**")
        
    with col2:
        asset = st.selectbox("Актив для торгівлі", list(FTMO_SPECS.keys()), key="calc_asset")
        # Дозволяємо дробові значення для SL (float)
        sl_points = st.number_input("Stop Loss (points)", value=100.0, step=1.0, format="%.1f")

    # 2. Отримання ціни з динамічною точністю
    try:
        ticker_symbol = PRICE_TICKERS.get(asset, "GC=F")
        current_price = yf.Ticker(ticker_symbol).fast_info['last_price']
        
        # Визначаємо точність виводу залежно від активу
        precision = 5 if asset == "EURUSD" else (3 if asset in ["XAGUSD", "DXY"] else 2)
        price_str = f"{current_price:.{precision}f}"
        
        st.markdown(f"### ⚡ Поточна ціна {asset}: `{price_str}`")
    except:
        st.markdown(f"### ⚡ Поточна ціна {asset}: `Data Error`")

    # 3. Розрахунок лота
    spec = FTMO_SPECS[asset]
    risk_usd = balance * (risk_pct / 100)
    one_point_val = spec['val'] / spec['tick']
    
    conv_rate = 1.0
    if spec['curr'] != "USD":
        try:
            pair = f"{spec['curr']}USD=X"
            conv_rate = yf.Ticker(pair).fast_info['last_price']
        except:
            conv_rate = 1.0

    raw_lot = risk_usd / (sl_points * one_point_val * conv_rate)
    final_lot = max(round(raw_lot, 2), 0.01)

    st.divider()
    # Результат лотності залишаємо 2 знаки (як у терміналі для вводу)
    st.success(f"## Рекомендований лот: **{final_lot}**")
    
    col_a, col_b = st.columns(2)
    col_a.metric("Ризик у валюті", f"${risk_usd:,.2f}")
    col_b.metric("Вартість пункту (1.00 лот)", f"${one_point_val * conv_rate:.4f}")

with tab2:
    st.header("📈 Технічний аналіз та Макро")
    
    # Оновлений словник тікерів (використовуємо джерела, доступні для віджетів)
    TV_TICKERS = {
        "DXY (Index)": "CAPITALCOM:DXY", # Змінено для обходу блокування
        "XAUUSD (Gold)": "OANDA:XAUUSD",
        "XAGUSD (Silver)": "OANDA:XAGUSD",
        "XCUUSD (Copper)": "CAPITALCOM:COPPER",
        "EURUSD": "OANDA:EURUSD",
        "US100 (Nasdaq)": "CAPITALCOM:US100",
        "GER40 (Dax)": "CAPITALCOM:DE40",
        "JP225 (Nikkei)": "CAPITALCOM:JP225"
    }
    
    selected_name = st.selectbox("Оберіть інструмент:", list(TV_TICKERS.keys()), key="macro_asset_selector")
    tv_symbol = TV_TICKERS[selected_name]
    
    # Віджет з фіксом для символів
    tradingview_widget = f"""
    <div style="height: 600px;">
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
        "allow_symbol_change": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
    """
    st.components.v1.html(tradingview_widget, height=600)

    st.markdown("---")
    st.subheader("📅 Пріоритетні новини тижня")

    # Повертаємо структурований календар (стабільніший за RSS)
    macro_categories = {
        "🇺🇸 USD (Gold, DXY, US100)": [
            {"Час": "15:30", "Подія": "Core CPI (Інфляція)", "Вплив": "🔴 High"},
            {"Час": "21:00", "Подія": "FOMC Minutes", "Вплив": "🔴 High"}
        ],
        "🇯🇵 JPY (JP225, Nikkei)": [
            {"Час": "01:30", "Подія": "Tokyo CPI", "Вплив": "🔴 High"},
            {"Час": "05:00", "Подія": "BoJ Press Conference", "Вплив": "🔴 High"}
        ]
    }

    for cat, news in macro_categories.items():
        with st.expander(cat, expanded=True):
            st.table(pd.DataFrame(news))

    st.info("💡 **Порада по JP225:** Nikkei часто має зворотну кореляцію з єною. Якщо BoJ залишає ставку низькою, єна падає, що дає поштовх для JP225 вгору.")
    
    # Створюємо актуальну таблицю (можна редагувати ці дані вручну)
    events = [
        {"Час": "15:30", "Подія": "CPI m/m (Інфляція)", "Важливість": "🔴 High", "Валюта": "USD", "Прогноз": "0.3%", "Факт": "?"},
        {"Час": "15:30", "Подія": "Retail Sales (Роздрібні продажі)", "Важливість": "🔴 High", "Валюта": "USD", "Прогноз": "0.1%", "Факт": "?"},
        {"Час": "15:30", "Подія": "Empire State Manufacturing Index", "Важливість": "🟠 Medium", "Валюта": "USD", "Прогноз": "-4.0", "Факт": "?"},
        {"Час": "15:30", "Подія": "Philly Fed Manufacturing Index", "Важливість": "🟠 Medium", "Валюта": "USD", "Прогноз": "8.0", "Факт": "?"},
        {"Час": "15:30", "Подія": "Unemployment Claims (Заявки на безробіття)", "Важливість": "🟠 Medium", "Валюта": "USD", "Прогноз": "220K", "Факт": "?"},
        {"Час": "17:00", "Подія": "Existing Home Sales", "Важливість": "🟠 Medium", "Валюта": "USD", "Прогноз": "4.00M", "Факт": "?"},
        {"Час": "21:00", "Подія": "FOMC Meeting Minutes (Протоколи ФРС)", "Важливість": "🔴 High", "Валюта": "USD", "Прогноз": "-", "Факт": "-"},
        {"Час": "11:00", "Подія": "Final CPI y/y", "Важливість": "🔴 High", "Валюта": "EUR", "Прогноз": "2.4%", "Факт": "?"},
        {"Час": "09:00", "Подія": "Flash Manufacturing PMI", "Важливість": "🔴 High", "Валюта": "GBP", "Прогноз": "50.5", "Факт": "?"}
    ]
    
    df_events = pd.DataFrame(events)
    
    # Вивід таблиці
    st.table(df_events)
    
    st.info("📊 **Примітка:** Дані CPI та FOMC мають найвищий пріоритет для золота (XAUUSD) та індексу долара (DXY).")