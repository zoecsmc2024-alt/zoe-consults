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
# --- 2. PERMANENT DATA CONNECTION (FORCE-LOAD) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # We use ttl="0" to ensure it doesn't show old "cached" data
        borrowers = conn.read(worksheet="Borrowers", ttl="0")
        payments = conn.read(worksheet="Payments", ttl="0")
        
        # Clean up empty rows
        borrowers = borrowers.dropna(how="all")
        payments = payments.dropna(how="all")
        
        # Ensure numbers are actually numbers (Crucial for Charts!)
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']:
            if col in borrowers.columns:
                borrowers[col] = pd.to_numeric(borrowers[col], errors='coerce').fillna(0)
                
        return borrowers, payments
    except Exception as e:
        st.error(f"⚠️ Connection Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

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

# --- 4. PAGE LOGIC (RESTORATION) ---

if page == "Overview":
    st.markdown('<div class="main-title">🛡️ Zoe Consults Executive Summary</div>', unsafe_allow_html=True)
    
    # DEBUG: This will show you if the app sees any data at all
    if df.empty:
        st.warning("🕵️ Your 'Borrowers' sheet appears to be empty. Please add a loan in the Borrowers tab.")
    else:
        # 📊 1. CALCULATE TOTALS
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        risk = total_p - total_c
        
        # 💎 2. PREMIUM TILES
        c1, c2, c3 = st.columns(3)
        c1.metric("Principal Issued", f"UGX {total_p:,.0f}")
        c2.metric("Total Collected", f"UGX {total_c:,.0f}")
        c3.metric("Outstanding Risk", f"UGX {risk:,.0f}")
            
        st.write("---")
        
        # 📈 3. THE RECOVERY CHART (Forced Mapping)
        st.subheader("Recovery Progress by Client")
        
        # We explicitly tell the chart which columns to use
        chart_data = df[['CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID']].set_index('CUSTOMER_NAME')
        st.bar_chart(chart_data, color=["#0ea5e9", "#10b981"])

elif page == "Borrowers":
    st.title("👥 Active Loan Registry")
    # Show the main table from Google Sheets
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    with st.popover("➕ New Loan Disbursal"):
        with st.form("new_loan_cloud"):
            name = st.text_input("Client Name")
            amt = st.number_input("Principal Amount", min_value=0)
            rate = st.number_input("Interest Rate (%)", value=10.0)
            if st.form_submit_button("✅ Save to Cloud"):
                new_id = int(df['SN'].max() + 1) if not df.empty else 1
                new_row = pd.DataFrame([[new_id, name, amt, 0, amt, rate, str(datetime.now().date())]], columns=df.columns)
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Borrowers", data=updated_df)
                st.success("Saved to Google Sheets!")
                st.rerun()

elif page == "Repayments":
    st.title("💰 Record a Payment")
    if not df.empty:
        with st.form("cloud_pay_form"):
            p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount Paid", min_value=0)
            p_ref = st.text_input("Receipt / Ref No.")
            if st.form_submit_button("Submit Payment"):
                # 1. Update Payments Sheet
                new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                updated_pay = pd.concat([pay_df, new_p], ignore_index=True)
                conn.update(worksheet="Payments", data=updated_pay)
                
                # 2. Update Borrowers Balance
                df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amt
                conn.update(worksheet="Borrowers", data=df)
                st.success("Payment Synced!")
                st.rerun()
    st.write("---")
    st.subheader("Recent Payment History")
    st.dataframe(pay_df.iloc[::-1], use_container_width=True)
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
