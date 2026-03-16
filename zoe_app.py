import streamlit as st
import pandas as pd
import os
import datetime

# --- 1. SETTINGS & THEMING ---
LOGO_URL = "logo.jpg" 
st.set_page_config(page_title="ZoeLend IQ Pro", page_icon="🏦", layout="wide")

# Corrected CSS: Specifically targets Sidebar text and main Table headers
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    
    /* SIDEBAR TEXT VISIBILITY */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
    }
    
    /* Force Sidebar labels and radio text to be WHITE */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }

    /* TABLE HEADER: Spreadsheet Blue (#00acee) */
    th {
        background-color: #00acee !important;
        color: white !important;
        text-align: center !important;
    }

    /* SideBar Button */
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent;
        color: white !important;
        border: 2px solid white !important;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINE ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['SN','OFFER_NO','NAME','GENDER','CONTACT','DATE_OF_ISSUE','PAYMENT_DATE','LOAN_AMOUNT','INTEREST_RATE','INTEREST','AMOUNT_TO_BE_PAID','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

# --- 3. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Secure Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

df = load_data()

# --- 4. SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_URL):
        st.image(LOGO_URL, width=120)
    else:
        st.header("🏦")
    
    st.title("Zoe Consults")
    st.markdown("---")
    
    # Navigation with Icons
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments"])
    
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()
    st.caption("v2.7 | Kampala, UG")

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Portfolio Registry")
    
    if df.empty:
        st.info("Registry is empty.")
    else:
        # Styles the rows to the Spreadsheet Orange (#ff9900)
        def style_rows(row):
            return ['background-color: #ff9900; color: black; font-weight: 500'] * len(row)

        st.table(df.style.apply(style_rows, axis=1).format({
            "LOAN_AMOUNT": "{:,.0f}",
            "INTEREST": "{:,.0f}",
            "AMOUNT_TO_BE_PAID": "{:,.0f}",
            "AMOUNT_PAID": "{:,.0f}",
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        }))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Disbursement")
    with st.form("new_loan_form", clear_on_submit=True):
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
                'STATUS': 'BCE'
            }])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Record Saved!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay_form"):
        cid = st.text_input("Enter SN or Name")
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Submit"):
            # Simplified for now: looks for the SN
            idx = df[df['SN'] == cid].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                save_data(df); st.success("Updated!"); st.rerun()
            else: st.error("Client not found.")
