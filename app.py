import requests
import pandas as pd
import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="FTMO Sentinel PRO", layout="wide")

# --- ІНІЦІАЛІЗАЦІЯ AI ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Ключ GEMINI_API_KEY не знайдено в Secrets.")

def get_sentinel_analysis(asset, query):
    prompt = f"Ти — Sentinel AI, елітний фінансовий аналітик. Актив: {asset}. Запит: {query}. Стиль: лаконічний, діловий."
    
    # Використовуємо лише актуальні моделі з твого доступу
    models_to_try = ['gemini-2.5-flash', 'gemini-3-flash-preview', 'gemini-2.0-flash']
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            continue
            
    return "❌ Помилка: Жодна з моделей Gemini не відповіла. Перевірте статус сервісу."

# --- ТЕХНІЧНІ ДАНІ FTMO ---
FTMO_SPECS = {
    "XAUUSD": {"contract": 100, "tick": 0.01, "val": 1.00, "curr": "USD"},
    "XAGUSD": {"contract": 5000, "tick": 0.001, "val": 5.00, "curr": "USD"},
    "XCUUSD": {"contract": 100, "tick": 0.01, "val": 1.00, "curr": "USD"},
    "EURUSD": {"contract": 100000, "tick": 0.00001, "val": 1.00, "curr": "USD"},
    "US100":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "USD"},
    "US500":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "USD"},
    "GER40":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "EUR"},
    "AUS200": {"contract": 1, "tick": 1.0, "val": 1.00, "curr": "AUD"}, # Валідуй тік в MT5
    "DXY":    {"contract": 100, "tick": 0.001, "val": 0.10, "curr": "USD"},
    "JP225":  {"contract": 10, "tick": 1.0, "val": 10.0, "curr": "JPY"}
}

PRICE_TICKERS = {
    "XAUUSD": "GC=F", "XAGUSD": "SI=F", "XCUUSD": "HG=F",
    "EURUSD": "EURUSD=X", "US100": "NQ=F", "US500": "ES=F",
    "GER40": "^GDAXI", "AUS200": "^AXJO", "DXY": "DX-Y.NYB", "JP225": "^N225"
}

# --- ФУНКЦІЇ ОТРИМАННЯ ДАНИХ ---
@st.cache_data(ttl=5)
def get_price_safe(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        data = t.history(period="1d", interval="1m")
        if not data.empty:
            return data['Close'].iloc[-1]
        return None
    except:
        return None

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
                
                dt_obj = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
                events.append({
                    "Дата": dt_obj.strftime("%m-%d"),
                    "Час": dt_obj.strftime("%H:%M"),
                    "Валюта": item['country'],
                    "Подія": item['title'],
                    "Вплив": impact_map.get(item['impact'], "⚪"),
                    "Прогноз": item.get('forecast', '-'),
                    "Попереднє": item.get('previous', '-')
                })
        return pd.DataFrame(events)
    except:
        return pd.DataFrame()

# --- ГЛОБАЛЬНА БІЧНА ПАНЕЛЬ (Поза вкладками) ---
st.sidebar.header("🛡 Ризик-менеджмент")
three_losses = st.sidebar.toggle("3 поспіль SL (Ризик 0.5%)")
global_risk_pct = 0.5 if three_losses else 1.0

# --- ВЕРХНЯ ПАНЕЛЬ МЕТРИК ---
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

# --- ОСНОВНИЙ РОБОЧИЙ ПРОСТІР ---
tab1, tab2, tab3 = st.tabs(["🧮 Calculator", "📊 Macro Intelligence", "🚨 Crisis Watch"])

# 1. КАЛЬКУЛЯТОР (Ізольований фрагмент)
with tab1:
    @st.fragment
    def render_calculator():
        col1, col2 = st.columns(2)
        with col1:
            balance = st.number_input("Баланс ($)", value=10000.0, step=1000.0)
            st.info(f"Активний ризик: **{global_risk_pct}%**")
            
        with col2:
            asset = st.selectbox("Актив", list(FTMO_SPECS.keys()))
            
            prec = 5 if asset == "EURUSD" else (3 if asset in ["XAGUSD", "DXY"] else 2)
            step_val = float(10**(-prec))
            
            current_price = get_price_safe(PRICE_TICKERS.get(asset))
            if current_price and asset == "XCUUSD":
                current_price *= 100 # Приведення біржової ціни міді до формату FTMO
            
            # ІЗОЛЯЦІЯ СТАНУ: Фіксуємо базову ціну, щоб оновлення котирувань не збивало ручний ввід
            if "active_asset" not in st.session_state or st.session_state.active_asset != asset:
                st.session_state.active_asset = asset
                st.session_state.saved_price = float(current_price) if current_price else 0.0

            entry_price = st.number_input("Entry Price (Ціна входу)", value=st.session_state.saved_price, format=f"%.{prec}f", step=step_val)
            sl_price = st.number_input("Stop Loss (Ціна)", value=st.session_state.saved_price, format=f"%.{prec}f", step=step_val)

        if current_price:
            st.markdown(f"### ⚡ Поточна ціна {asset}: `{current_price:.{prec}f}`")

        spec = FTMO_SPECS[asset]
        abs_diff = abs(entry_price - sl_price)
        sl_points = abs_diff / spec['tick']

        risk_usd = balance * (global_risk_pct / 100)
        one_point_val = spec['val']
        
        conv_rate = 1.0
        if spec['curr'] != "USD":
            val_conv = get_price_safe(f"{spec['curr']}USD=X")
            conv_rate = val_conv if val_conv else 1.0

        if sl_points > 0:
            raw_lot = risk_usd / (sl_points * one_point_val * conv_rate)
            final_lot = max(round(raw_lot, 2), 0.01)
        else:
            final_lot = 0.0

        st.divider()
        st.success(f"## Рекомендований лот: **{final_lot}**")
        st.caption(f"Дистанція: **{sl_points:.1f} пунктів** | Допустимий збиток: **${risk_usd:.2f}**")
        
    render_calculator()

# 2. МАКРО АНАЛІТИКА ТА ШІ (Ізольовані фрагменти)
with tab2:
    st.header("📈 Macro Intelligence Hub")
    
    @st.fragment
    def render_tv():
        # Точні джерела котирувань згідно з MT5
        TV_TICKERS = {
            "XAUUSD (Gold)": "OANDA:XAUUSD",
            "XAGUSD (Silver)": "FXOPEN:XAGUSD",
            "XCUUSD (Copper)": "ACTIVTRADES:COPPERH2026",
            "EURUSD": "TICKMILL:EURUSD",
            "US100 (Nasdaq)": "CFI:US100",
            "US500 (S&P 500)": "CAPITALCOM:US500", 
            "GER40 (DAX)": "FPMARKETS:GER40",
            "AUS200": "TVC:AUS200",               
            "DXY (US Dollar)": "TVC:DXY",
            "JP225 (Nikkei)": "ICMARKETS:JP225"
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
    
    render_tv()
    st.divider()

    @st.fragment
    def render_ai_chat():
        st.subheader("🤖 Sentinel Quick Analysis")
        query_col, asset_col = st.columns([2, 1])
        
        with asset_col:
            analyze_target = st.text_input("Введіть актив (напр. BTC, OIL):", value="XAUUSD", key="asset_input")
        with query_col:
            user_query = st.text_input("Позачергове питання до ШІ:", key="query_input")
        
        if user_query:
            with st.spinner('Аналіз ринкових даних...'):
                answer = get_sentinel_analysis(analyze_target, user_query)
                st.chat_message("assistant").write(answer)

    render_ai_chat()
    st.divider()

    @st.fragment
    def render_news():
        macro_df = get_sentinel_macro_stable()
        if not macro_df.empty:
            st.dataframe(macro_df, use_container_width=True, hide_index=True)
        else:
            st.error("🔌 Помилка зв'язку з сервером новин.")
            
    render_news()

import streamlit as st
import pandas as pd
import google.generativeai as genai
import logging

with tab3:
    @st.fragment
    def render_crisis():
        st.header("🚨 Crisis Watch & Liquidity (Big Five)")
        
        row1_1, row1_2, row1_3 = st.columns(3)
        with row1_1: 
            st.metric("10Y-2Y Yield Spread", "+0.60%", delta="Un-inversion", delta_color="inverse", 
                      help="Різниця дохідності 10-річних та 2-річних держоблігацій США. Перехід від інверсії (від'ємних значень) до нормальної кривої часто безпосередньо передує початку рецесії.")
        with row1_2: 
            st.metric("US Reverse Repo (RRP)", "$0.5B", delta="Critical Drain", delta_color="inverse", 
                      help="Об'єм надлишкової ліквідності банків, припаркованої у ФРС. Наближення до нуля сигналізує про ризик гострого дефіциту готівки у фінансовій системі.")
        with row1_3: 
            st.metric("US High Yield Spread", "2.86%", delta="Low Risk", delta_color="normal", 
                      help="Премія за ризик по корпоративних облігаціях з низьким рейтингом (junk bonds). Різке зростання означає паніку кредиторів та відтік капіталу в захисні активи.")

        row2_1, row2_2, row2_3 = st.columns(3)
        with row2_1: 
            st.metric("Sahm Rule Indicator", "0.30%", delta="Rising", delta_color="inverse", 
                      help="Макроекономічний індикатор початку рецесії. Спрацьовує, коли середнє безробіття за 3 місяці перевищує мінімум за останні 12 місяців на 0.50%.")
        with row2_2: 
            st.metric("Job Search 'Find a Job'", "+12%", delta="High Risk", delta_color="inverse", 
                      help="Динаміка пошукових запитів про пошук роботи. Надійний випереджаючий індикатор слабкості ринку праці та падіння споживчого попиту.")
        with row2_3: 
            st.metric("VIX (Fear Index)", "21.60", delta="Elevated", delta_color="inverse", 
                      help="Індекс очікуваної волатильності S&P 500 (індекс страху). Значення вище 20 вказують на підвищену нервозність ринку, вище 30 — на паніку.")

        st.divider()
        
        st.subheader("⚠️ Карта системних аномалій")
        anomaly_df = pd.DataFrame([
            {"Індикатор": "10Y-2Y Spread", "Рівень": "+0.60%", "Статус": "🔴 Де-інверсія", "Наслідок": "Сигнал рецесії"},
            {"Індикатор": "Reverse Repo", "Рівень": "$0.5B", "Статус": "⚠️ Виснажено", "Наслідок": "Ризик дефіциту ліквідності"},
            {"Індикатор": "High Yield Spread", "Рівень": "2.86%", "Статус": "🟢 Стабільно", "Наслідок": "Відсутність паніки"},
            {"Індикатор": "Sahm Rule", "Рівень": "0.30%", "Статус": "🟠 Увага", "Наслідок": "Слабкість ринку праці"},
            {"Індикатор": "Job Search Trends", "Рівень": "+12%", "Статус": "🔴 Аномалія", "Наслідок": "Споживчий песимізм"}
        ])
        st.dataframe(anomaly_df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🧠 Sentinel Macro Assessment")
        
        if st.button("Згенерувати актуальний звіт 'Великої п'ятірки'", type="primary"):
            with st.spinner("Синтез даних системного ризику..."):
                
                # Ініціалізація моделі
                crisis_generation_config = {
                    "temperature": 0.1, 
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
                
                try:
                    crisis_model = genai.GenerativeModel(
                        model_name="gemini-3-pro-preview",
                        generation_config=crisis_generation_config
                    )
                    
                    report_prompt = """
                    Сформуй жорсткий макроекономічний звіт про системний ризик на основі 5 індикаторів:
                    1) Де-інверсія кривої дохідності (+0.60%). 
                    2) Виснаження Reverse Repo ($0.5B).
                    3) High Yield Spread (2.86%). 
                    4) Sahm Rule (0.30%). 
                    5) Job Search (+12%).
                    
                    Вимоги до звіту:
                    1. Оціни ризик нестачі доларової ліквідності в системі.
                    2. Зроби чіткий аргументований висновок щодо потенційного напрямку руху DXY та XAUUSD.
                    3. Обов'язково виведи аналіз 5 індикаторів виключно у форматі Markdown-таблиці з колонками: Індикатор, Фактичне значення, Оцінка системного ризику.
                    4. Формат: лаконічний, діловий. Жодних загальних фраз.
                    """
                    
                    # Прямий виклик налаштованої моделі замість старої функції
                    response = crisis_model.generate_content(report_prompt)
                    st.markdown(response.text)
                    
                except Exception as e:
                    logging.error(f"Помилка генерації звіту Crisis Watch: {str(e)}")
                    st.warning("Сервіс макроаналізу тимчасово недоступний. Деталі помилки записано в лог.")
                    
    render_crisis()