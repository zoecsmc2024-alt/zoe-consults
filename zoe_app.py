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
    # 1. TOP PROFILE HEADER (Inspired by your image)
    if not df.empty:
        client_options = df.apply(lambda x: f"{str(x['SN']).zfill(5)} - {x['NAME']}", axis=1).tolist()
        selected_client = st.selectbox("Search Borrower", client_options)
        c = df[df['SN'].astype(str).str.zfill(5) == selected_client.split(" - ")[0]].iloc[0]

        st.markdown(f"""
            <div style="background-color: white; padding: 20px; border-radius: 10px; border-top: 5px solid #00acc1; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h2 style="margin:0; color:#1e293b;">{c['NAME']}</h2>
                        <p style="color:#00acc1; font-weight:bold; margin:0;">CL-{c['SN']}</p>
                        <p style="font-size:0.8em; color:gray;">Issued: {c['DATE_OF_ISSUE']}</p>
                    </div>
                    <div style="text-align: right; font-size:0.9em;">
                        <p><b>Address:</b> {c['LOCATION']}</p>
                        <p><b>NIN:</b> {c['NIN']}</p>
                        <p><b>Employer:</b> {c['EMPLOYER']}</p>
                    </div>
                </div>
                <div style="margin-top:15px;">
                    <span style="background-color:#00acc1; color:white; padding:5px 15px; border-radius:5px; font-size:0.8em;">Add Loan</span>
                    <span style="background-color:#1e293b; color:white; padding:5px 15px; border-radius:5px; font-size:0.8em; margin-left:10px;">View All Loans</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.write("")

        # 2. MAIN LOAN SUMMARY BAR (Teal Theme)
       # --- WRAP THIS SECTION IN ST.MARKDOWN ---
# 2. MAIN LOAN SUMMARY BAR (Teal Theme)
    st.markdown(f"""
        <style>
            .loan-header {{ background-color: #00acc1; color: white; padding: 10px; display: flex; justify-content: space-between; font-weight: bold; border-radius: 8px 8px 0 0; }}
            .loan-row {{ background-color: white; padding: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #eee; font-size: 0.9em; }}
        </style>
        
        <div class="loan-header">
            <span>Loan#</span><span>Principal</span><span>Interest</span><span>Paid</span><span>Balance</span><span>Status</span>
        </div>
        <div class="loan-row">
            <span>LN-{c['SN']}</span>
            <span>{float(c['LOAN_AMOUNT']):,.0f}</span>
            <span>{c['INTEREST_RATE']}%</span>
            <span>{float(c['AMOUNT_PAID']):,.0f}</span>
            <span style="color:#00acc1; font-weight:bold;">{float(c['OUTSTANDING_AMOUNT']):,.0f}</span>
            <span style="background-color:#00acc1; color:white; padding:2px 8px; border-radius:4px; font-size:0.8em;">{c['STATUS']}</span>
        </div>
    """, unsafe_allow_html=True)
        
