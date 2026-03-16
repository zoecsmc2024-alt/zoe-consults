import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    th { background-color: #00acee !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOCAL DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    # Create the structure if file doesn't exist
    return pd.DataFrame(columns=['SN','NAME','DATE_OF_ISSUE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Load data at start
df = load_data()

# --- 3. NAVIGATION ---
with st.sidebar:
    st.title("Zoe Consults")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    # Added a handy download button so you can always get your data
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel/CSV", data=csv, file_name="zoe_loans.csv", mime="text/csv")

# --- 4. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Loan Portfolio")
    if df.empty:
        st.info("The portfolio is currently empty.")
    else:
        st.table(df)

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Issue")
    with st.form("onboard_form"):
        name = st.text_input("NAME")
        amt = st.number_input("LOAN AMOUNT", min_value=1000)
        rate = st.number_input("MONTHLY RATE (%)", value=3)
        
        if st.form_submit_button("✅ Save Record"):
            new_row = pd.DataFrame([{
                'SN': str(len(df) + 1).zfill(5),
                'NAME': name,
                'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'),
                'LOAN_AMOUNT': amt,
                'INTEREST_RATE': rate,
                'AMOUNT_PAID': 0,
                'OUTSTANDING_AMOUNT': amt + (amt * (rate/100)),
                'STATUS': 'Active'
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success(f"Successfully saved {name} to the database!")
            st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn_input = st.text_input("Enter SN (e.g. 00001)")
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Submit"):
            df['SN'] = df['SN'].astype(str)
            idx = df[df['SN'] == sn_input.strip()].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                save_data(df)
                st.success("Payment recorded!"); st.rerun()
            else: st.error("SN not found.")
