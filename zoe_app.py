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

# --- 2. THE FINANCIAL ENGINES ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['Start_Date'] = pd.to_datetime(df['Start_Date'])
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Phone', 'NIN', 'Address', 'Next_of_Kin', 'Employer', 'Principal_UGX', 'Annual_Rate', 'Duration_Months', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def generate_schedule(principal, annual_rate, months):
    """Calculates monthly installments using the Amortization formula."""
    monthly_rate = annual_rate / 12
    if monthly_rate > 0:
        installment = (principal * monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    else:
        installment = principal / months
    
    schedule = []
    rem_bal = principal
    for i in range(1, int(months) + 1):
        interest = rem_bal * monthly_rate
        princ_rep = installment - interest
        rem_bal -= princ_rep
        schedule.append({
            "Month": i,
            "Installment (UGX)": round(installment, 0),
            "Principal (UGX)": round(princ_rep, 0),
            "Interest (UGX)": round(interest, 0),
            "Balance (UGX)": max(0, round(rem_bal, 0))
        })
    return pd.DataFrame(schedule)

# --- 3. LOGIN GATE ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ: Pro Edition")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Secure Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 4. APP INTERFACE ---
df = load_data()

with st.sidebar:
    if os.path.exists(LOGO_URL):
        st.image(LOGO_URL, width=120)
    else: st.header("🏦")
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("LMS Navigation", ["📊 Dashboard", "👤 Client Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 5. PAGES ---
if choice == "📊 Dashboard":
    st.title("📊 Financial Portfolio")
    if df.empty:
        st.info("No data found.")
    else:
        total_p = df['Principal_UGX'].sum()
        st.metric("Total Principal Disbursed", f"UGX {total_p:,.0f}")
        st.dataframe(df[['Customer_ID', 'Name', 'Phone', 'Principal_UGX', 'Duration_Months', 'Status']], use_container_width=True, hide_index=True)

elif choice == "👤 Client Onboarding":
    st.title("👤 New Client Registration")
    with st.form("kyc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n = st.text_input("Full Name")
            phone = st.text_input("Phone Number")
            nin = st.text_input("NIN (National ID)")
        with col2:
            addr = st.text_input("Physical Address")
            nok = st.text_input("Next of Kin")
            emp = st.text_input("Employer / Business")
        
        st.markdown("---")
        col_a, col_b = st.columns(2)
        with col_a:
            a = st.number_input("Loan Amount (UGX)", min_value=1000, step=50000)
            r = st.number_input("Annual Interest Rate (e.g. 0.15)", value=0.15)
        with col_b:
            d = st.number_input("Duration (Months)", min_value=1, max_value=36, value=6)
        
        if st.form_submit_button("✅ Disburse & Generate Schedule"):
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            now = datetime.datetime.now()
            new_row = pd.DataFrame([{'Customer_ID': int(new_id), 'Name': n, 'Phone': phone, 'NIN': nin, 'Address': addr, 'Next_of_Kin': nok, 'Employer': emp, 'Principal_UGX': float(a), 'Annual_Rate': float(r), 'Duration_Months': int(d), 'Start_Date': now, 'Last_Payment_Date': now, 'Status': 'Active'}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success(f"Successfully Onboarded {n}!"); st.balloons()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    cid = st.number_input("Client ID", min_value=101)
    p_amt = st.number_input("Amount (UGX)", min_value=500)
    if st.button("Confirm Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            save_data(df); st.success("Payment Logged!"); st.rerun()

elif choice == "📄 Client Report":
    st.title("📄 Client Statement & Repayment Schedule")
    if not df.empty:
        client = st.selectbox("Search Client", df['Name'].unique())
        c = df[df['Name'] == client].iloc[0]
        
        st.markdown(f"""
        ### **OFFICIAL STATEMENT: {c['Name']}**
        * **NIN:** {c['NIN']} | **Phone:** {c['Phone']}
        * **Principal:** UGX {c['Principal_UGX']:,.0f} | **Rate:** {c['Annual_Rate']*100}%
        ---
        """)
        
        # GENERATE AND SHOW SCHEDULE
        st.subheader("Monthly Repayment Schedule")
        schedule = generate_schedule(c['Principal_UGX'], c['Annual_Rate'], c['Duration_Months'])
        st.table(schedule.style.format("{:,.0f}"))
