import streamlit as st
import yfinance as yf

# Твої дані з MT5
FTMO_SPECS = {
    "XAUUSD": {"contract": 100, "tick": 0.01, "val": 1.00, "curr": "USD", "comm": 2.0},
    "XAGUSD": {"contract": 5000, "tick": 0.001, "val": 5.00, "curr": "USD", "comm": 2.0},
    "EURUSD": {"contract": 100000, "tick": 0.00001, "val": 1.00, "curr": "USD", "comm": 2.5},
    "DXY":    {"contract": 100, "tick": 0.001, "val": 0.10, "curr": "USD", "comm": 0.0},
    "US100":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "USD", "comm": 0.0},
    "US500":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "USD", "comm": 0.0},
    "GER40":  {"contract": 1, "tick": 0.01, "val": 0.01, "curr": "EUR", "comm": 0.0},
    "JP225":  {"contract": 10, "tick": 0.01, "val": 0.10, "curr": "JPY", "comm": 0.0}
}

st.set_page_config(page_title="FTMO Sentinel", layout="centered")
st.title("🎛 FTMO Sentinel v2.0")

# Блок вводу даних
col1, col2 = st.columns(2)
with col1:
    balance = st.number_input("Баланс ($)", value=100000, step=1000)
    risk_pct = st.selectbox("Ризик на угоду", [1.0, 0.5, 0.25], index=1)
with col2:
    asset = st.selectbox("Актив", list(FTMO_SPECS.keys()))
    sl_points = st.number_input("Stop Loss (пункти/points)", value=100, step=10)

# Логіка розрахунку
spec = FTMO_SPECS[asset]
risk_usd = balance * (risk_pct / 100)

# Конвертація валюти, якщо актив не в USD
conv_rate = 1.0
if spec['curr'] != "USD":
    try:
        pair = f"{spec['curr']}USD=X"
        data = yf.Ticker(pair).fast_info['last_price']
        conv_rate = data
    except:
        st.warning(f"Не вдалося отримати курс {spec['curr']}/USD. Розрахунок може бути приблизним.")

# Розрахунок лота: Ризик / (SL * Вартість 1 пункту)
# Вартість 1 пункту = (Tick Value / Tick Size) * 1 пункт
# Спрощена формула для твоїх специфікацій:
one_point_val = spec['val'] / spec['tick']
lot = risk_usd / (sl_points * one_point_val * conv_rate)

# Вирахування комісії (приблизно)
final_lot = round(lot, 2)

st.divider()

# Вивід результату
st.subheader(f"Рекомендований лот: {final_lot}")
st.info(f"💰 Ризик: ${risk_usd:.2f} | Актив: {asset}")

if asset == "XAGUSD":
    st.warning("⚠️ Срібло має великий контракт (5000). Будь обережний з лотністю!")