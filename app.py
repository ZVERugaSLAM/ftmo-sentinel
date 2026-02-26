import logging
import requests
import pandas as pd
import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="FTMO Sentinel PRO", layout="wide")

# Ін'єкція кастомного CSS для стилізації інтерфейсу
st.markdown("""
    <style>
    /* Приховування стандартного меню та футера Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* Оптимізація робочого простору (зменшення відступів) */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
        max-width: 95%;
    }

    /* Стилізація блоків цифрових метрик */
    [data-testid="stMetric"] {
        background-color: #1c1f26;
        border: 1px solid #2d3139;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Розмір основного шрифту всередині метрик */
    [data-testid="stMetricValue"] {
        font-size: 26px;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- ІНІЦІАЛІЗАЦІЯ AI ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ Ключ GEMINI_API_KEY не знайдено в Secrets.")

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

# --- ГЛОБАЛЬНА БІЧНА ПАНЕЛЬ (Intelligence & Control Center) ---
with st.sidebar:
    st.markdown("### 🕒 Час терміналу (Kyiv/EET)")
    
    # Живий годинник на JavaScript
    st.components.v1.html("""
        <div style="background: #1c1f26; padding: 10px; border-radius: 8px; border: 1px solid #2d3139; text-align: center;">
            <div id="clock" style="font-size: 1.8rem; font-weight: 700; color: #00bfa5; font-family: 'Courier New', monospace;">00:00:00</div>
            <div style="color: #848e9c; font-size: 0.7rem; margin-top: 5px;">GMT+2 (Зимовий час)</div>
        </div>
        <script>
            function updateClock() {
                const now = new Date();
                const options = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
                document.getElementById('clock').innerText = now.toLocaleTimeString('uk-UA', options);
            }
            setInterval(updateClock, 1000);
            updateClock();
        </script>
    """, height=100)

    st.divider()
    
    # Макро-віджет "Сьогодні"
    st.subheader("📅 Макро сьогодні")
    calendar_mini = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {
      "colorTheme": "dark",
      "isTransparent": true,
      "width": "100%",
      "height": "350",
      "locale": "uk",
      "importanceFilter": "0,1",
      "currencyFilter": "USD,EUR,GBP"
      }
      </script>
    </div>
    """
    st.components.v1.html(calendar_mini, height=350)
    
    if st.button("Весь календар →", use_container_width=True):
        st.info("Використовуйте вкладку 'Macro Intelligence'")

# --- ВЕРХНЯ ПАНЕЛЬ МЕТРИК ---
st.title("🛰 FTMO Sentinel: Intelligence & Risk")
cols = st.columns(4)
with cols[0]:
    val = get_price_safe("DX=F")
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
tab1, tab2, tab3, tab4 = st.tabs(["🧮 Calculator", "📊 Macro Intelligence", "🚨 Crisis Watch", "📓 Trade Journal"])

# 1. КАЛЬКУЛЯТОР (Ізольований фрагмент з редизайном 2x2)
with tab1:
    @st.fragment
    def render_calculator():
        row1_col1, row1_col2 = st.columns(2, gap="medium")
        
        with row1_col1:
            balance = st.number_input("Баланс ($)", value=10000.0, step=1000.0)
            
            # ІНТЕГРОВАНИЙ РИЗИК-МЕНЕДЖМЕНТ
            risk_container = st.container()
            with risk_container:
                three_losses = st.toggle("3 поспіль SL (Знизити ризик до 0.5%)", key="calc_risk_toggle")
                global_risk_pct = 0.5 if three_losses else 1.0
                
                # Динамічна зміна кольору блоку залежно від ризику
                if three_losses:
                    st.warning(f"⚠️ Захисний режим: **{global_risk_pct}%**")
                else:
                    st.info(f"Активний ризик: **{global_risk_pct}%**")
            
        with row1_col2:
            asset = st.selectbox("Символ / Інструмент", list(FTMO_SPECS.keys()))
            
            # Логіка точності (залишається без змін)
            prec = 5 if asset == "EURUSD" else (3 if asset in ["XAGUSD", "DXY"] else 2)
            step_val = float(10**(-prec))
            
            current_price = get_price_safe(PRICE_TICKERS.get(asset))
            if current_price and asset == "XCUUSD":
                current_price *= 100 
            
            if "active_asset" not in st.session_state or st.session_state.active_asset != asset:
                st.session_state.active_asset = asset
                st.session_state.saved_price = float(current_price) if current_price else 0.0

        row2_col1, row2_col2 = st.columns(2, gap="medium")
        with row2_col1:
            entry_price = st.number_input("Entry Price (Ціна входу)", value=st.session_state.saved_price, format=f"%.{prec}f", step=step_val)
        with row2_col2:
            sl_price = st.number_input("Stop Loss (Ціна виходу)", value=st.session_state.saved_price, format=f"%.{prec}f", step=step_val)

        # Розрахункова частина
        if current_price:
            st.markdown(f"#### ⚡ Поточна ціна {asset}: `{current_price:.{prec}f}`")

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

        # Вивід результату (Візуальний акцент)
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
                    "autosize": true,
                    "symbol": "{TV_TICKERS[selected_asset]}",
                    "interval": "15",
                    "timezone": "Europe/Kyiv",
                    "theme": "dark",
                    "style": "1",
                    "locale": "uk",
                    "enable_publishing": false,
                    "hide_top_toolbar": false,
                    "hide_side_toolbar": false,
                    "allow_symbol_change": true,
                    "save_image": false,
                    "container_id": "tradingview_chart"
                }});
            </script>
        </div>
        """
        st.components.v1.html(tv_widget, height=500)
    
    render_tv()
    st.divider()

    @st.cache_data(ttl=1800)
    def fetch_price_action(ticker_symbol):
        try:
            # Мапінг торгових інструментів MT5 на тікери Yahoo Finance (використовуємо ф'ючерси для металів)
            yf_map = {
                "XAUUSD": "GC=F",      # Ф'ючерс на золото (GC)
                "XAGUSD": "SI=F",      # Ф'ючерс на срібло (SI)
                "XCUUSD": "HG=F",      # Ф'ючерс на мідь (HG)
                "EURUSD": "EURUSD=X",  # Спот EUR/USD
                "US100": "NQ=F",       # Ф'ючерс Nasdaq 100
                "GER40": "^GDAXI",     # Індекс DAX
                "DXY": "DX-Y.NYB",     # Індекс Долара
                "JP225": "^N225"       # Індекс Nikkei 225
            }
            actual_ticker = yf_map.get(ticker_symbol.upper(), ticker_symbol.upper())
            
            # Отримання свічкових даних за 14 днів
            stock = yf.Ticker(actual_ticker)
            df = stock.history(period="14d")
            
            if df.empty:
                return "Дані відсутні. Перевірте правильність тікера."
            
            # Форматування для промпту
            df = df[['Open', 'High', 'Low', 'Close']].round(2)
            df.index = df.index.strftime('%Y-%m-%d')
            return df.to_string()
        except Exception as e:
            logging.error(f"Помилка yfinance: {e}")
            return "Помилка завантаження котирувань."

    @st.fragment
    def render_ai_chat():
        st.subheader("🤖 Sentinel Price Action (14D)")
        query_col, asset_col = st.columns([2, 1])
        
        with asset_col:
            analyze_target = st.selectbox(
                "Актив:", 
                ["XAUUSD", "XAGUSD", "XCUUSD", "EURUSD", "US100", "GER40", "DXY", "JP225"], 
                index=0, 
                key="asset_input"
            )
        with query_col:
            user_query = st.text_input("Специфічний запит (залиш порожнім для загального звіту):", key="query_input")
        
        if st.button("Провести аналіз Price Action", type="primary"):
            with st.spinner(f'Завантаження даних {analyze_target} та генерація звіту...'):
                ohlcv_text = fetch_price_action(analyze_target)
                
                pa_prompt = f"""
                Виконай детальний технічний аналіз Price Action для активу {analyze_target} за останні 14 торгових днів.
                
                Дані OHLCV (Open, High, Low, Close):
                {ohlcv_text}
                
                Обов'язкова структура звіту (розкрий кожен пункт розгорнуто, спираючись виключно на конкретні цифри з таблиці):
                1. Домінуючий тренд: Опиши поточну структуру ринку (висхідна, низхідна, консолідація). Вкажи дати, де відбувся злам структури або підтвердження тренду.
                2. Ключові рівні (POI / S&R): Визнач точні цінові зони підтримки та опору. Аргументуй їх формування конкретними максимумами (High) та мінімумами (Low) з наданих даних.
                3. Ліквідність та патерни: Вкажи дні, де відбулося зняття ліквідності (пробій попередніх екстремумів з наступним поверненням ціни) або сформувалися явні розворотні формації.
                """
                
                if user_query:
                    pa_prompt += f"\n\nСпецифічний запит трейдера: {user_query}\nІнтегруй детальну відповідь на цей запит у свій аналіз."
                
                pa_prompt += "\n\nФормат: Діловий, жорсткий, аналітичний. Заборонено використовувати загальні фрази. Використовуй марковані списки та жирний шрифт для виділення дат і цінових рівнів."
                
                try:
                    pa_model = genai.GenerativeModel(
                        model_name="gemini-2.5-flash",
                        generation_config={
                            "temperature": 0.1, 
                            "max_output_tokens": 8192
                        }
                    )
                    
                    # Відключення фільтрів безпеки для уникнення обривів при генерації фінансового аналізу
                    safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ]
                    
                    response = pa_model.generate_content(pa_prompt, safety_settings=safety_settings)
                    
                    if response.text:
                        st.markdown(response.text)
                    else:
                        st.warning("Отримано порожню відповідь від моделі.")
                        
                except Exception as e:
                    st.error(f"Помилка генерації звіту: {str(e)}")
                    
    render_ai_chat()
    st.divider()

    @st.fragment
    def render_news():
        st.subheader("📅 Макроекономічний Календар (Live)")
        
        calendar_widget = """
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
          {
          "colorTheme": "dark",
          "isTransparent": true,
          "width": "100%",
          "height": "500",
          "locale": "uk",
          "importanceFilter": "0,1",
          "currencyFilter": "USD,EUR,GBP,JPY"
        }
          </script>
        </div>
        """
        st.components.v1.html(calendar_widget, height=500)
            
    render_news()


with tab3:
    # Оновлена функція парсингу 4 індикаторів з FRED
    @st.cache_data(ttl=3600)
    def fetch_fred_macro():
        try:
            urls = {
                'spread': ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y", 'T10Y2Y'),
                'rrp': ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=RRPONTSYD", 'RRPONTSYD'),
                'hy': ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2", 'BAMLH0A0HYM2'),
                'sahm': ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=SAHMREALTIME", 'SAHMREALTIME'),
                'vix': ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS", 'VIXCLS')
            }
            
            results = {}
            for key, (url, col) in urls.items():
                df = pd.read_csv(url, index_col='DATE', parse_dates=True, na_values='.')
                results[key] = float(df[col].dropna().iloc[-1])
                
            return results['spread'], results['rrp'], results['hy'], results['sahm'], results['vix']
        except Exception as e:
            logging.error(f"Помилка підключення до FRED: {e}")
            return None, None, None, None, None

    @st.fragment
    def render_crisis():
        st.header("🚨 Crisis Watch & Liquidity (Big Five)")
        
        # Отримання даних
        spread_val, rrp_val, hy_val, sahm_val, vix_val = fetch_fred_macro()
        
        # Запобіжники на випадок збою API
        actual_spread = spread_val if spread_val is not None else 0.60
        actual_rrp = rrp_val if rrp_val is not None else 500.0
        actual_hy = hy_val if hy_val is not None else 2.86
        actual_sahm = sahm_val if sahm_val is not None else 0.30
        actual_vix = vix_val if vix_val is not None else 21.60
        
        # Форматування
        spread_str = f"{actual_spread:+.2f}%"
        rrp_str = f"${actual_rrp:.2f}B"
        hy_str = f"{actual_hy:.2f}%"
        sahm_str = f"{actual_sahm:.2f}%"
        vix_str = f"{actual_vix:.2f}"
        
        row1_1, row1_2, row1_3 = st.columns(3)
        with row1_1: 
            st.metric("10Y-2Y Yield Spread", spread_str, delta="FRED Live", delta_color="off", 
                      help="Різниця дохідності 10-річних та 2-річних держоблігацій США. Перехід від інверсії (від'ємних значень) до нормальної кривої часто безпосередньо передує початку рецесії.")
        with row1_2: 
            st.metric("US Reverse Repo (RRP)", rrp_str, delta="FRED Live", delta_color="off", 
                      help="Об'єм надлишкової ліквідності банків, припаркованої у ФРС. Наближення до нуля сигналізує про ризик гострого дефіциту готівки у фінансовій системі.")
        with row1_3: 
            st.metric("US High Yield Spread", hy_str, delta="FRED Live", delta_color="off", 
                      help="Премія за ризик по корпоративних облігаціях з низьким рейтингом (junk bonds). Різке зростання означає паніку кредиторів та відтік капіталу в захисні активи.")

        row2_1, row2_2, row2_3 = st.columns(3)
        with row2_1: 
            st.metric("Sahm Rule Indicator", sahm_str, delta="FRED Live", delta_color="off", 
                      help="Макроекономічний індикатор початку рецесії. Спрацьовує, коли середнє безробіття за 3 місяці перевищує мінімум за останні 12 місяців на 0.50%.")
        with row2_2: 
            st.metric("Job Search 'Find a Job'", "+12%", delta="Static", delta_color="off", 
                      help="Динаміка пошукових запитів про пошук роботи. Залишено статичним через блокування хмарних серверів з боку Google Trends.")
        with row2_3: 
            st.metric("VIX (Fear Index)", vix_str, delta="FRED Live", delta_color="off", 
                      help="Індекс очікуваної волатильності S&P 500 (індекс страху). Значення вище 20 вказують на підвищену нервозність ринку, вище 30 — на паніку.")

        st.divider()
        
        st.subheader("⚠️ Карта системних аномалій")
        
        # Динамічна оцінка статусів на основі актуальних даних FRED
        spread_status = "🔴 Де-інверсія" if actual_spread > 0 else "🟡 Інверсія"
        spread_cons = "Сигнал початку рецесії" if actual_spread > 0 else "Накопичення системного ризику"
        
        rrp_status = "🔴 Критично" if actual_rrp < 500 else ("🟡 Виснаження" if actual_rrp < 1000 else "🟢 В нормі")
        rrp_cons = "Гострий дефіцит ліквідності" if actual_rrp < 500 else "Поступове скорочення ліквідності"
        
        hy_status = "🔴 Паніка" if actual_hy >= 5.0 else ("🟠 Увага" if actual_hy >= 4.0 else "🟢 Стабільно")
        hy_cons = "Кредитний стиск" if actual_hy >= 4.0 else "Відсутність паніки кредиторів"
        
        sahm_status = "🔴 Рецесія" if actual_sahm >= 0.50 else ("🟠 Зростання" if actual_sahm >= 0.30 else "🟢 Норма")
        sahm_cons = "Зростання безробіття" if actual_sahm >= 0.30 else "Ринок праці стабільний"
        
        anomaly_df = pd.DataFrame([
            {"Індикатор": "10Y-2Y Spread", "Рівень": spread_str, "Статус": spread_status, "Наслідок": spread_cons},
            {"Індикатор": "Reverse Repo", "Рівень": rrp_str, "Статус": rrp_status, "Наслідок": rrp_cons},
            {"Індикатор": "High Yield Spread", "Рівень": hy_str, "Статус": hy_status, "Наслідок": hy_cons},
            {"Індикатор": "Sahm Rule", "Рівень": sahm_str, "Статус": sahm_status, "Наслідок": sahm_cons},
            {"Індикатор": "Job Search Trends", "Рівень": "+12%", "Статус": "🔴 Аномалія", "Наслідок": "Споживчий песимізм"}
        ])
        st.dataframe(anomaly_df, width="stretch", hide_index=True)

        st.divider()
        st.subheader("🧠 Sentinel Macro Assessment")
        
        if st.button("Згенерувати актуальний звіт 'Великої п'ятірки'", type="primary"):
            with st.spinner("Синтез даних системного ризику..."):
                crisis_generation_config = {
                    "temperature": 0.1, 
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
                
                try:
                    crisis_model = genai.GenerativeModel(
                        model_name="gemini-2.5-flash",
                        generation_config=crisis_generation_config
                    )
                    
                    report_prompt = f"""
                    Сформуй глибокий макроекономічний аналіз системного ризику.

                    Вхідні дані (Велика п'ятірка):
                    1) Де-інверсія кривої дохідності (10Y-2Y): {spread_str}
                    2) Reverse Repo (RRP): {rrp_str}
                    3) High Yield Spread: {hy_str}
                    4) Sahm Rule: {sahm_str}
                    5) Job Search: +12%
                    
                    Вимоги до звіту:
                    1. Синтез (Не перелічуй індикатори як список): Поясни їхній взаємозв'язок. Наприклад, як фактичний рівень RRP у поєднанні зі спредом кривої впливає на міжбанківський ринок та загрожує кредитним стиском.
                    2. Ліквідність: Дай розгорнуту оцінку ризику гострого дефіциту доларової ліквідності.
                    3. Прогноз: Зроби аргументований висновок щодо напрямку руху DXY та XAUUSD з огляду на захисні властивості цих активів.
                    
                    Формат: Діловий, жорсткий та аналітичний. Використовуй жирний шрифт для виділення ключових тригерів, цифр та фінансових термінів. Структуруй висновки маркованими списками. Суворо заборонено генерувати таблиці.
                    """
                    
                    response = crisis_model.generate_content(report_prompt)
                    st.markdown(response.text)
                    
                except Exception as e:
                    logging.error(f"Помилка генерації звіту Crisis Watch: {str(e)}")
                    st.warning("Сервіс макроаналізу тимчасово недоступний. Деталі помилки записано в лог.")
                    
    render_crisis()

with tab4:
    st.header("📓 Торговий Журнал (Синхронізація MT5)")
    
    uploaded_file = st.file_uploader("Завантажте звіт історії MT5 (HTML)", type=["html", "htm"])
    
    if uploaded_file is not None:
        try:
            with st.spinner("Обробка звіту MT5..."):
                from bs4 import BeautifulSoup
                import pandas as pd
                
                raw_bytes = uploaded_file.getvalue()
                
                soup = BeautifulSoup(raw_bytes, "html.parser")
                trs = soup.find_all('tr')
                
                parsed_data = []
                capture = False
                
                for tr in trs:
                    cells = tr.find_all(['td', 'th'])
                    
                    # 1. Витягуємо текст, видаляємо невидимі символи (&nbsp;) та пробіли
                    row_text = [c.get_text().replace('\xa0', '').strip() for c in cells]
                    
                    # 2. ВБИВАЄМО ПРИХОВАНІ КОЛОНКИ-РОЗПІРКИ ВІД MT5 (фільтруємо пустоту)
                    row_text = [x for x in row_text if x != '']
                    
                    if not row_text:
                        continue
                        
                    # 3. Знаходимо заголовок таблиці Positions
                    if len(row_text) >= 13 and ('time' in row_text[0].lower() or 'час' in row_text[0].lower()) and ('position' in row_text[1].lower() or 'позиці' in row_text[1].lower() or 'позици' in row_text[1].lower()):
                        capture = True
                        continue
                        
                    if capture:
                        # Зупинка, якщо почався інший блок (Orders, Deals тощо)
                        if len(row_text) > 0 and row_text[0].lower() in ['orders', 'deals', 'open positions', 'ордери', 'угоди', 'сделки']:
                            break
                            
                        # Відбір лише закритих угод (buy / sell)
                        if len(row_text) >= 13:
                            trade_type = row_text[3].lower()
                            if trade_type in ['buy', 'sell']:
                                # Беремо рівно 13 чистих значень
                                parsed_data.append(row_text[:13])
                                
                if not parsed_data:
                    st.error("Не знайдено угод у блоці 'Positions'. Перевірте формат звіту.")
                else:
                    target_cols = ['Open Time', 'Position', 'Symbol', 'Type', 'Volume', 'Open Price', 'S/L', 'T/P', 'Close Time', 'Close Price', 'Commission', 'Swap', 'Profit']
                    df_final = pd.DataFrame(parsed_data, columns=target_cols)
                    
                    # Очищення числових значень (коми на крапки, видалення пробілів)
                    def clean_numeric(series):
                        s = series.astype(str).str.replace(r'\s+', '', regex=True).str.replace(',', '.')
                        return pd.to_numeric(s, errors='coerce').fillna(0.0)

                    num_cols = ['Volume', 'Open Price', 'S/L', 'T/P', 'Close Price', 'Commission', 'Swap', 'Profit']
                    for col in num_cols:
                        df_final[col] = clean_numeric(df_final[col])
                        
                    st.write("### 📝 Дані з таблиці Positions")
                    
                    edited_df = st.data_editor(
                        df_final, 
                        num_rows="dynamic", 
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Динамічний підрахунок
                    total_profit = edited_df['Profit'].sum()
                    color = "green" if total_profit > 0 else "red" if total_profit < 0 else "gray"
                    st.markdown(f"**Підсумок Profit:** <span style='color:{color}; font-size:18px'>**{total_profit:.2f}**</span>", unsafe_allow_html=True)
                    
                    st.divider()
                    if st.button("💾 Експортувати в Google Sheets", type="primary"):
                        with st.spinner("З'єднання з Google Sheets..."):
                            try:
                                import gspread
                                from google.oauth2.service_account import Credentials
                                
                                scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                                skey = dict(st.secrets["gcp_service_account"])
                                credentials = Credentials.from_service_account_info(skey, scopes=scopes)
                                gc = gspread.authorize(credentials)
                                
                                sheet_url = st.secrets["google_sheets"]["journal_url"]
                                sh = gc.open_by_url(sheet_url)
                                worksheet = sh.sheet1
                                
                                if len(worksheet.get_all_values()) == 0:
                                    worksheet.append_row(target_cols)
                                
                                edited_df_clean = edited_df.fillna("").astype(str)
                                data_to_append = edited_df_clean.values.tolist()
                                
                                worksheet.append_rows(data_to_append)
                                st.success(f"✅ Успішно експортовано {len(data_to_append)} рядків!")
                                
                            except Exception as e:
                                st.error(f"Помилка запису: {e}")

        except Exception as e:
            st.error(f"Критична помилка обробки: {e}")