import streamlit as st
import pandas as pd
import datetime
import os

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
    .report-box { background-color: white; padding: 30px; border: 1px solid #e2e8f0; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINES ---
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
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Phone', 'NIN', 'Address', 'Next_of_Kin', 'Employer', 'Principal_UGX', 'Monthly_Rate', 'Duration_Months', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def generate_schedule(principal, monthly_rate, months):
    # Monthly compounding/amortization logic
    if monthly_rate > 0:
        installment = (principal * monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    else: installment = principal / months
    
    data = []
    rem = principal
    for i in range(1, int(months) + 1):
        interest = rem * monthly_rate
        princ_rep = installment - interest
        rem -= princ_rep
        data.append({"Month": i, "Installment": round(installment, 0), "Principal": round(princ_rep, 0), "Interest": round(interest, 0), "Balance": max(0, round(rem, 0))})
    return pd.DataFrame(data)

# --- 3. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Denied")
    st.stop()

# --- 4. DATA PROCESSING ---
df = load_data()
with st.sidebar:
    if os.path.exists(LOGO_URL): st.image(LOGO_URL, width=120)
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Client Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Portfolio Registry")
    if df.empty: st.info("No data.")
    else:
        st.table(df[['Customer_ID', 'Name', 'Principal_UGX', 'Status']].style \
            .set_properties(**{'background-color': '#e0f2fe'}, subset=['Customer_ID', 'Name']) \
            .format({"Principal_UGX": "UGX {:,.0f}"}))

elif choice == "👤 Client Onboarding":
    st.title("👤 New Loan Disbursement")
    with st.form("kyc"):
        c1, c2 = st.columns(2)
        with c1:
            n = st.text_input("Name"); ph = st.text_input("Phone"); ni = st.text_input("NIN")
            disburse_date = st.date_input("Disbursement Date", datetime.date.today())
        with c2:
            ad = st.text_input("Address"); nk = st.text_input("Next of Kin"); em = st.text_input("Employer")
        
        st.markdown("---")
        a = st.number_input("Principal (UGX)", min_value=1000)
        r = st.number_input("Monthly Interest Rate (e.g. 0.10 for 10% per month)", value=0.10)
        d = st.number_input("Duration (Months)", min_value=1, value=6)
        
        if st.form_submit_button("✅ Register & Disburse"):
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            new_row = pd.DataFrame([{'Customer_ID': int(new_id), 'Name': n, 'Phone': ph, 'NIN': ni, 'Address': ad, 'Next_of_Kin': nk, 'Employer': em, 'Principal_UGX': float(a), 'Monthly_Rate': float(r), 'Duration_Months': int(d), 'Start_Date': disburse_date, 'Last_Payment_Date': disburse_date, 'Status': 'Active'}])
            save_data(pd.concat([df, new_row], ignore_index=True)); st.success("Success!"); st.balloons()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("payment_form"):
        cid = st.number_input("Client ID", min_value=101)
        amt_paid = st.number_input("Amount Paid (UGX)", min_value=500)
        if st.form_submit_button("Confirm Payment"):
            idx = df[df['Customer_ID'] == cid].index
            if not idx.empty:
                df.at[idx[0], 'Principal_UGX'] -= amt_paid
                df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
                save_data(df); st.success("Payment Logged!"); st.rerun()
            else: st.error("ID not found.")

elif choice == "📄 Client Report":
    st.title("📄 Client Statement")
    if not df.empty:
        client = st.selectbox("Select Client", df['Name'].unique())
        c = df[df['Name'] == client].iloc[0]
        
        st.markdown(f"""
        <div class="report-box">
            <h2 style="color: #1e293b; text-align: center;">ZOE CONSULTS LIMITED</h2>
            <hr>
            <p><b>Client:</b> {c['Name']} (ID: {c['Customer_ID']})</p>
            <p><b>Disbursed On:</b> {pd.to_datetime(c['Start_Date']).strftime('%d %B %Y')}</p>
            <p><b>Monthly Interest Rate:</b> {c['Monthly_Rate']*100}%</p>
            <p><b>Principal:</b> UGX {c['Principal_UGX']:,.0f}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Monthly Repayment Schedule")
        sched = generate_schedule(c['Principal_UGX'], c['Monthly_Rate'], c['Duration_Months'])
        st.table(sched.style.format("{:,.0f}"))
