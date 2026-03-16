import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. CONFIGURATION ---
FILE_NAME = 'zoe_consults_loans.csv'

def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            # Ensure dates are correct
            df['Start_Date'] = pd.to_datetime(df['Start_Date'])
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
            return df
        except:
            return create_empty_df()
    else:
        return create_empty_df()

def create_empty_df():
    columns = ['Customer_ID', 'Name', 'Principal_UGX', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status']
    return pd.DataFrame(columns=columns)

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def calculate_live_balance(row):
    if row['Status'] == 'Paid Off':
        return 0.0
    today = datetime.datetime.now()
    years_diff = today.year - row['Start_Date'].year
    months_diff = today.month - row['Start_Date'].month
    total_months = max(0, (years_diff * 12) + months_diff)
    monthly_rate = row['Annual_Rate'] / 12
    balance = row['Principal_UGX'] * (1 + monthly_rate) ** total_months
    return round(balance, 0)

def auto_update_status(row):
    # Safety get to prevent crashes
    p = row.get('Principal_UGX', 0)
    s = row.get('Status', 'Active')
    if s == 'Paid Off' or p <= 0:
        return 'Paid Off'
    today = datetime.datetime.now()
    last_pay = pd.to_datetime(row['Last_Payment_Date'])
    days_since = (today - last_pay).days
    return 'Dormant' if days_since > 60 else 'Active'

# --- 2. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🔒 ZoeLend IQ Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Login failed")
    st.stop()

# --- 3. MAIN APP ---
st.set_page_config(page_title="ZoeLend IQ", layout="wide")
df = load_data()

# Data Processing
if not df.empty:
    if 'Principal_USD' in df.columns:
        df = df.rename(columns={'Principal_USD': 'Principal_UGX'})
    df['Status'] = df.apply(auto_update_status, axis=1)
    df['Current_Balance'] = df.apply(calculate_live_balance, axis=1)

st.sidebar.title("Zoe Consults Menu")
choice = st.sidebar.selectbox("Navigation", ["Daily Report", "Add New Customer", "Record Payment", "Welcome Letter"])

if choice == "Daily Report":
    st.title("📊 Daily Portfolio Report (UGX)")
    if df.empty:
        st.info("No loans found. Go to 'Add New Customer' to begin.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Total Principal", f"UGX {df['Principal_UGX'].sum():,.0f}")
        c2.metric("Portfolio Value", f"UGX {df['Current_Balance'].sum():,.0f}")
        
        search = st.text_input("🔍 Search Name")
        display_df = df[df['Name'].str.contains(search, case=False)] if search else df
        st.dataframe(display_df.style.format({"Principal_UGX": "UGX {:,.0f}", "Current_Balance": "UGX {:,.0f}", "Annual_Rate": "{:.1%}"}))

elif choice == "Add New Customer":
    st.title("👤 New Loan Entry")
    with st.form("new_loan_form", clear_on_submit=True):
        name = st.text_input("Customer Name")
        amt = st.number_input("Amount (UGX)", min_value=1000, step=10000)
        rate = st.number_input("Annual Interest Rate (e.g., 0.15 for 15%)", format="%.2f")
        submitted = st.form_submit_button("Create Loan")
        
        if submitted and name:
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            now = datetime.datetime.now()
            new_row = pd.DataFrame([{
                'Customer_ID': new_id, 'Name': name, 'Principal_UGX': amt, 
                'Annual_Rate': rate, 'Start_Date': now, 
                'Last_Payment_Date': now, 'Status': 'Active'
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success(f"Loan Created for {name}!")
            # No rerun inside form, it will refresh on next interaction

elif choice == "Record Payment":
    st.title("💰 Record Payment")
    cid = st.number_input("Customer ID", min_value=101)
    p_amt = st.number_input("Payment Amount (UGX)", min_value=100)
    if st.button("Apply Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Principal_UGX'] -= p_amt
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            save_data(df)
            st.success("Payment Recorded!")
            st.rerun()

elif choice == "Welcome Letter":
    st.title("✉️ Letter Generator")
    if not df.empty:
        sel = st.selectbox("Select Customer", df['Name'].tolist())
        r = df[df['Name'] == sel].iloc[0]
        st.text_area("Letter:", f"Dear {r['Name']},\nYour loan of UGX {r['Principal_UGX']:,.0f} is active.")
