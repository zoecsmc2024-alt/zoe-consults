import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import base64
import urllib.parse

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
<style>
    /* 1. THE ULTIMATE TOP RESET */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        margin-top: 0rem !important;
    }

    /* 2. REMOVE THE HEADER GAP */
    header {
        visibility: hidden;
        height: 0% !important;
    }

    /* 3. THE MAIN VIEWPORT */
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
    }

    /* 4. FIX TITLE POSITION */
    .main-title {
        color: #0f172a !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        margin-top: -20px !important;
        margin-bottom: 20px !important;
        letter-spacing: -1px;
    }
</style>
""", unsafe_allow_html=True)
# --- 2. PERMANENT DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Fetching both tables from Google Sheets
    borrowers = conn.read(worksheet="Borrowers", ttl="0")
    payments = conn.read(worksheet="Payments", ttl="0")
    return borrowers.dropna(how="all"), payments.dropna(how="all")

df, pay_df = get_data()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown('<div style="margin-top: -30px;"></div>', unsafe_allow_html=True)
    
    # Logo Logic
    if 'custom_logo_b64' in st.session_state and st.session_state['custom_logo_b64']:
        st.markdown(f'<img src="data:image/png;base64,{st.session_state["custom_logo_b64"]}">', unsafe_allow_html=True)
    else:
        st.markdown('<div style="width:80px;height:80px;border-radius:50%;background-color:#1e293b;border:2px solid #00a8b5;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:30px;">💰</div>', unsafe_allow_html=True)
    
    st.markdown(f'<p class="admin-text"><b>Admin:</b> Evans Ahuura</p>', unsafe_allow_html=True)
    
    # WE USE SIMPLE NAMES HERE TO AVOID SYNTAX ERRORS
    menu_options = ["Overview", "Borrowers", "Repayments", "Calendar", "Collateral", "Ledger", "Settings"]
    page = st.radio("Menu", menu_options)
    
    st.write("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# --- 4. PAGE LOGIC (CLEAN VERSION) ---

if page == "Overview":
    st.markdown('<div class="main-title">🛡️ Zoe Consults Executive Summary</div>', unsafe_allow_html=True)
    if not df.empty:
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Principal", f"{total_p:,.0f}")
        c2.metric("Collected", f"{total_c:,.0f}")
        c3.metric("Outstanding", f"{total_p - total_c:,.0f}")
    else:
        st.info("Welcome! Add your first loan to see the dashboard.")

elif page == "Borrowers":
    st.title("👥 Active Borrowers")
    st.dataframe(df, use_container_width=True, hide_index=True)
    with st.popover("➕ New Loan"):
        with st.form("new_loan_form"):
            name = st.text_input("Name")
            amt = st.number_input("Amount", min_value=0)
            if st.form_submit_button("Save"):
                # Save logic here...
                pass

elif page == "Repayments":
    st.title("💰 Record Payment")
    if not df.empty:
        with st.form("pay_form"):
            p_name = st.selectbox("Client", df['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount", min_value=0)
            if st.form_submit_button("Submit"):
                # Payment logic here...
                pass

elif page == "Calendar":
    st.title("📅 Due Dates")
    st.write("Calendar logic goes here.")

elif page == "Collateral":
    st.title("📑 Security Assets")
    st.write("Collateral logic goes here.")

elif page == "Ledger":
    st.title("📄 Client Ledger")
    st.write("Ledger logic goes here.")

elif page == "Settings":
    st.title("⚙️ Settings")
    st.write("Settings logic goes here.")
