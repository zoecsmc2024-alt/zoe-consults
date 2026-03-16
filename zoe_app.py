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
    .main { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { 
        color: #ffffff !important; opacity: 1 !important;
    }
    th { background-color: #00acee !important; color: white !important; text-align: center !important; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINES ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'])
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['SN','OFFER_NO','NAME','CONTACT','DATE_OF_ISSUE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS','DURATION_MONTHS','Last_Payment_Date'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def get_loan_status(last_payment_date):
    days = (datetime.datetime.now() - pd.to_datetime(last_payment_date)).days
    if days <= 30: return "Active"
    elif 31 <= days <= 60: return "Risky"
    else: return "Dormant"

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
if not df.empty:
    df['STATUS'] = df['Last_Payment_Date'].apply(get_loan_status)

# --- 4. SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_URL): st.image(LOGO_URL, width=120)
    st.title("Zoe Consults")
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
        def style_rows(res):
            return ['background-color: #f1f5f9' if i % 2 == 0 else 'background-color: #ffffff' for i in range(len(res))]

        def color_status(val):
            if val == 'Active': color = '#10b981'
            elif val == 'Risky': color = '#f59e0b'
            else: color = '#ef4444'
            return f'color: {color}; font-weight: bold'

        display_cols = ['SN', 'OFFER_NO', 'NAME', 'DATE_OF_ISSUE', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']
        temp_df = df[display_cols].copy()
        temp_df['DATE_OF_ISSUE'] = temp_df['DATE_OF_ISSUE'].dt.strftime('%d-%b-%Y')

        st.table(temp_df.style.apply(style_rows, axis=0).applymap(color_status, subset=['STATUS']).format({"LOAN_AMOUNT": "{:,.0f}", "OUTSTANDING_AMOUNT": "{:,.0f}"}))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Disbursement")
    with st.form("new_loan"):
        c1, c2 = st.columns(2)
        with c1:
            sn = st.text_input("SN", value=f"{len(df)+1:05d}")
            off_no = st.text_input("OFFER NO")
            name = st.text_input("NAME")
        with c2:
            contact = st.text_input("CONTACT")
            doi = st.date_input("DATE OF ISSUE")
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("MONTHLY RATE (%)", value=3)
            dur = st.number_input("DURATION (MONTHS)", min_value=1, value=6)
        
        if st.form_submit_button("✅ Save & Disburse"):
            to_pay = amt + (amt * (rate/100) * dur)
            new_row = pd.DataFrame([{'SN': sn, 'OFFER_NO': off_no, 'NAME': name, 'CONTACT': contact, 'DATE_OF_ISSUE': doi, 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': to_pay, 'STATUS': 'Active', 'DURATION_MONTHS': dur, 'Last_Payment_Date': doi}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Recorded!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        # We use .strip() to remove any accidental spaces
        cid = st.text_input("Enter SN (e.g. 00001)").strip()
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        
        if st.form_submit_button("Submit"):
            # This makes sure we compare text to text
            df['SN'] = df['SN'].astype(str).str.strip()
            
            idx = df[df['SN'] == cid].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
                save_data(df)
                st.success(f"Payment of UGX {p_amt:,.0f} logged for SN {cid}!")
                st.rerun()
            else:
                st.error(f"SN '{cid}' not found. Please check the Daily Report for the correct SN.")

elif choice == "📄 Client Report":
    st.title("📄 Client Report")
    if not df.empty:
        client = st.selectbox("Select Client", df['NAME'].unique())
        c = df[df['NAME'] == client].iloc[0]
        st.markdown(f"""<div style="padding:20px; border:1px solid #e2e8f0; border-radius:10px;">
            <h3>ZOE CONSULTS LIMITED</h3>
            <p><b>Client:</b> {c['NAME']} | <b>Status:</b> {c['STATUS']}</p>
            <p><b>Contact:</b> {c['CONTACT']} | <b>Disbursement:</b> {pd.to_datetime(c['DATE_OF_ISSUE']).strftime('%d-%b-%Y')}</p>
            <p><b>Outstanding:</b> UGX {c['OUTSTANDING_AMOUNT']:,.0f}</p>
        </div>""", unsafe_allow_html=True)
        st.subheader("Repayment Schedule")
        sched = generate_schedule(c['LOAN_AMOUNT'], c['INTEREST_RATE'], c['DURATION_MONTHS'])
        st.table(sched.style.format("{:,.0f}"))
