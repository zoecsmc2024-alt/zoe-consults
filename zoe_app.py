import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. SETTINGS ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# --- 2. THE GOOGLE SHEET LINK (TRANSFORMED) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg/export?format=csv"

def load_data():
    try:
        # This pulls the latest data from your Google Sheet every refresh
        df = pd.read_csv(SHEET_URL)
        # Clean up column names just in case there are spaces
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Connection Error: {e}")
        # Fallback to empty structure if link fails
        return pd.DataFrame(columns=['SN','OFFER_NO','NAME','GENDER','CONTACT','DATE_OF_ISSUE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS'])

# --- 3. DATA LOADING ---
df = load_data()

# --- 4. SIDEBAR ---
st.sidebar.title("Zoe Consults")
choice = st.sidebar.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])

# --- 5. DAILY REPORT PAGE ---
if choice == "📊 Daily Report":
    st.title("📊 Live Google Sheets Registry")
    if df.empty:
        st.warning("The Google Sheet is empty or not reachable.")
    else:
        st.table(df)

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
