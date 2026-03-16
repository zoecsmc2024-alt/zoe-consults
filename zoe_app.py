import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# This CSS fixes the table headers and the report card look
# --- Line 11: CSS STYLING ---
st.markdown("""
    <style>
    /* 1. SIDEBAR & HEADER BLEND */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border-right: 1px solid #334155 !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(10px);
    }

    /* 2. PREMIUM METRIC TILES */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
        text-align: center !important;
    }
    [data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        font-size: 0.8em !important;
    }
    [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 800 !important;
    }

    /* 3. TABLE STYLING */
    .stTable td, .stTable th { color: #1e293b !important; }
    thead tr th { background-color: #00acc1 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    # (Optional: Add your circular logo code here)
    st.markdown("<p style='color: #94a3b8; font-size: 0.7em; font-weight: bold; letter-spacing: 1.5px; margin-top: 20px;'>MAIN MENU</p>", unsafe_allow_html=True)
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"], label_visibility="collapsed")
# --- 2. DATA ENGINE ---
def load_data():
    try:
        # 1. READ THE FILE (Make sure the filename matches yours!)
        df = pd.read_csv("zoe_database.csv") 
        
        # 2. PERFORM ANY CLEANUP
        # (Ensure columns like DATE_OF_ISSUE are datetime objects)
        df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'])
        
        # 3. NOW RETURN IT
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame() # Returns an empty table if the file is missing

# 4. CALL THE FUNCTION
df = load_data()
# --- 4. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Portfolio Insights")
    
    if not df.empty:
        # 1. PROFIT CALCULATIONS
        # We calculate how much of each payment is actual interest profit
        df['profit_ratio'] = (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100)) / (df['LOAN_AMOUNT'] + (df['LOAN_AMOUNT'] * (df['INTEREST_RATE']/100)))
        total_profit_earned = (df['AMOUNT_PAID'] * df['profit_ratio']).sum()

        # 2. TOP METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Principal", f"UGX {df['LOAN_AMOUNT'].sum():,.0f}")
        m2.metric("Total Collected", f"UGX {df['AMOUNT_PAID'].sum():,.0f}")
        m3.metric("Outstanding", f"UGX {df['OUTSTANDING_AMOUNT'].sum():,.0f}")
        m4.metric("Total Profit", f"UGX {total_profit_earned:,.0f}")

        # 3. GROWTH CHART
        st.subheader("📈 Business Growth Strategy")
        chart_df = df.copy()
        chart_df['DATE_OF_ISSUE'] = pd.to_datetime(chart_df['DATE_OF_ISSUE'])
        chart_df = chart_df.sort_values('DATE_OF_ISSUE')
        chart_df['Cumulative_Principal'] = chart_df['LOAN_AMOUNT'].cumsum()
        chart_df['Cumulative_Profit'] = (chart_df['AMOUNT_PAID'] * chart_df['profit_ratio']).cumsum()
        
        st.area_chart(chart_df.set_index('DATE_OF_ISSUE')[['Cumulative_Principal', 'Cumulative_Profit']])

        # 4. REGISTRY TABLE
        st.subheader("📋 Loan Portfolio Registry")
        display_cols = ['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'STATUS']
        # This line prevents the 'KeyError' by only showing columns that exist
        safe_cols = [c for c in display_cols if c in df.columns]
        st.table(df[safe_cols])
    else:
        st.info("No data found. Please onboard a client first!")
elif choice == "👤 Onboarding":
    st.title("👤 New Loan")
    with st.form("onboard"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME").upper(); nin = st.text_input("NIN")
            loc = st.text_input("LOCATION"); emp = st.text_input("EMPLOYER")
        with c2:
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("RATE (%)", value=3); dur = st.number_input("MONTHS", min_value=1, value=1)
            due = datetime.date.today() + datetime.timedelta(days=30*dur)
        if st.form_submit_button("✅ Save"):
            new_sn = str(len(df) + 1).zfill(5)
            new_row = pd.DataFrame([{'SN': new_sn, 'NAME': name, 'NIN': nin, 'LOCATION': loc, 'EMPLOYER': emp, 'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'), 'EXPECTED_DUE_DATE': due.strftime('%d-%b-%Y'), 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': amt+(amt*(rate/100)), 'STATUS': 'Active'}])
            df = pd.concat([df, new_row], ignore_index=True); save_data(df); st.success("Done!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn = st.text_input("Enter SN").strip().zfill(5)
        p_amt = st.number_input("Amount", min_value=100)
        if st.form_submit_button("Confirm"):
            idx = df[df['SN'] == sn].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt; df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                if df.at[idx[0], 'OUTSTANDING_AMOUNT'] <= 0: df.at[idx[0], 'STATUS'] = 'Cleared'
                save_data(df); st.success("Paid!"); st.rerun()
            else: st.error("Not found.")

elif choice == "📄 Client Report":
    st.title("📄 Client Statement")
    
    # 1. SEARCH BAR
    search_query = st.selectbox("Search Borrower", df['SN'].astype(str) + " - " + df['CUSTOMER_NAME'])
    
    if search_query:
        # Get the serial number from the selection
        sn_selected = int(search_query.split(" - ")[0])
        c = df[df['SN'] == sn_selected].iloc[0]

        # 2. CLIENT PROFILE HEADER
        st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border-left: 5px solid #00acc1; margin-bottom: 20px;">
                <h2 style="color: #0f172a; margin: 0;">{c.get('CUSTOMER_NAME', 'Unknown Client')}</h2>
                <p style="color: #64748b;">ID: {c.get('SN', 'N/A')} | Location: {c.get('LOCATION', 'N/A')}</p>
                <div style="display: flex; gap: 20px; margin-top: 10px;">
                    <span><b>NIN:</b> {c.get('NIN', 'N/A')}</span>
                    <span><b>Phone:</b> {c.get('PHONE', 'N/A')}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 3. LOAN SUMMARY TILES
        m1, m2, m3 = st.columns(3)
        m1.metric("Principal", f"UGX {float(c.get('LOAN_AMOUNT', 0)):,.0f}")
        m2.metric("Paid", f"UGX {float(c.get('AMOUNT_PAID', 0)):,.0f}")
        m3.metric("Balance", f"UGX {float(c.get('OUTSTANDING_AMOUNT', 0)):,.0f}")

        # 4. REPAYMENT TABS
        st.write("")
        tab1, tab2, tab3 = st.tabs(["📊 Repayments", "📝 Terms", "📅 Schedule"])

        with tab1:
            st.subheader("Repayment History")
            ledger_data = [
                {"Date": c.get('DATE_OF_ISSUE', 'N/A'), "Description": "Loan Released", "Amount": c.get('LOAN_AMOUNT', 0)},
                {"Date": "To Date", "Description": "Total Collections", "Amount": -c.get('AMOUNT_PAID', 0)}
            ]
            st.table(pd.DataFrame(ledger_data))
            st.button("➕ Add Repayment", key="add_rep")

        with tab2:
            st.write(f"**Interest Rate:** {c.get('INTEREST_RATE', '0')}%")
            st.write(f"**Next of Kin:** {c.get('NEXT_OF_KIN', 'N/A')}")

        with tab3:
            st.info(f"Final Maturity Date: {c.get('EXPECTED_DUE_DATE', 'N/A')}")
