import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# --- 1. MENU SETTINGS (The "No-Typo" Strategy) ---
MENU_DASHBOARD = "📊 Daily Report"
MENU_ONBOARDING = "👤 Onboarding"
MENU_PAYMENTS = "💰 Payments"
MENU_REPORT = "📄 Client Report"

st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
# Make sure your 'Secrets' are set in Streamlit Cloud Settings!
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
except Exception as e:
    st.error("Connection Error. Check your Streamlit Secrets.")
    df = pd.DataFrame()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Zoe Consults")
    choice = st.radio("Navigation", [MENU_DASHBOARD, MENU_ONBOARDING, MENU_PAYMENTS, MENU_REPORT])

# --- 4. THE PAGES ---

# PAGE A: DASHBOARD
if choice == MENU_DASHBOARD:
    st.title(MENU_DASHBOARD)
    if df.empty:
        st.info("No data found in Google Sheets.")
    else:
        st.table(df)

# PAGE B: ONBOARDING (This is where the fix is!)
elif choice == MENU_ONBOARDING:
    st.title(MENU_ONBOARDING)
    with st.form("onboarding_form"):
        name = st.text_input("NAME")
        amt = st.number_input("LOAN AMOUNT", min_value=1000)
        rate = st.number_input("MONTHLY RATE (%)", value=3)
        
        # The button is now INSIDE the form
        submit = st.form_submit_button("✅ Save to Google Sheets")
        
        if submit:
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
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Saved to Google Sheets!")
            st.rerun()

# PAGE C: PAYMENTS
elif choice == MENU_PAYMENTS:
    st.title(MENU_PAYMENTS)
    with st.form("payment_form"):
        sn_input = st.text_input("Enter SN (e.g. 00001)")
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        pay_submit = st.form_submit_button("Submit Payment")
        
        if pay_submit:
            df['SN'] = df['SN'].astype(str)
            idx = df[df['SN'] == sn_input.strip()].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                conn.update(data=df)
                st.success("Payment recorded!")
                st.rerun()
            else:
                st.error("SN not found.")

# PAGE D: CLIENT REPORT
elif choice == MENU_REPORT:
    st.title(MENU_REPORT)
    if not df.empty:
        name_list = df['NAME'].unique()
        selected_name = st.selectbox("Select Client", name_list)
        client_data = df[df['NAME'] == selected_name].iloc[0]
        st.write(f"**Outstanding Balance:** UGX {client_data['OUTSTANDING_AMOUNT']:,.0f}")
