import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. CONFIGURATION & DATABASE SETUP ---
FILE_NAME = 'zoe_consults_loans.csv'

def load_data():
    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
        df['Start_Date'] = pd.to_datetime(df['Start_Date'])
        df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
        return df
    else:
        columns = ['Customer_ID', 'Name', 'Principal_USD', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status']
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
    balance = row['Principal_USD'] * (1 + monthly_rate) ** total_months
    return round(balance, 2)

def auto_update_status(row):
    if row['Status'] == 'Paid Off' or row['Principal_USD'] <= 0:
        return 'Paid Off'
    today = datetime.datetime.now()
    days_since_payment = (today - row['Last_Payment_Date']).days
    if days_since_payment > 60:
        return 'Dormant'
    return 'Active'

# --- 2. LOGIN SECURITY ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 ZoeLend IQ Secure Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Login"):
            if st.session_state["username"] == "admin" and st.session_state["password"] == "zoe2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Username or password incorrect")
        return False
    return True

# --- 3. MAIN APP INTERFACE ---
if check_password():
    st.set_page_config(page_title="ZoeLend IQ", layout="wide")
    df = load_data()

    if not df.empty:
        df['Status'] = df.apply(auto_update_status, axis=1)
        df['Current_Balance'] = df.apply(calculate_live_balance, axis=1)

    st.sidebar.title("Zoe Consults Menu")
    choice = st.sidebar.selectbox("Navigation", ["Daily Report", "Add New Customer", "Record Payment", "Welcome Letter", "Help"])

    if choice == "Daily Report":
        st.title("📊 Daily Portfolio Report")
        search_query = st.text_input("🔍 Search for a customer by name", "")
        
        display_df = df[df['Name'].str.contains(search_query, case=False, na=False)] if search_query else df
        
        if df.empty:
            st.info("No active loans found. Start by adding a customer!")
        else:
            total_principal = df['Principal_UGX'].sum()
            total_balance = df['Current_Balance'].sum()
            next_month_est = (df['Current_Balance'] * (df['Annual_Rate'] / 12)).sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Principal Out", f"${total_principal:,.2f}")
            c2.metric("Total Portfolio Value", f"${total_balance:,.2f}")
            c3.metric("Expected Interest (Mo)", f"${next_month_est:,.2f}")

            st.write("### Loan Registry")
            st.dataframe(display_df.style.format({"Annual_Rate": "{:.2%}"}))
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Report as CSV", data=csv, file_name=f"Zoe_Report_{datetime.date.today()}.csv", mime='text/csv')

    elif choice == "Add New Customer":
        st.title("👤 New Customer Onboarding")
        with st.form("add_form"):
            name = st.text_input("Customer Full Name")
            amount = st.number_input("Principal Loan Amount (UGX)", min_value=10.0)
            rate = st.number_input("Annual Interest Rate (e.g., 0.15 for 15%)", min_value=10.0, max_value=30.0, format="%.2f")
            submitted = st.form_submit_button("Create Loan")
            
            if submitted:
                new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
                today = datetime.datetime.now()
                new_data = {
                    'Customer_ID': new_id, 'Name': name, 'Principal_UGX': amount,
                    'Annual_Rate': rate, 'Start_Date': today, 
                    'Last_Payment_Date': today, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(df)
                st.success(f"Successfully added {name} (ID: {new_id})")

    elif choice == "Record Payment":
        st.title("💰 Record a Payment")
        cust_id = st.number_input("Enter Customer ID", min_value=101)
        pay_amount = st.number_input("Payment Amount (UGX)", min_value=1.0)
        
        if st.button("Apply Payment"):
            idx = df[df['Customer_ID'] == cust_id].index
            if not idx.empty:
                df.at[idx[0], 'Principal_UGX'] -= pay_amount
                df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
                if df.at[idx[0], 'Principal_UGX'] <= 0:
                    df.at[idx[0], 'Status'] = 'Paid Off'
                save_data(df)
                st.success(f"Payment recorded for ID {cust_id}!")
            else:
                st.error("Customer ID not found.")

    elif choice == "Welcome Letter":
        st.title("✉️ Welcome Letter Generator")
        if not df.empty:
            target = st.selectbox("Select Customer", df['Name'].tolist())
            row = df[df['Name'] == target].iloc[0]
            letter = f"Dear {row['Name']},\nYour loan of ${row['Principal_UGX']:,.2f} is approved at {row['Annual_Rate']*100}% interest."
            st.text_area("Copy Letter Below:", letter, height=200)

    elif choice == "Help":
        st.title("❓ Help Guide")
        st.markdown("Interest compounds monthly. Status flips to 'Dormant' after 60 days of no payment.")
