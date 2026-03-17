import streamlit as st
import pandas as pd

# --- 1. CONFIG & UPDATED THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .box-card {
        background: white; border: 1px solid #e2e8f0;
        padding: 25px; border-radius: 6px; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .box-title { color: #94a3b8; font-size: 0.8em; text-transform: uppercase; margin-bottom: 10px; font-weight: 600; }
    .box-value { color: #1e293b; font-size: 1.8em; font-weight: 800; }
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        data = pd.read_csv("zoe_database.csv")
        data.columns = data.columns.str.strip()
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except:
        return pd.DataFrame({'SN':[1], 'CUSTOMER_NAME':['Test'], 'LOAN_AMOUNT':[0], 'AMOUNT_PAID':[0]})

df = load_data()

# --- 3. ERP NAVIGATION HEADER ---
st.markdown("""
    <div style="background-color: #0f172a; padding: 12px 25px; display: flex; justify-content: space-between; align-items: center; color: white; border-bottom: 2px solid #00acc1;">
        <div style="display: flex; gap: 20px; align-items: center;">
            <span style="opacity: 0.8; font-size: 0.9em;">👤 Evans Ahuura</span>
            <b style="font-size: 1.3em; letter-spacing: 0.5px;">Zoe Consults</b>
            <span style="background: #00acc1; padding: 2px 10px; border-radius: 20px; font-size: 0.8em;">Branch #1</span>
        </div>
        <div style="display: flex; gap: 20px; font-size: 0.85em; opacity: 0.9;">
            <span>⚙️ Admin</span><span>🔗 Settings</span><span>🔌 API</span><span style="color: #fbbf24;">❓ Help</span>
        </div>
    </div>
""", unsafe_allow_html=True)

menu_tabs = st.tabs(["👥 Borrowers", "⚖️ Loans", "💰 Repayments", "📑 Collateral", "📅 Calendar"])

# --- 4. DASHBOARD CONTENT ---
with menu_tabs[0]:
    st.write("") 
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="box-card"><div class="box-title">Total Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="box-card"><div class="box-title">Principal Released</div><div class="box-value">UGX {df["LOAN_AMOUNT"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="box-card"><div class="box-title">Collections</div><div class="box-value">UGX {df["AMOUNT_PAID"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c4:
            active = len(df[df['AMOUNT_PAID'] < df['LOAN_AMOUNT']])
            st.markdown(f'<div class="box-card"><div class="box-title">Active Loans</div><div class="box-value">{active}</div></div>', unsafe_allow_html=True)
