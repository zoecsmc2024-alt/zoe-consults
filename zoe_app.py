import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    /* Premium Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid #334155 !important;
    }
    /* Logo Styling */
    .logo-container { text-align: center; padding: 20px; }
    .logo-circle {
        width: 80px; height: 80px; background: #00acc1;
        border-radius: 50%; display: inline-block;
        line-height: 80px; color: white; font-size: 24px; font-weight: bold;
        box-shadow: 0 4px 15px rgba(0,172,193,0.3);
    }
    /* Tables & Metrics */
    [data-testid="stMetric"] {
        background-color: white !important; border: 1px solid #e2e8f0 !important;
        padding: 20px !important; border-radius: 12px !important;
    }
    .stTable thead tr th { background-color: #00acc1 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        df = pd.read_csv("zoe_database.csv")
        df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'])
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown('<div class="logo-container"><div class="logo-circle">ZC</div></div>', unsafe_allow_html=True)
    st.markdown("<h3 style='color:white; text-align:center;'>Zoe Consults</h3>", unsafe_allow_html=True)
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])
    # --- 4. DASHBOARD LOGIC ---

if choice == "📊 Daily Report":
    st.title("📊 Portfolio Insights")
    
    if not df.empty:
        # Profit Calculations (Safety added for division by zero)
        df['profit_ratio'] = (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100)) / (df['LOAN_AMOUNT'] + (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100) + 0.0001))
        total_profit = (df['AMOUNT_PAID'] * df['profit_ratio']).sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Principal", f"UGX {df['LOAN_AMOUNT'].sum():,.0f}")
        m2.metric("Total Collected", f"UGX {df['AMOUNT_PAID'].sum():,.0f}")
        m3.metric("Outstanding", f"UGX {df['OUTSTANDING_AMOUNT'].sum():,.0f}")
        m4.metric("Total Profit", f"UGX {total_profit:,.0f}")

        # The Loan Registry Table
        st.subheader("📋 Loan Portfolio Registry")
        cols = ['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'STATUS']
        safe_cols = [c for c in cols if c in df.columns]
        st.table(df[safe_cols].sort_values('SN', ascending=False))
    else:
        st.info("No data found in zoe_database.csv")

elif choice == "📄 Client Report":
    st.title("📄 Client Statement")
    if not df.empty:
        # Combined ID and Name for search
        search_list = df['SN'].astype(str) + " - " + df['CUSTOMER_NAME']
        search = st.selectbox("Select Client", search_list)
        
        if search:
            sn = int(search.split(" - ")[0])
            c = df[df['SN'] == sn].iloc[0]
            
            # Detailed Profile Card
            st.markdown(f"""
                <div style="background:#f8fafc; padding:20px; border-radius:12px; border-left:6px solid #00acc1;">
                    <h2 style="margin:0; color:#0f172a;">{c.get('CUSTOMER_NAME')}</h2>
                    <p style="margin:5px 0; color:#64748b;"><b>NIN:</b> {c.get('NIN', 'N/A')} | <b>Phone:</b> {c.get('PHONE', 'N/A')}</p>
                    <p style="margin:5px 0; color:#64748b;"><b>Location:</b> {c.get('LOCATION', 'N/A')} | <b>Next of Kin:</b> {c.get('NEXT_OF_KIN', 'N/A')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            t1, t2 = st.tabs(["💰 Ledger Summary", "📅 Loan Schedule"])
            with t1:
                summary_data = {
                    "Description": ["Total Loan Amount", "Total Repaid", "Current Balance Due"],
                    "Amount (UGX)": [f"{c['LOAN_AMOUNT']:,.0f}", f"{c['AMOUNT_PAID']:,.0f}", f"{c['OUTSTANDING_AMOUNT']:,.0f}"]
                }
                st.table(pd.DataFrame(summary_data))
    else:
        st.info("No clients found in the database.")

else:
    st.title(choice)
    st.info("This section is under construction. Your data is safe!")
