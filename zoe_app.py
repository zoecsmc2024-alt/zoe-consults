import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. EDITABLE ICON & APP SETTINGS ---
# Change the URL below to change your app's logo!
# This looks for the file you uploaded to GitHub
LOGO_URL = "logo.png"

st.set_page_config(page_title="ZoeLend IQ", page_icon="🏦", layout="wide")

# Custom CSS for Visibility and Logout Button
st.markdown(f"""
    <style>
    .main {{ background-color: #f5f7f9; }}
    
    /* Sidebar Background */
    [data-testid="stSidebar"] {{
        background-color: #1e293b;
    }}
    
    /* Sidebar Text visibility */
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label p {{
        color: white !important;
    }}
    
    /* NEW: High-Visibility Logout Button */
    .stButton > button {{
        width: 100%;
        border-radius: 5px;
    }}
    
    [data-testid="stSidebar"] .stButton > button {{
        background-color: transparent;
        color: white !important;
        border: 2px solid white !important;
        font-weight: bold;
        margin-top: 20px;
    }}
    
    [data-testid="stSidebar"] .stButton > button:hover {{
        background-color: white !important;
        color: #1e293b !important;
    }}

    .stMetric {{
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }}
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
        except: return create_empty_df()
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
    st.info("Zoe Consults: Secured Portal")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Secure Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Access Denied.")
    st.stop()

# --- 4. APP INTERFACE ---
df = load_data()
if not df.empty:
    df['Status'] = df.apply(auto_status, axis=1)
    df['Current_Balance'] = df.apply(calculate_live_balance, axis=1)

with st.sidebar:
    # This uses the LOGIC from the top of the script
    st.image(LOGO_URL, width=120)
    st.title("Zoe Consults")
    st.markdown("---")
    
    choice = st.radio("Menu Navigation", ["📊 Daily Report", "👤 New Customer", "💰 Record Payment", "✉️ Letters"])
    
    st.markdown("---")
    # Visually distinct logout button
    if st.button("🔓 LOGOUT SYSTEM"):
        del st.session_state["password_correct"]
        st.rerun()
    st.caption("v2.3 | Kampala, UG")

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("Financial Portfolio Overview")
    if df.empty:
        st.info("No active loans found.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Principal", f"UGX {df['Principal_UGX'].sum():,.0f}")
        c2.metric("Portfolio Value", f"UGX {df['Current_Balance'].sum():,.0f}")
        c3.metric("Active Clients", len(df[df['Status'] == 'Active']))

        st.markdown("---")
        search = st.text_input("🔍 Quick Search")
        display_df = df[df['Name'].str.contains(search, case=False)] if search else df
        st.dataframe(display_df, use_container_width=True, hide_index=True)

elif choice == "👤 New Customer":
    st.title("Onboard New Customer")
    with st.form("add_form", clear_on_submit=True):
        n = st.text_input("Full Name")
        a = st.number_input("Amount (UGX)", min_value=1000, step=10000)
        r = st.number_input("Annual Interest (e.g. 0.25 for 25%)", value=0.15)
        if st.form_submit_button("Create Loan"):
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            now = datetime.datetime.now()
            new_row = pd.DataFrame([{'Customer_ID': int(new_id), 'Name': n, 'Principal_UGX': float(a), 'Annual_Rate': float(r), 'Start_Date': now, 'Last_Payment_Date': now, 'Status': 'Active'}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success(f"Loan Created for {n}")

elif choice == "💰 Record Payment":
    st.title("Payment Processing")
    cid = st.number_input("Customer ID", min_value=101)
    p_amt = st.number_input("Amount (UGX)", min_value=100)
    if st.button("Submit Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Principal_UGX'] -= p_amt
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            save_data(df)
            st.success("Payment saved!"); st.rerun()
        else: st.error("ID not found.")

elif choice == "✉️ Letters":
    st.title("Letter Gen")
    if not df.empty:
        name = st.selectbox("Select Client", df['Name'].tolist())
        r = df[df['Name'] == name].iloc[0]
        st.text_area("Preview", f"Dear {r['Name']},\nYour balance is UGX {r['Current_Balance']:,.0f}.", height=200)
