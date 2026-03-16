import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
LOGO_URL = "logo.jpg" 
st.set_page_config(page_title="ZoeLend IQ Pro", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: white !important; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] .stButton > button { background-color: transparent; color: white !important; border: 2px solid white !important; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINE ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['Start_Date'] = pd.to_datetime(df['Start_Date'])
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Phone', 'NIN', 'Address', 'Next_of_Kin', 'Employer', 'Principal_UGX', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

# --- 3. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ: Loandisk Edition")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Secure Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 4. DATA PROCESSING ---
df = load_data()
if not df.empty:
    def get_bal(r):
        today = datetime.datetime.now()
        start = pd.to_datetime(r['Start_Date'])
        months = (today.year - start.year) * 12 + (today.month - start.month)
        return round(r['Principal_UGX'] * (1 + (r['Annual_Rate']/12))**max(0, months), 0)
    df['Current_Balance'] = df.apply(get_bal, axis=1)

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_URL):
        st.image(LOGO_URL, width=120)
    else: st.header("🏦")
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("LMS Navigation", ["📊 Portfolio Dashboard", "👤 Client Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 6. PAGES ---
if choice == "📊 Portfolio Dashboard":
    st.title("📊 Portfolio Analytics")
    if df.empty:
        st.info("No data available.")
    else:
        c1, c2, c3 = st.columns(3)
        total_p = df['Principal_UGX'].sum()
        total_b = df['Current_Balance'].sum()
        total_i = total_b - total_p
        c1.metric("Principal Out", f"UGX {total_p:,.0f}")
        c2.metric("Portfolio Value", f"UGX {total_b:,.0f}")
        c3.metric("Profit (Interest)", f"UGX {total_i:,.0f}")
        
        # Donut Chart
        chart_data = pd.DataFrame({"Category": ["Principal", "Interest"], "Amount": [total_p, total_i]})
        fig = px.pie(chart_data, values='Amount', names='Category', hole=0.5, color_discrete_sequence=['#1e293b', '#10b981'])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df[['Customer_ID', 'Name', 'Phone', 'Principal_UGX', 'Status']], use_container_width=True, hide_index=True)

elif choice == "👤 Client Onboarding":
    st.title("👤 New Client Registration (KYC)")
    with st.form("kyc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n = st.text_input("Full Name")
            phone = st.text_input("Phone Number (MTN/Airtel)")
            nin = st.text_input("NIN (National ID)")
        with col2:
            addr = st.text_input("Physical Address (Village/Street)")
            nok = st.text_input("Next of Kin")
            emp = st.text_input("Employer / Business")
        
        st.markdown("---")
        a = st.number_input("Loan Amount (UGX)", min_value=1000)
        r = st.number_input("Annual Rate (e.g. 0.15 for 15%)", value=0.15)
        
        if st.form_submit_button("✅ Disburse Loan"):
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            now = datetime.datetime.now()
            new_row = pd.DataFrame([{'Customer_ID': int(new_id), 'Name': n, 'Phone': phone, 'NIN': nin, 'Address': addr, 'Next_of_Kin': nok, 'Employer': emp, 'Principal_UGX': float(a), 'Annual_Rate': float(r), 'Start_Date': now, 'Last_Payment_Date': now, 'Status': 'Active'}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success(f"Client {n} Onboarded!"); st.balloons()

elif choice == "💰 Payments":
    st.title("💰 Receive Payment")
    cid = st.number_input("Enter Client ID", min_value=101)
    p_amt = st.number_input("Amount Paid (UGX)", min_value=500)
    if st.button("Post Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Principal_UGX'] -= p_amt
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            save_data(df); st.success("Transaction Complete!"); st.rerun()
        else: st.error("Client ID not found.")

elif choice == "📄 Client Report":
    st.title("📄 Detailed Client Statement")
    if not df.empty:
        client = st.selectbox("Select Client", df['Name'].unique())
        c = df[df['Name'] == client].iloc[0]
        st.markdown(f"""
        ### **ZOE CONSULTS LTD STATEMENT**
        **Client ID:** {c['Customer_ID']} | **NIN:** {c['NIN']}
        **Phone:** {c['Phone']} | **Address:** {c['Address']}
        ---
        **FINANCIAL SUMMARY**
        * Original Principal: **UGX {c['Principal_UGX']:,.0f}**
        * Current Balance (with Interest): **UGX {c.get('Current_Balance', 0):,.0f}**
        * Last Payment Date: {pd.to_datetime(c['Last_Payment_Date']).strftime('%Y-%m-%d')}
        ---
        **RECOVERY INFO**
        * Next of Kin: {c['Next_of_Kin']}
        * Employer: {c['Employer']}
        """)
        st.button("🖨️ Export to PDF (Internal Use)")
