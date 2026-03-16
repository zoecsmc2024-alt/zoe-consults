import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. SETTINGS & THEMING ---
# FIXED: Updated to .jpg to match your GitHub file
LOGO_URL = "logo.jpg" 

st.set_page_config(page_title="ZoeLend IQ", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: white !important; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] .stButton > button { background-color: transparent; color: white !important; border: 2px solid white !important; font-weight: bold; width: 100%; }
    /* Style for the Create Loan button to make it pop */
    .stForm submit_button { background-color: #1e293b; color: white; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINE ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['Start_Date'] = pd.to_datetime(df['Start_Date'])
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
            return df
        except: return pd.DataFrame(columns=['Customer_ID', 'Name', 'Principal_UGX', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status'])
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Principal_UGX', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

# --- 3. LOGIN GATE ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 4. DATA PROCESSING ---
df = load_data()
if not df.empty:
    if 'Principal_USD' in df.columns: 
        df = df.rename(columns={'Principal_USD': 'Principal_UGX'})
    
    # Live Balance Calculation
    def get_bal(r):
        today = datetime.datetime.now()
        start = pd.to_datetime(r['Start_Date'])
        months = (today.year - start.year) * 12 + (today.month - start.month)
        return round(r['Principal_UGX'] * (1 + (r['Annual_Rate']/12))**max(0, months), 0)
    
    df['Current_Balance'] = df.apply(get_bal, axis=1)

# --- 5. SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_URL):
        st.image(LOGO_URL, width=120)
    else:
        st.header("🏦")
        st.caption(f"Waiting for {LOGO_URL}...")
    
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("Menu Navigation", ["📊 Daily Report", "👤 New Customer", "💰 Record Payment", "✉️ Letters"])
    st.markdown("---")
    if st.button("🔓 LOGOUT SYSTEM"):
        del st.session_state["password_correct"]
        st.rerun()
    st.caption("v2.6 | Kampala, UG")

# --- 6. PAGES ---
if choice == "📊 Daily Report":
    st.title("Financial Portfolio Overview")
    if df.empty:
        st.info("No loans found.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Principal", f"UGX {df['Principal_UGX'].sum():,.0f}")
        c2.metric("Portfolio Value", f"UGX {df['Current_Balance'].sum():,.0f}")
        c3.metric("Growth", f"UGX {(df['Current_Balance'].sum() - df['Principal_UGX'].sum()):,.0f}")
        
        st.markdown("---")
        search = st.text_input("🔍 Quick Search")
        display_df = df[df['Name'].str.contains(search, case=False)] if search else df
        st.dataframe(display_df, use_container_width=True, hide_index=True)

elif choice == "👤 New Customer":
    st.title("Onboard New Customer")
    # Form key ensures the button stays active
    with st.form("add_customer_form", clear_on_submit=True):
        n = st.text_input("Full Name")
        a = st.number_input("Amount (UGX)", min_value=1000)
        r = st.number_input("Annual Interest (e.g. 0.15 for 15%)", value=0.15)
        submitted = st.form_submit_button("Create Loan")
        
        if submitted:
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
                st.success(f"Successfully added {n}!")
                st.balloons()
            else:
                st.warning("Please enter a name.")

elif choice == "💰 Record Payment":
    st.title("Payment Processing")
    cid = st.number_input("ID", min_value=101)
    p_amt = st.number_input("UGX", min_value=100)
    if st.button("Submit Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Principal_UGX'] -= p_amt
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            save_data(df)
            st.success("Payment Saved!")
            st.rerun()
        else: st.error("ID not found.")

elif choice == "✉️ Letters":
    st.title("Letter Gen")
    if not df.empty:
        name = st.selectbox("Select", df['Name'].tolist())
        st.text_area("Preview", f"Dear {name}, Balance: UGX {df[df['Name']==name]['Principal_UGX'].iloc[0]:,.0f}")
