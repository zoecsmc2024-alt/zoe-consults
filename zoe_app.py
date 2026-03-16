import streamlit as st
import pandas as pd
import os

# --- 1. SETTINGS & THEMING ---
LOGO_URL = "logo.jpg" 
st.set_page_config(page_title="ZoeLend IQ Pro", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    /* Table Header Styling to match your blue */
    th { background-color: #00acee !important; color: black !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINE ---
def load_data():
    if os.path.exists(FILE_NAME):
        return pd.read_csv(FILE_NAME)
    return pd.DataFrame(columns=['SN','OFFER_NO','NAME','GENDER','CONTACT','DATE_OF_ISSUE','PAYMENT_DATE','LOAN_AMOUNT','INTEREST_RATE','INTEREST','AMOUNT_TO_BE_PAID','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

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
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments"])

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Portfolio Registry")
    
    if df.empty:
        st.info("Registry is empty.")
    else:
        # Applying the Orange Background for the rows
        def style_portfolio(res):
            return pd.Series('background-color: #ff9900; color: black', index=res.index)

        # Formatting numbers to UGX
        st.table(df.style.apply(style_portfolio, axis=1).format({
            "LOAN_AMOUNT": "{:,.0f}",
            "INTEREST": "{:,.0f}",
            "AMOUNT_TO_BE_PAID": "{:,.0f}",
            "AMOUNT_PAID": "{:,.0f}",
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        }))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Issue")
    with st.form("new_loan"):
        c1, c2 = st.columns(2)
        with c1:
            sn = st.text_input("SN", value=f"{len(df)+1:05d}")
            off_no = st.text_input("OFFER NO")
            name = st.text_input("NAME")
            gender = st.selectbox("GENDER", ["M", "F"])
            contact = st.text_input("CONTACT")
        with c2:
            doi = st.date_input("DATE OF ISSUE")
            pod = st.date_input("PAYMENT DATE")
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("INTEREST RATE (%)", value=3)
        
        if st.form_submit_button("✅ Save to Registry"):
            interest_amt = amt * (rate/100)
            to_pay = amt + interest_amt
            new_row = pd.DataFrame([{
                'SN': sn, 'OFFER_NO': off_no, 'NAME': name, 'GENDER': gender,
                'CONTACT': contact, 'DATE_OF_ISSUE': doi, 'PAYMENT_DATE': pod,
                'LOAN_AMOUNT': amt, 'INTEREST_RATE': f"{rate}%", 'INTEREST': interest_amt,
                'AMOUNT_TO_BE_PAID': to_pay, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': to_pay,
                'STATUS': 'BCE' # Matches your screenshot
            }])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Loan recorded!"); st.rerun()
