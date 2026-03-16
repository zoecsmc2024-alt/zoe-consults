import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. APP CONFIG & PROFESSIONAL THEMING ---
st.set_page_config(page_title="ZoeLend IQ", page_icon="🏦", layout="wide")

# Custom CSS to force sidebar text visibility and banking aesthetic
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    
    /* Force ALL sidebar text and labels to be white */
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label p,
    [data-testid="stSidebar"] .st-expanderHeader p {
        color: white !important;
    }
    
    /* Style the metrics cards */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #1e293b;
    }
    
    .stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. DATABASE ENGINE ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['Start_Date'] = pd.to_datetime(df['Start_Date'])
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
            return df
        except:
            return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Principal_UGX', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def calculate_live_balance(row):
    if row['Status'] == 'Paid Off': return 0.0
    today = datetime.datetime.now()
    months_diff = (today.year - row['Start_Date'].year) * 12 + (today.month - row['Start_Date'].month)
    balance = row['Principal_UGX'] * (1 + (row['Annual_Rate'] / 12)) ** max(0, months_diff)
    return round(balance, 0)

def auto_status(row):
    if row['Status'] == 'Paid Off' or row['Principal_UGX'] <= 0: return 'Paid Off'
    days = (datetime.datetime.now() - pd.to_datetime(row['Last_Payment_Date'])).days
    return 'Dormant' if days > 60 else 'Active'

# --- 3. SECURITY GATE ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    st.info("Authorized Personnel Only - Zoe Consults")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Secure Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.stop()

# --- 4. DATA LOADING & SIDEBAR ---
df = load_data()

# Process data if it exists
if not df.empty:
    if 'Principal_USD' in df.columns:
        df = df.rename(columns={'Principal_USD': 'Principal_UGX'})
    df['Status'] = df.apply(auto_status, axis=1)
    df['Current_Balance'] = df.apply(calculate_live_balance, axis=1)

with st.sidebar:
    # Professional Logo
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135706.png", width=100)
    st.title("Zoe Consults")
    st.markdown("---")
    
    # Defining 'choice' correctly here so the rest of the app can see it
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 New Customer", "💰 Record Payment", "✉️ Letter Gen", "❓ Help"])
    
    st.markdown("---")
    if st.button("🔓 Logout"):
        del st.session_state["password_correct"]
        st.rerun()
    st.caption("v2.2 | Kampala, UG")

# --- 5. PAGE ROUTING ---

if choice == "📊 Daily Report":
    st.title("Financial Portfolio Overview")
    if df.empty:
        st.info("No active loans found. Start by adding a customer.")
    else:
        c1, c2, c3 = st.columns(3)
        total_p = df['Principal_UGX'].sum()
        total_b = df['Current_Balance'].sum()
        c1.metric("Total Principal", f"UGX {total_p:,.0f}")
        c2.metric("Portfolio Value", f"UGX {total_b:,.0f}")
        c3.metric("Active Clients", len(df[df['Status'] == 'Active']))

        st.markdown("---")
        search = st.text_input("🔍 Search Registry", placeholder="Type name...")
        display_df = df[df['Name'].str.contains(search, case=False)] if search else df
        
        st.dataframe(
            display_df,
            column_config={
                "Principal_UGX": st.column_config.NumberColumn("Principal", format="UGX %d"),
                "Current_Balance": st.column_config.NumberColumn("Live Balance", format="UGX %d"),
                "Annual_Rate": st.column_config.NumberColumn("Rate", format="%.1f%%"),
            },
            hide_index=True,
            use_container_width=True
        )
        st.download_button("💾 Download Ledger", df.to_csv(index=False), "Zoe_Master_List.csv")

elif choice == "👤 New Customer":
    st.title("Onboard New Customer")
    with st.form("add_form", clear_on_submit=True):
        n = st.text_input("Full Name")
        a = st.number_input("Principal Amount (UGX)", min_value=1000, step=10000)
        # Simplified rate input for the boss
        r = st.number_input("Annual Interest Rate (e.g. 0.25 for 25%)", value=0.15, format="%.2f")
        if st.form_submit_button("Confirm & Issue Loan"):
            if n:
                new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
                now = datetime.datetime.now()
                new_row = pd.DataFrame([{
                    'Customer_ID': int(new_id), 'Name': n, 'Principal_UGX': float(a), 
                    'Annual_Rate': float(r), 'Start_Date': now, 
                    'Last_Payment_Date': now, 'Status': 'Active'
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success(f"Successfully issued loan to {n}!")
            else: st.warning("Please enter a name.")

elif choice == "💰 Record Payment":
    st.title("Payment Processing")
    cid = st.number_input("Enter Customer ID", min_value=101)
    p_amt = st.number_input("Payment Amount (UGX)", min_value=500)
    if st.button("Submit Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Principal_UGX'] -= p_amt
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            if df.at[idx[0], 'Principal_UGX'] <= 0:
                df.at[idx[0], 'Status'] = 'Paid Off'
            save_data(df)
            st.success("Payment saved successfully!")
            st.rerun()
        else: st.error("Customer ID not found.")

elif choice == "✉️ Letter Gen":
    st.title("Document Generator")
    if not df.empty:
        name = st.selectbox("Select Client", df['Name'].tolist())
        r = df[df['Name'] == name].iloc[0]
        letter = f"Dear {r['Name']},\n\nYour current loan balance with Zoe Consults is UGX {r['Current_Balance']:,.0f}.\n\nIssued on: {r['Start_Date'].date()}"
        st.text_area("Agreement Summary", letter, height=200)
    else:
        st.info("Add a customer first to generate letters.")

elif choice == "❓ Help":
    st.title("System Guide")
    st.markdown("""
    * **New Loans:** Set the Annual Rate as a decimal (0.10 = 10%).
    * **Status:** Automatically turns 'Dormant' after 60 days of no payments.
    * **Security:** Use the Logout button before closing the tab.
    """)
