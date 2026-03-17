import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. CONFIG & UPDATED THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .box-card {
        background: white; border: 1px solid #e2e8f0;
        padding: 20px; border-radius: 8px; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .box-title { color: #64748b; font-size: 0.85em; text-transform: uppercase; margin-bottom: 8px; font-weight: 600; }
    .box-value { color: #0f172a; font-size: 1.6em; font-weight: 800; }
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 4px 4px 0 0; padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
            'SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 
            'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED'
        ])
        df.to_csv(DB_FILE, index=False)

@st.cache_data(ttl=60) # Refresh cache every minute
def load_data():
    try:
        data = pd.read_csv(DB_FILE)
        data.columns = data.columns.str.strip()
        numeric_cols = ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE']
        for col in numeric_cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except Exception:
        return pd.DataFrame()

init_db()
df = load_data()

# --- 3. ERP NAVIGATION HEADER ---
st.markdown("""
    <div style="background-color: #0f172a; padding: 12px 25px; display: flex; justify-content: space-between; align-items: center; color: white; border-bottom: 3px solid #00acc1; margin-bottom: 20px;">
        <div style="display: flex; gap: 20px; align-items: center;">
            <span style="opacity: 0.8; font-size: 0.9em;">👤 Evans Ahuura</span>
            <b style="font-size: 1.4em; letter-spacing: 0.5px;">Zoe Consults</b>
            <span style="background: #00acc1; padding: 2px 12px; border-radius: 20px; font-size: 0.75em; font-weight: 700;">BRANCH #1</span>
        </div>
        <div style="display: flex; gap: 20px; font-size: 0.85em; opacity: 0.9;">
            <span>⚙️ Admin</span><span>🔗 Settings</span><span style="color: #fbbf24;">❓ Help</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 4. TOP CONTROLS (Updated & Fixed) ---
col_search, col_btn, col_dl = st.columns([3, 1, 0.5]) 

with col_search:
    search = st.text_input("", placeholder="🔍 Search borrower by name...", label_visibility="collapsed")

with col_btn:
    with st.popover("➕ New Loan Entry", use_container_width=True):
        with st.form("loan_form", clear_on_submit=True):
            st.markdown("### Client Details")
            name = st.text_input("Customer Name")
            amount = st.number_input("Principal Amount (UGX)", min_value=0, step=50000)
            rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.5)
            
            if st.form_submit_button("Confirm & Save"):
                new_data = pd.DataFrame([{
                    'SN': len(df) + 1,
                    'CUSTOMER_NAME': name,
                    'LOAN_AMOUNT': amount,
                    'AMOUNT_PAID': 0,
                    'OUTSTANDING_AMOUNT': amount,
                    'INTEREST_RATE': rate,
                    'DATE_ISSUED': datetime.now().strftime("%Y-%m-%d")
                }])
                new_data.to_csv(DB_FILE, mode='a', header=False, index=False)
                st.success("Loan Recorded!")
                st.cache_data.clear()
                st.rerun()

with col_dl:
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥",
        data=csv_data,
        file_name=f"Zoe_Lend_Report_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        help="Download current records as CSV"
    )

# --- 5. DASHBOARD TABS ---
menu_tabs = st.tabs(["📊 Overview", "👥 Borrowers List", "💰 Repayments", "📅 Calendar"])

with menu_tabs[0]:
    st.write("") 
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="box-card"><div class="box-title">Total Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="box-card"><div class="box-title">Total Principal</div><div class="box-value">UGX {df["LOAN_AMOUNT"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="box-card"><div class="box-title">Collections</div><div class="box-value">UGX {df["AMOUNT_PAID"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c4:
            active = len(df[df['AMOUNT_PAID'] < df['LOAN_AMOUNT']])
            st.markdown(f'<div class="box-card"><div class="box-title">Active Loans</div><div class="box-value">{active}</div></div>', unsafe_allow_html=True)
        
        st.write("---")
        st.subheader("Recent Loan Records")
        st.dataframe(
            df, 
            column_config={
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %d"),
                "AMOUNT_PAID": st.column_config.NumberColumn("Collected", format="UGX %d"),
                "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %d"),
                "INTEREST_RATE": st.column_config.NumberColumn("Rate", format="%d%%"),
            },
            hide_index=True, 
            use_container_width=True
        )
    else:
        st.info("No records found. Click 'New Loan Entry' to begin.")

with menu_tabs[1]:
    st.info("Borrower CRM Management - coming soon.")
