import streamlit as st
import pandas as pd
import plotly.express as px
import base64

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# CSS for the Gradient Sidebar, Premium Metrics, and Clean Tables
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid #334155 !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(10px);
    }
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stMetricLabel"] { color: #64748b !important; font-weight: bold; text-transform: uppercase; font-size: 0.8em; }
    [data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 800; }
    .stTable thead tr th { background-color: #00acc1 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
def load_data():
    try:
        df = pd.read_csv("zoe_database.csv")
        df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'])
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:white; text-align:center;'>ZoeLend IQ</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.7em; font-weight: bold; letter-spacing: 1.5px; text-align:center;'>MAIN MENU</p>", unsafe_allow_html=True)
    choice = st.radio("Nav", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"], label_visibility="collapsed")

# --- 4. PAGE LOGIC ---

# PAGE 1: DAILY REPORT
if choice == "📊 Daily Report":
    st.title("📊 Portfolio Insights")
    if not df.empty:
        # Profit Intelligence Math
        df['profit_ratio'] = (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100)) / (df['LOAN_AMOUNT'] + (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100)))
        total_profit_earned = (df['AMOUNT_PAID'] * df['profit_ratio']).sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Principal", f"UGX {df['LOAN_AMOUNT'].sum():,.0f}")
        m2.metric("Total Collected", f"UGX {df['AMOUNT_PAID'].sum():,.0f}")
        m3.metric("Outstanding", f"UGX {df['OUTSTANDING_AMOUNT'].sum():,.0f}")
        m4.metric("Total Profit", f"UGX {total_profit_earned:,.0f}")

        st.subheader("📈 Business Growth Strategy")
        chart_df = df.copy().sort_values('DATE_OF_ISSUE')
        chart_df['Cumulative_Principal'] = chart_df['LOAN_AMOUNT'].cumsum()
        chart_df['Cumulative_Profit'] = (chart_df['AMOUNT_PAID'] * chart_df['profit_ratio']).cumsum()
        st.area_chart(chart_df.set_index('DATE_OF_ISSUE')[['Cumulative_Principal', 'Cumulative_Profit']])
    else:
        st.info("No data available.")

# PAGE 2: CLIENT REPORT (THE "BULLETPROOF" VERSION)
elif choice == "📄 Client Report":
    st.title("📄 Client Statement")
    if not df.empty:
        search_query = st.selectbox("Search Borrower", df['SN'].astype(str) + " - " + df['CUSTOMER_NAME'])
        if search_query:
            sn_selected = int(search_query.split(" - ")[0])
            c = df[df['SN'] == sn_selected].iloc[0]
            
            st.markdown(f"""
                <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border-left: 5px solid #00acc1;">
                    <h2 style="margin:0;">{c.get('CUSTOMER_NAME', 'Unknown')}</h2>
                    <p>NIN: {c.get('NIN', 'N/A')} | Phone: {c.get('PHONE', 'N/A')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            t1, t2 = st.tabs(["📊 Ledger", "📝 Details"])
            with t1:
                st.table(pd.DataFrame([
                    {"Item": "Loan Amount", "Value": f"UGX {c.get('LOAN_AMOUNT', 0):,.0f}"},
                    {"Item": "Total Paid", "Value": f"UGX {c.get('AMOUNT_PAID', 0):,.0f}"},
                    {"Item": "Balance", "Value": f"UGX {c.get('OUTSTANDING_AMOUNT', 0):,.0f}"}
                ]))
    else:
        st.info("Onboard clients to view reports.")

# PAGE 3 & 4: (STUBS FOR OTHER PAGES)
else:
    st.title(choice)
    st.write("Section coming soon...")
