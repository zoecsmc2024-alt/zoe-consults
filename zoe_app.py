import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. SETTINGS & THEMING ---
LOGO_URL = "logo.jpg" 
st.set_page_config(page_title="ZoeLend IQ", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: white !important; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] .stButton > button { background-color: transparent; color: white !important; border: 2px solid white !important; font-weight: bold; width: 100%; }
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

# --- 3. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Denied")
    st.stop()

# --- 4. SIDEBAR (ONE MENU ONLY) ---
df = load_data()
with st.sidebar:
    # Safe Logo Check
    if os.path.exists(LOGO_URL):
        st.image(LOGO_URL, width=120)
    else:
        st.header("🏦")
        st.caption(f"Logo '{LOGO_URL}' missing on GitHub")
    
    st.title("Zoe Consults")
    st.markdown("---")
    
    # This is the ONLY radio menu in the entire app:
    choice = st.radio("Menu Navigation", ["📊 Daily Report", "👤 New Customer", "💰 Record Payment", "✉️ Letters"])
    
    st.markdown("---")
    if st.button("🔓 LOGOUT SYSTEM"):
        del st.session_state["password_correct"]
        st.rerun()
    st.caption("v2.5 | Kampala, UG")

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("Financial Portfolio Overview")
    if df.empty:
        st.info("No loans found.")
    else:
        # Standardize and Calculate
        if 'Principal_USD' in df.columns: df = df.rename(columns={'Principal_USD': 'Principal_UGX'})
        df['Current_Balance'] = df.apply(lambda r: round(r['Principal_UGX'] * (1 + (r['Annual_Rate']/12))**max(0,(datetime.datetime.now().year-pd.to_datetime(r['Start_Date']).year)*12+(datetime.datetime.now().month-pd.to_datetime(r['Start_Date']).month)),0), axis=1)
        
        c1, c2 = st.columns(2)
        c1.metric("Total Principal", f"UGX {df['Principal_UGX'].sum():,.0f}")
        c2.metric("Portfolio Value", f"UGX {df['Current_Balance'].sum():,.0f}")
        
        st.markdown("---")
        search = st.text_input("🔍 Quick Search")
        display_df = df[df['Name'].str.contains(search, case=False)] if search else df
        st.dataframe(display_df, use_container_width=True, hide_index=True)

elif choice == "👤 New Customer":
    st.title("Onboard New Customer")
    with st.form("add_new"):
        n = st.text_input("Name")
        a = st.number_input("Amount (UGX)", min_value=1000)
        r = st.number_input("Annual Interest (e.g. 0.25)", value=0.15)
        if st.form_submit_button("Create Loan"):
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            now = datetime.datetime.now()
            new_row = pd.DataFrame([{'Customer_ID': int(new_id), 'Name': n, 'Principal_UGX': float(a), 'Annual_Rate': float(r), 'Start_Date': now, 'Last_Payment_Date': now, 'Status': 'Active'}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Added!"); st.rerun()

elif choice == "💰 Record Payment":
    st.title("Payment Processing")
    cid = st.number_input("ID", min_value=101)
    p_amt = st.number_input("UGX", min_value=100)
    if st.button("Submit"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Principal_UGX'] -= p_amt
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            save_data(df); st.success("Saved!"); st.rerun()

elif choice == "✉️ Letters":
    st.title("Letter Gen")
    if not df.empty:
        name = st.selectbox("Select", df['Name'].tolist())
        st.text_area("Preview", f"Dear {name}, Balance: UGX {df[df['Name']==name]['Principal_UGX'].iloc[0]:,.0f}")
