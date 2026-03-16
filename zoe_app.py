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
        # Create a fresh database structure if none exists
        columns = ['Customer_ID', 'Name', 'Principal_USD', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status']
        return pd.DataFrame(columns=columns)

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def calculate_live_balance(row):
    if row['Status'] == 'Paid Off':
        return 0.0
    today = datetime.datetime.now()
    # Calculate months passed
    years_diff = today.year - row['Start_Date'].year
    months_diff = today.month - row['Start_Date'].month
    total_months = max(0, (years_diff * 12) + months_diff)
    
    # Compound interest formula: A = P(1 + r/n)^nt
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

    # Automatic Data Refresh
    if not df.empty:
        df['Status'] = df.apply(auto_update_status, axis=1)
        df['Current_Balance'] = df.apply(calculate_live_balance, axis=1)

    st.sidebar.title("Zoe Consults Menu")
    choice = st.sidebar.selectbox("Navigation", ["Daily Report", "Add New Customer", "Record Payment", "Welcome Letter", "Help"])

    if choice == "Daily Report":
        st.title("📊 Daily Portfolio Report")
if choice == "Daily Report":
        st.title("📊 Daily Portfolio Report")
        
        # --- NEW SEARCH BAR ---
        search_query = st.text_input("🔍 Search for a customer by name", "")
        
        if search_query:
            display_df = df[df['Name'].str.contains(search_query, case=False, na=False)]
        else:
            display_df = df
        
        if df.empty:
            st.info("No active loans found. Start by adding a customer!")
        else:
            # Stats (Still based on full database)
            total_principal = df['Principal_USD'].sum()
            total_balance = df['Current_Balance'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Principal Out", f"${total_principal:,.2f}")
            c2.metric("Total Portfolio Value", f"${total_balance:,.2f}")
            c3.metric("Filtered Results", f"{len(display_df)} Customers")

            st.write("### Loan Registry")
            # Show the filtered results
            st.dataframe(display_df.style.format({"Annual_Rate": "{:.2%}"}))
        if df.empty:
            st.info("No active loans found. Start by adding a customer!")
        else:
            # Metrics
            total_principal = df['Principal_USD'].sum()
            total_balance = df['Current_Balance'].sum()
            next_month_est = (df['Current_Balance'] * (df['Annual_Rate'] / 12)).sum()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Principal Out", f"${total_principal:,.2f}")
            c2.metric("Total Portfolio Value", f"${total_balance:,.2f}")
            c3.metric("Expected Interest (Mo)", f"${next_month_est:,.2f}")

            st.write("### Full Loan Registry")
            st.dataframe(df.style.format({"Annual_Rate": "{:.2%}"}))

            # Download Feature
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Report as CSV", data=csv, file_name=f"Zoe_Report_{datetime.date.today()}.csv", mime='text/csv')

    elif choice == "Add New Customer":
        st.title("👤 New Customer Onboarding")
        with st.form("add_form"):
            name = st.text_input("Customer Full Name")
            amount = st.number_input("Principal Loan Amount ($)", min_value=1.0)
            rate = st.number_input("Annual Interest Rate (e.g., 0.15 for 15%)", min_value=0.01, max_value=1.0, format="%.2f")
            submitted = st.form_submit_button("Create Loan")
            
            if submitted:
                new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
                today = datetime.datetime.now()
                new_data = {
                    'Customer_ID': new_id, 'Name': name, 'Principal_USD': amount,
                    'Annual_Rate': rate, 'Start_Date': today, 
                    'Last_Payment_Date': today, 'Status': 'Active'
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(df)
                st.success(f"Successfully added {name} (ID: {new_id})")

    elif choice == "Record Payment":
        st.title("💰 Record a Payment")
        cust_id = st.number_input("Enter Customer ID", min_value=101)
        pay_amount = st.number_input("Payment Amount ($)", min_value=1.0)
        
        if st.button("Apply Payment"):
            idx = df[df['Customer_ID'] == cust_id].index
            if not idx.empty:
                df.at[idx[0], 'Principal_USD'] -= pay_amount
                df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
                if df.at[idx[0], 'Principal_USD'] <= 0:
                    df.at[idx[0], 'Status'] = 'Paid Off'
                save_data(df)
                st.success(f"Payment of ${pay_amount} recorded for ID {cust_id}!")
            else:
                st.error("Customer ID not found.")

    elif choice == "Welcome Letter":
        st.title("✉️ Welcome Letter Generator")
        if not df.empty:
            target = st.selectbox("Select Customer", df['Name'].tolist())
            row = df[df['Name'] == target].iloc[0]
            
            letter = f"""
--------------------------------------------------
ZOE CONSULTS - OFFICIAL LOAN AGREEMENT
Date: {datetime.date.today()}

Dear {row['Name']},

Your loan has been approved. 
Principal: ${row['Principal_USD']:,.2f}
Interest Rate: {row['Annual_Rate']*100}% (Compounded Monthly)

To maintain 'Active' status, please ensure payments 
are made at least once every 60 days.

Regards,
Management, Zoe Consults
--------------------------------------------------
            """
            st.text_area("Copy Letter Below:", letter, height=300)
        else:
            st.warning("No customers available.")

    elif choice == "Help":
        st.title("❓ ZoeLend IQ Support & Instructions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📖 How to Manage Loans
            1. **Onboarding**: Use 'Add New Customer' to register a new loan. Use decimal points for rates (e.g., 0.1 for 10%).
            2. **Payments**: When a customer pays, enter their ID in 'Record Payment'. This reduces the principal and resets the dormancy timer.
            3. **Monitoring**: Check the 'Daily Report' every morning. If a customer is highlighted as **Dormant**, it means they haven't paid in 60+ days.
            4. **Data Safety**: The system saves automatically to the cloud. You can download a backup at any time using the 'Download' button.
            """)

        with col2:
            st.markdown("""
            ### 📞 Business Support
            **Administrative Contact:**
            - **Primary:** Zoe Consults Admin
            - **Emergency Technical Support:** [Your Name/Email]
            
            **System Policy:**
            - Interest compounds on the 1st of every month.
            - Loans marked as 'Paid Off' will no longer accrue interest.
            """)
            
        st.info("💡 **Pro Tip:** Use the search bar in the 'Daily Report' table to quickly find a specific customer by name.")