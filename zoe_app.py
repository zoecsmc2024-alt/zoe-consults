import streamlit as st
import pandas as pd

# --- 1. CONFIG & ADMIN THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    /* Gradient Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    }
    /* Admin Header Style */
    .admin-header {
        background-color: #f7f7f7;
        border: 1px solid #e0e0e0;
        padding: 10px 15px;
        margin-bottom: 20px;
        font-weight: bold;
        color: #555;
        border-radius: 4px;
    }
    /* Box Cards (The col-md-3 style from your images) */
    .box-card {
        background: white;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 4px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .box-title { color: #888; font-size: 0.8em; text-transform: uppercase; margin-bottom: 8px; }
    .box-value { color: #333; font-size: 1.6em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        df = pd.read_csv("zoe_database.csv")
        # Ensure numbers are cleaned for math
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'INTEREST_RATE']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>ZoeLend IQ</h2>", unsafe_allow_html=True)
    # For now, we only have one choice to keep it simple
    choice = st.radio("MAIN MENU", ["📊 Dashboard"])

# --- 4. DASHBOARD CONTENT ---
st.markdown(f'<div class="admin-header">Main Content > Dashboard Summary</div>', unsafe_allow_html=True)

if not df.empty:
    # 4-Column Row (Borrowers, Principal, Collections, Active)
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f'<div class="box-card"><div class="box-title">Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
    with c2:
        total_principal = df["LOAN_AMOUNT"].sum()
        st.markdown(f'<div class="box-card"><div class="box-title">Principal Released</div><div class="box-value">UGX {total_principal:,.0f}</div></div>', unsafe_allow_html=True)
    with c3:
        total_collected = df["AMOUNT_PAID"].sum()
        st.markdown(f'<div class="box-card"><div class="box-title">Collections</div><div class="box-value">UGX {total_collected:,.0f}</div></div>', unsafe_allow_html=True)
    with c4:
        active_loans = len(df[df['AMOUNT_PAID'] < df['LOAN_AMOUNT']]) # Simple logic for now
        st.markdown(f'<div class="box-card"><div class="box-title">Active Loans</div><div class="box-value">{active_loans}</div></div>', unsafe_allow_html=True)
else:
    st.warning("Database is empty or not found. Please ensure 'zoe_database.csv' exists.")
