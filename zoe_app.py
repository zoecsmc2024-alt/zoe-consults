import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    th { background-color: #00acee !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE PERMANENT CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # This reads the sheet using the 'spreadsheet' link in your Secrets
    return conn.read(ttl="0") 

def save_data(df_to_save):
    try:
        # We specify the worksheet name directly here for safety
        conn.update(worksheet="Loans", data=df_to_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ Could not save to Google Sheets: {e}")
        return False

# --- Inside your Onboarding page ---
if st.form_submit_button("✅ Save to Google Sheets"):
    # ... (Your new_row logic here) ...
    updated_df = pd.concat([df, new_row], ignore_index=True)
    
    if save_data(updated_df):
        st.success("Successfully saved to Google Drive!")
        st.rerun()
    else:
        st.warning("⚠️ Data was not saved. Please check your Google Sheet 'Share' settings.")

# --- 3. APP LOGIC ---
df = load_data()

with st.sidebar:
    st.title("Zoe Consults")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])

if choice == "📊 Daily Report":
    st.title("📊 Live Portfolio")
    if df.empty:
        st.info("No data found.")
    else:
        st.table(df)

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Issue")
    with st.form("onboarding_form"):
        name = st.text_input("NAME")
        amt = st.number_input("LOAN AMOUNT", min_value=1000)
        rate = st.number_input("MONTHLY RATE (%)", value=3)
        if st.form_submit_button("✅ Save to Google Sheets"):
            # Create the new row
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
            # Add to the existing data and save
            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_data(updated_df)
            st.success("Successfully saved to Google Drive!")
            st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn_to_find = st.text_input("Enter SN (e.g. 00001)")
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Submit"):
            # Ensure SNs are strings for matching
            df['SN'] = df['SN'].astype(str)
            idx = df[df['SN'] == sn_to_find].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                save_data(df)
                st.success("Payment recorded!"); st.rerun()
            else: st.error("SN not found.")
