import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. CONFIGURATION ---
FILE_NAME = 'zoe_consults_loans.csv'

def load_data():
    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        df['Start_Date'] = pd.to_datetime(df['Start_Date'])
        df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
        return df
    else:
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
    return round(balance, 0) # Rounding to nearest Shilling

def auto_update_status(row):
    if row['Status'] == 'Paid Off' or row['Principal_UGX'] <= 0:
        return 'Paid Off'
    today = datetime.datetime.now()
    days_since_payment = (today - row['Last_Payment_Date']).days
    return 'Dormant' if days_since_payment > 60 else 'Active'

# --- 2. LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 ZoeLend IQ Secure Login")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u == "admin" and p == "zoe2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Login Failed")
        return False
    return True

# --- 3. MAIN APP ---
if check_password():
    st.set_page_config(page_title="ZoeLend IQ", layout="wide")
    df = load_data()

    if not df.empty:
        # Standardize column name if you're switching from USD to UGX
        if 'Principal_USD' in df.columns:
            df = df.rename(columns={'Principal_USD': 'Principal_UGX'})
        df['Status'] = df.apply(auto_update_status, axis=1)
        df['Current_Balance'] = df.apply(calculate_live_balance, axis=1)

    st.sidebar.title("Zoe Consults Menu")
    choice = st.sidebar.selectbox("Navigation", ["Daily Report", "Add New Customer", "Record Payment", "Welcome Letter", "Help"])

    if choice == "Daily Report":
        st.title("📊 Daily Portfolio Report (UGX)")
        search = st.text_input("🔍 Search by name")
        display_df = df[df['Name'].str.contains(search, case=False, na=False)] if search else df
        
        if df.empty:
            st.info("No loans found.")
        else:
            c1, c2, c3 = st.columns(3)
            # Formatting as UGX with no decimals
            c1.metric("Total Principal", f"UGX {df['Principal_UGX'].sum():,.0f}")
            c2.metric("Portfolio Value", f"UGX {df['Current_Balance'].sum():,.0f}")
            c3.metric("Expected Mo. Interest", f"UGX {(df['Current_Balance'] * (df['Annual_Rate']/12)).sum():,.0f}")

            st.write("### Loan Registry")
            st.dataframe(display_df.style.format({
                "Principal_UGX": "UGX {:,.0f}",
                "Current_Balance": "UGX {:,.0f}",
                "Annual_Rate": "{:.1%}"
            }))
            st.download_button("📥 Export CSV", df.to_csv(index=False), "Zoe_Report.csv")

    elif choice == "Add New Customer":
        st.title("👤 New Loan (UGX)")
        with st.form("add"):
            name = st.text_input("Name")
            amt = st.number_input("Amount (UGX)", min_value=1000, step=10000)
            # Rate is now flexible (e.g. 0.1 for 10%)
            rate = st.number_input("Annual Interest Rate (decimal, e.g. 0.28 for 28%)", format="%.2f")
            if st.form_submit_button("Create Loan"):
                new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
                new_row = {'Customer_ID': new_id, 'Name': name, 'Principal_UGX': amt, 'Annual_Rate': rate, 
                           'Start_Date': datetime.datetime.now(), 'Last_Payment_Date': datetime.datetime.now(), 'Status': 'Active'}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df); st.success(f"Added {name}!"); st.rerun()

    elif choice == "Record Payment":
        st.title("💰 Record Payment")
        cid = st.number_input("Customer ID", min_value=101)
        p_amt = st.number_input("Amount (UGX)", min_value=500)
        if st.button("Apply"):
            idx = df[df['Customer_ID'] == cid].index
            if not idx.empty:
                df.at[idx[0], 'Principal_UGX'] -= p_amt
                df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
                save_data(df); st.success("Payment Saved!"); st.rerun()

    elif choice == "Welcome Letter":
        st.title("✉️ Letter Generator")
        if not df.empty:
            sel = st.selectbox("Select Customer", df['Name'].tolist())
            r = df[df['Name'] == sel].iloc[0]
            st.text_area("Letter:", f"Dear {r['Name']},\nLoan: UGX {r['Principal_UGX']:,.0f} @ {r['Annual_Rate']*100}% p.a.")

    elif choice == "Help":
        st.write("All values in UGX. Interest calculated monthly.")
