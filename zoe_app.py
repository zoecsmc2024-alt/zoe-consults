import streamlit as st
import pandas as pd

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    /* Gradient Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid #334155 !important;
    }
    /* Admin Header Style */
    .admin-header {
        background-color: #f7f7f7;
        border: 1px solid #e0e0e0;
        padding: 8px 15px;
        margin-bottom: 20px;
        font-weight: bold;
        color: #555;
        border-radius: 4px;
    }
    /* Box Cards (col-md-3 style) */
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
    
    /* Clean Tables */
    .stTable thead tr th { background-color: #00acc1 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        # Load the CSV
        df = pd.read_csv("zoe_database.csv")
        # Basic cleanup
        df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'], errors='coerce')
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>ZoeLend IQ</h2>", unsafe_allow_html=True)
    choice = st.radio("MAIN MENU", ["📊 Dashboard", "👤 Onboarding", "💰 Payments", "📄 Client Report"])

# --- 4. MAIN CONTENT ---

# BREADCRUMB
st.markdown(f'<div class="admin-header">Main Content > {choice.split(" ")[1]}</div>', unsafe_allow_html=True)

if choice == "📊 Dashboard":
    if not df.empty:
        # 4-Column Box Row
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f'<div class="box-card"><div class="box-title">Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="box-card"><div class="box-title">Principal Released</div><div class="box-value">UGX {df["LOAN_AMOUNT"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="box-card"><div class="box-title">Collections</div><div class="box-value">UGX {df["AMOUNT_PAID"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with c4:
            # Active vs Closed logic
            active = len(df[df['STATUS'] == 'Active'])
            st.markdown(f'<div class="box-card"><div class="box-title">Active Loans</div><div class="box-value">{active}</div></div>', unsafe_allow_html=True)

        st.write("")
        st.subheader("📋 Recent Loan Portfolio")
        cols = ['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'STATUS']
        st.table(df[cols].tail(10)) # Show last 10 entries
    else:
        st.info("No data found. Please check your zoe_database.csv file.")

elif choice == "👤 Onboarding":
    st.title("👤 New Client Onboarding")
    st.write("We will build the form logic here next!")

else:
    st.title(choice)
    st.info("Section pending configuration.")
