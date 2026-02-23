import streamlit as st
import pandas as pd
import yfinance as yf
import google.generativeai as genai
import streamlit.components.v1 as components

# Налаштування Gemini (у Streamlit Secrets)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    pass

st.set_page_config(page_title="FTMO Sentinel", layout="wide")

# --- КАЛЬКУЛЯТОР РИЗИКУ ---
st.sidebar.title("🛡 FTMO Risk")
balance = st.sidebar.number_input("Баланс ($)", value=100000)
loss_streak = st.sidebar.toggle("3+ Losses (Risk 0.5%)")
risk_pct = 0.5 if loss_streak else 1.0
risk_amount = balance * (risk_pct / 100)

st.sidebar.write(f"💵 Ризик: **${risk_amount}**")

# Параметри лотності (FTMO Standard)
# Важливо: Перевір ці значення в специфікації MT5!
point_values = {"XAUUSD": 1, "EURUSD": 10, "NAS100": 1, "AUS200": 0.7, "JPN225": 0.1}

asset = st.selectbox("Актив", list(point_values.keys()))
sl_points = st.number_input("Stop Loss (points)", value=150)
lot = risk_amount / (sl_points * point_values[asset])

st.metric("📦 ЛОТ", f"{lot:.2f}")

# --- ТАБЛИЦЯ ТА ГРАФІК ---
st.subheader("📊 Market Status")
# (Тут буде код збору даних yfinance та віджет TV, який ми обговорювали)
st.write("Графік TradingView та аналітика Gemini з'являться після деплою.")
