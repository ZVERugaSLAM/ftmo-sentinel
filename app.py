import streamlit as st
import yfinance as yf

# 1. СПЕЦИФІКАЦІЇ (З твоїх скріншотів)
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

st.set_page_config(page_title="FTMO Sentinel", layout="centered")
st.title("🎛 FTMO Sentinel v2.1")

# 2. БОКОВА ПАНЕЛЬ (Ризик-менеджмент за твоїми правилами)
st.sidebar.header("🛡 Ризик-менеджмент")
three_losses = st.sidebar.toggle("3 поспіль збитки")
manual_risk = st.sidebar.number_input("Або введи ризик в $ вручну", value=0.0)

# 3. ОСНОВНЕ ВІКНО ВВОДУ
col1, col2 = st.columns(2)
with col1:
    balance = st.number_input("Баланс рахунку ($)", value=100000, step=1000)
    risk_pct = st.selectbox("Ризик %", [1.0, 0.5, 0.25], index=0)
with col2:
    asset = st.selectbox("Актив для торгівлі", list(FTMO_SPECS.keys()))
    sl_points = st.number_input("Stop Loss (пункти/points)", value=100, step=10)

# 4. ЛОГІКА РОЗРАХУНКУ
spec = FTMO_SPECS[asset]

# Визначення суми ризику
if manual_risk > 0:
    risk_usd = manual_risk
elif three_losses:
    risk_usd = balance * 0.005 # Твоє правило: 0.5% після 3 лосів
    st.sidebar.warning("Застосовано ризик 0.5%")
else:
    risk_usd = balance * (risk_pct / 100)

# Конвертація валюти (для GER40, JP225 тощо)
conv_rate = 1.0
if spec['curr'] != "USD":
    try:
        pair = f"{spec['curr']}USD=X"
        conv_rate = yf.Ticker(pair).fast_info['last_price']
    except:
        st.error("Помилка оновлення курсу валют.")

# ФОРМУЛА: Лот = Ризик / (SL_в_пунктах * Вартість_1_пункту)
one_point_val = spec['val'] / spec['tick']
raw_lot = risk_usd / (sl_points * one_point_val * conv_rate)
final_lot = max(round(raw_lot, 2), 0.01)

# 5. ВИВІД РЕЗУЛЬТАТІВ (Те, що ми додаємо)
st.divider()

# Головне вікно з об'ємом
st.success(f"## Рекомендований лот: **{final_lot}**")

# Деталізація
c1, c2, c3 = st.columns(3)
c1.metric("Ризик $", f"${risk_usd:,.2f}")
c2.metric("SL Пункти", f"{sl_points}")
c3.metric("Валюта активу", spec['curr'])

if asset == "XAGUSD":
    st.warning("⚠️ Срібло: Контракт 5000! Перевір лотність ще раз.")