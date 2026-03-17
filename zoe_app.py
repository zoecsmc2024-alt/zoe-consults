import streamlit as st
import pandas as pd

# --- 1. CONFIG & ADMIN THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Hide the Sidebar entirely */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    
    /* Main Content Background */
    .stApp { background-color: #ffffff; }

    /* Admin Header Style */
    .admin-header {
        background-color: #f7f7f7;
        border: 1px solid #e0e0e0;
        padding: 10px 15px;
        margin-bottom: 25px;
        font-weight: bold;
        color: #555;
        border-radius: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Box Cards (Matching your Admin design) */
    .box-card {
        background: white;
        border: 1px solid #e0e0e0;
        padding: 25px;
        border-radius: 4px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .box-title { color: #888; font-size: 0.85em; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; }
    .box-value { color: #333; font-size: 1.8em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        df = pd.read_csv("zoe_database.csv")
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'INTEREST_RATE']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. DASHBOARD CONTENT ---
# Header with a "New Borrower" button shortcut
st.markdown("""
    <div class="admin-header">
        <span>ZoeLend IQ > Dashboard Summary</span>
        <span style="font-size: 0.8em; color: #00acc1;">Logged in as Admin</span>
    </div>
""", unsafe_allow_html=True)

if not df.empty:
    # 4-Column Summary Row
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f'<div class="box-card"><div class="box-title">Total Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
    with c2:
        total_principal = df["LOAN_AMOUNT"].sum()
        st.markdown(f'<div class="box-card"><div class="box-title">Principal Released</div><div class="box-value">UGX {total_principal:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        total_collected = df["AMOUNT_PAID"].sum()
        st.markdown(f'<div class="box-card"><div class="box-title">Collections</div><div class="box-value">UGX {total_collected:,.0f}</div></div>', unsafe_allow_html=True)
    with c4:
        # Loans with remaining balance
        active_loans = len(df[df['AMOUNT_PAID'] < df['LOAN_AMOUNT']])
        st.markdown(f'<div class="box-card"><div class="box-title">Active Loans</div><div class="box-value">{active_loans}</div></div>', unsafe_allow_html=True)
else:
    st.error("⚠️ Data connection error. Please ensure 'zoe_database.csv' is uploaded and formatted correctly.")
