import requests
import pandas as pd
import streamlit as st
import yfinance as yf
import google.generativeai as genai  # Додано
from datetime import datetime

# --- ІНІЦІАЛІЗАЦІЯ AI ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.warning("⚠️ Ключ GEMINI_API_KEY не знайдено в Secrets.")

def get_sentinel_analysis(asset, query):
    prompt = f"""
    Ти — Sentinel AI, елітний фінансовий аналітик.
    Актив: {asset}. Запит: {query}.
    Стиль: лаконічний, професійний, без води. 
    """
    
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    error_logs = []
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Фіксуємо точну помилку API для поточної моделі
            error_logs.append(f"[{model_name}]: {str(e)}")
            continue
            
    # Формуємо детальний звіт про помилки, якщо жодна модель не спрацювала
    detailed_error = "❌ **Критична помилка API Google:**\n\n"
    for err in error_logs:
        detailed_error += f"- {err}\n"
        
    return detailed_error

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

tab1, tab2, tab3 = st.tabs(["🧮 Calculator", "📊 Macro Intelligence", "🚨 Crisis Watch"])

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

    # 1. Ізолюємо віджет TradingView
    @st.fragment
    def render_tradingview():
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

    render_tradingview()

    st.divider()
    st.subheader("🤖 Sentinel AI: Аналіз")
    ca1, ca2 = st.columns(2)
    with ca1:
        st.info("🎯 **Сценарій XAUUSD:** Слідкуй за DXY. CPI > прогноз = Gold 📉.")
    with ca2:
        st.warning("🏮 **Сценарій JP225:** USDJPY вгору = Nikkei 🚀. Слабкість єни — союзник.")

    st.divider()
    st.subheader("🤖 Sentinel Quick Analysis")
    
    # 2. Ізолюємо логіку запитів до AI
    @st.fragment
    def render_ai_chat():
        query_col, asset_col = st.columns([2, 1])
        
        with asset_col:
            analyze_target = st.text_input("Введіть актив (напр. BTC, OIL):", value="XAUUSD", key="asset_input")
        with query_col:
            user_query = st.text_input("Позачергове питання до ШІ:", key="query_input")
        
        if user_query:
            with st.spinner('Sentinel аналізує ринкові дані та макро-фон...'):
                answer = get_sentinel_analysis(analyze_target, user_query)
                st.chat_message("assistant").write(answer)

    render_ai_chat()
    
    # 3. Ізолюємо таблицю новин
    @st.fragment
    def render_macro_news():
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

    render_macro_news()

with tab3:
    st.header("🚨 Crisis Watch & Liquidity (Big Five)")
    st.write("Моніторинг макроекономічних індикаторів системного ризику та кризової ліквідності.")
    
    # ПЕРШИЙ РЯДОК (Підказки перенесено всередину метрик - шуму більше не буде)
    row1_1, row1_2, row1_3 = st.columns(3)
    
    with row1_1:
        st.metric("10Y-2Y Yield Spread", "+0.60%", delta="Un-inversion", delta_color="inverse", 
                  help="Різниця дохідності 10- та 2-річних облігацій США. Де-інверсія історично збігається з початком рецесії.")
        
    with row1_2:
        st.metric("US Reverse Repo (RRP)", "$0.5B", delta="Critical Drain", delta_color="inverse", 
                  help="Об'єм надлишкової ліквідності банків у ФРС. Падіння до нуля означає виснаження 'подушки безпеки'.")
        
    with row1_3:
        st.metric("US High Yield Spread", "2.86%", delta="Low Risk", delta_color="normal", 
                  help="Спред 'сміттєвих' облігацій. Ріст вище 5.00% означає паніку на кредитному ринку.")

    # ДРУГИЙ РЯДОК
    row2_1, row2_2, row2_3 = st.columns(3)
    
    with row2_1:
        st.metric("Sahm Rule Indicator", "0.30%", delta="Rising", delta_color="inverse", 
                  help="Індикатор рецесії. Досягнення 0.50% означає фактичний вхід економіки США в рецесію.")
        
    with row2_2:
        st.metric("Job Search 'Find a Job'", "+12%", delta="High Risk", delta_color="inverse", 
                  help="Google Trends. Випереджальний соціальний індикатор безробіття перед звітами NFP.")

    with row2_3:
        st.metric("VIX (Fear Index)", "21.60", delta="Elevated", delta_color="inverse", 
                  help="Індекс очікуваної волатильності S&P 500. Значення > 20 вказують на хеджування великим капіталом.")

    st.divider()

    # ПОВЕРНУТА ТАБЛИЦЯ
    st.subheader("⚠️ Карта системних аномалій")
    crisis_data = [
        {"Індикатор": "10Y-2Y Spread", "Рівень": "+0.60%", "Статус": "🔴 Де-інверсія", "Наслідок": "Сигнал рецесії"},
        {"Індикатор": "Reverse Repo", "Рівень": "$0.5B", "Статус": "⚠️ Виснажено", "Наслідок": "Ризик дефіциту ліквідності"},
        {"Індикатор": "High Yield Spread", "Рівень": "2.86%", "Статус": "🟢 Стабільно", "Наслідок": "Відсутність паніки"},
        {"Індикатор": "Sahm Rule", "Рівень": "0.30%", "Статус": "🟠 Увага", "Наслідок": "Слабкість ринку праці"},
        {"Індикатор": "Job Search Trends", "Рівень": "+12%", "Статус": "🔴 Аномалія", "Наслідок": "Споживчий песимізм"}
    ]
    st.table(pd.DataFrame(crisis_data))

    # AI ЗВІТ
    st.subheader("🧠 Sentinel Macro Assessment")
    if st.button("Згенерувати актуальний звіт 'Великої п'ятірки'"):
        with st.spinner("Аналіз кривої дохідності, RRP, HY Spread та ринку праці..."):
            report_prompt = """
            Проаналізуй фазу світового ринку на основі 5 індикаторів:
            1) Де-інверсія кривої дохідності (+0.60%).
            2) Повне виснаження Reverse Repo ($0.5B).
            3) High Yield Spread на рівні 2.86%.
            4) Sahm Rule наближається до рецесійного порогу (0.30%).
            5) Ріст пошуку роботи (+12%).
            Зроби жорсткий висновок щодо ризику обвалу та впливу на DXY і XAUUSD.
            """
            report = get_sentinel_analysis("Global Liquidity", report_prompt)
            st.markdown(report)

