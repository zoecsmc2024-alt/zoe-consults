import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
LOGO_URL = "logo.jpg" 
st.set_page_config(page_title="ZoeLend IQ Pro", page_icon="🏦", layout="wide")

# Custom CSS for light blue cells and Status colors
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: white !important; }
    
    /* Metric Card Styling */
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
    
    /* Sidebar Button styling */
    [data-testid="stSidebar"] .stButton > button { background-color: transparent; color: white !important; border: 2px solid white !important; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINES ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['Start_Date'] = pd.to_datetime(df['Start_Date'])
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Phone', 'NIN', 'Address', 'Next_of_Kin', 'Employer', 'Principal_UGX', 'Annual_Rate', 'Duration_Months', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def auto_status(row):
    # Logic for Active vs Dormant
    today = datetime.datetime.now()
    last_pay = pd.to_datetime(row['Last_Payment_Date'])
    days = (today - last_pay).days
    return 'Dormant' if days > 60 else 'Active'

# --- 3. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Secure Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 4. APP INTERFACE ---
df = load_data()
if not df.empty:
    df['Status'] = df.apply(auto_status, axis=1)

with st.sidebar:
    if os.path.exists(LOGO_URL): st.image(LOGO_URL, width=120)
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Client Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Financial Portfolio & Registry")
    
    if df.empty:
        st.info("No data found.")
    else:
        # Table Styling Logic
        def color_status(val):
            color = '#10b981' if val == 'Active' else '#ef4444' # Green for Active, Red for Dormant
            return f'color: {color}; font-weight: bold'

        # Apply Light Blue to first two columns and Status colors
        styled_df = df[['Customer_ID', 'Name', 'Phone', 'Principal_UGX', 'Status']].style \
            .set_properties(**{'background-color': '#e0f2fe'}, subset=['Customer_ID', 'Name']) \
            .applymap(color_status, subset=['Status']) \
            .format({"Principal_UGX": "UGX {:,.0f}"})

        st.table(styled_df)

        st.markdown("---")
        # EDIT TRANSACTION SECTION
        with st.expander("🛠️ Edit an Existing Transaction"):
            edit_id = st.number_input("Enter Customer ID to Edit", min_value=101, step=1)
            if edit_id in df['Customer_ID'].values:
                idx = df[df['Customer_ID'] == edit_id].index[0]
                with st.form("edit_form"):
                    new_name = st.text_input("Edit Name", value=df.at[idx, 'Name'])
                    new_principal = st.number_input("Edit Principal (UGX)", value=float(df.at[idx, 'Principal_UGX']))
                    new_rate = st.number_input("Edit Annual Rate", value=float(df.at[idx, 'Annual_Rate']))
                    
                    if st.form_submit_button("Save Changes"):
                        df.at[idx, 'Name'] = new_name
                        df.at[idx, 'Principal_UGX'] = new_principal
                        df.at[idx, 'Annual_Rate'] = new_rate
                        save_data(df)
                        st.success(f"Record {edit_id} updated!")
                        st.rerun()
            else:
                st.caption("Enter a valid ID to unlock the edit form.")

elif choice == "👤 Client Onboarding":
    st.title("👤 New Client Onboarding")
    with st.form("kyc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n = st.text_input("Full Name")
            phone = st.text_input("Phone")
            nin = st.text_input("NIN")
        with col2:
            addr = st.text_input("Address")
            nok = st.text_input("Next of Kin")
            emp = st.text_input("Employer")
        
        st.markdown("---")
        a = st.number_input("Loan Principal (UGX)", min_value=1000)
        r = st.number_input("Annual Rate (e.g. 0.15)", value=0.15)
        d = st.number_input("Duration (Months)", min_value=1, value=6)
        
        if st.form_submit_button("✅ Register Client"):
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            now = datetime.datetime.now()
            new_row = pd.DataFrame([{'Customer_ID': int(new_id), 'Name': n, 'Phone': phone, 'NIN': nin, 'Address': addr, 'Next_of_Kin': nok, 'Employer': emp, 'Principal_UGX': float(a), 'Annual_Rate': float(r), 'Duration_Months': int(d), 'Start_Date': now, 'Last_Payment_Date': now, 'Status': 'Active'}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Client added!"); st.balloons()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    cid = st.number_input("Client ID", min_value=101)
    p_amt = st.number_input("Amount (UGX)", min_value=100)
    if st.button("Post Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            # Note: In a real system, you'd subtract from a 'Current_Balance' column here
            save_data(df); st.success("Payment Logged!"); st.rerun()
        else: st.error("ID not found.")

elif choice == "📄 Client Report":
    st.title("📄 Client Report")
    if not df.empty:
        client = st.selectbox("Select Client", df['Name'].unique())
        c = df[df['Name'] == client].iloc[0]
        st.write(f"### Statement for {c['Name']}")
        st.json(c.to_dict()) # Placeholder for a pretty layout
