import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# --- 2. THE GOOGLE SHEETS CONNECTION ---
# This replaces the CSV and makes memory permanent
url = "https://docs.google.com/spreadsheets/d/1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=url, worksheet="Loans")

def save_data(df):
    conn.update(spreadsheet=url, worksheet="Loans", data=df)
    st.cache_data.clear()

# --- 3. DATA LOADING ---
df = load_data()

# --- 4. APP LOGIC ---
st.sidebar.title("Zoe Consults")
choice = st.sidebar.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])

if choice == "📊 Daily Report":
    st.title("📊 Permanent Portfolio Registry")
    if df.empty:
        st.info("No data in Google Sheets.")
    else:
        # Spreadsheet styling
        st.table(df[['SN', 'NAME', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']].style.format({"LOAN_AMOUNT": "{:,.0f}"}))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Issue")
    with st.form("onboard"):
        name = st.text_input("NAME")
        amt = st.number_input("LOAN AMOUNT", min_value=1000)
        rate = st.number_input("MONTHLY RATE (%)", value=3)
        if st.form_submit_button("✅ Save to Google Sheets"):
            new_row = pd.DataFrame([{
                'SN': f"{len(df)+1:05d}", 'NAME': name, 'LOAN_AMOUNT': amt, 
                'OUTSTANDING_AMOUNT': amt + (amt*(rate/100)), 'STATUS': 'Active'
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_data(updated_df)
            st.success("Data synced to Google Drive!")
            st.rerun()

elif choice == "📄 Client Report":
    st.title("📄 Dynamic Ledger")
    # ... (Rest of your ledger logic here)
