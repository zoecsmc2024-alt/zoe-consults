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
    
    /* SIDEBAR VISIBILITY FIX */
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    
    /* Force 'Zoe Consults' and all Navigation text to be pure White */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label { 
        color: #ffffff !important; 
        opacity: 1 !important;
    }
    
    /* SPREADSHEET TABLE STYLING */
    th { background-color: #00acee !important; color: white !important; text-align: center !important; }
    
    .report-box { background-color: white; padding: 30px; border: 1px solid #e2e8f0; border-radius: 10px; color: black; }
    
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent; color: white !important; border: 2px solid white !important; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINES ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'])
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['SN','OFFER_NO','NAME','GENDER','CONTACT','DATE_OF_ISSUE','PAYMENT_DATE','LOAN_AMOUNT','INTEREST_RATE','INTEREST','AMOUNT_TO_BE_PAID','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS','DURATION_MONTHS'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def generate_schedule(principal, monthly_rate_pct, months):
    rate = monthly_rate_pct / 100
    if rate > 0:
        installment = (principal * rate * (1 + rate)**months) / ((1 + rate)**months - 1)
    else: installment = principal / months
    data = []
    rem = principal
    for i in range(1, int(months) + 1):
        interest = rem * rate
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
    st.stop()

df = load_data()

# --- 4. SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_URL): st.image(LOGO_URL, width=120)
    st.title("Zoe Consults") # This is now forced to white by CSS
    st.markdown("---")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Portfolio Registry")
    if df.empty: st.info("Registry is empty.")
    else:
        def style_rows(row): return ['background-color: #ff9900; color: black; font-weight: 500'] * len(row)
        st.table(df[['SN', 'OFFER_NO', 'NAME', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']].style.apply(style_rows, axis=1).format({"LOAN_AMOUNT": "{:,.0f}", "OUTSTANDING_AMOUNT": "{:,.0f}"}))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Issue")
    with st.form("new_loan"):
        c1, c2 = st.columns(2)
        with c1:
            sn = st.text_input("SN", value=f"{len(df)+1:05d}")
            off_no = st.text_input("OFFER NO")
            name = st.text_input("NAME")
            gender = st.selectbox("GENDER", ["M", "F"])
        with c2:
            contact = st.text_input("CONTACT")
            doi = st.date_input("DATE OF ISSUE")
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("MONTHLY INTEREST RATE (%)", value=3)
            dur = st.number_input("DURATION (MONTHS)", min_value=1, value=6)
        
        if st.form_submit_button("✅ Save to Registry"):
            interest_amt = amt * (rate/100) * dur
            to_pay = amt + interest_amt
            new_row = pd.DataFrame([{'SN': sn, 'OFFER_NO': off_no, 'NAME': name, 'GENDER': gender, 'CONTACT': contact, 'DATE_OF_ISSUE': doi, 'PAYMENT_DATE': doi, 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'INTEREST': interest_amt, 'AMOUNT_TO_BE_PAID': to_pay, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': to_pay, 'STATUS': 'BCE', 'DURATION_MONTHS': dur}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Recorded!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        cid = st.text_input("Enter SN")
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Submit Payment"):
            idx = df[df['SN'] == cid].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                save_data(df); st.success("Updated!"); st.rerun()

elif choice == "📄 Client Report":
    st.title("📄 Client Report & Schedule")
    if not df.empty:
        client = st.selectbox("Select Client", df['NAME'].unique())
        c = df[df['NAME'] == client].iloc[0]
        st.markdown(f"""<div class="report-box">
            <h2 style="text-align:center;">ZOE CONSULTS LIMITED</h2>
            <p><b>Client:</b> {c['NAME']} | <b>SN:</b> {c['SN']}</p>
            <p><b>Contact:</b> {c['CONTACT']} | <b>Gender:</b> {c['GENDER']}</p>
            <hr>
            <p><b>Loan Amount:</b> UGX {c['LOAN_AMOUNT']:,.0f}</p>
            <p><b>Monthly Rate:</b> {c['INTEREST_RATE']}%</p>
            <p><b>Total to Pay:</b> UGX {c['AMOUNT_TO_BE_PAID']:,.0f}</p>
        </div>""", unsafe_allow_html=True)
        st.subheader("Amortized Repayment Schedule")
        sched = generate_schedule(c['LOAN_AMOUNT'], c['INTEREST_RATE'], c['DURATION_MONTHS'])
        st.table(sched.style.format("{:,.0f}"))
