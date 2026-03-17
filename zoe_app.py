import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import base64

# --- 0. SECURITY GATE ---
def check_password():
    def login_clicked():
        if st.session_state["user_input"] == "admin" and st.session_state["pass_input"] == "Zoe2026":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("## 🔐 ZoeLend IQ Pro Login")
        st.text_input("Username", key="user_input")
        st.text_input("Password", type="password", key="pass_input")
        st.button("Login", on_click=login_clicked)
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Invalid Username or Password")
        return False
    return True

if not check_password():
    st.stop()

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background: #f8fafc; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- DATA ENGINE (Self-Healing) ---
DB_FILE = "zoe_database.csv"
PAYMENT_FILE = "repayments_log.csv"
COLLATERAL_FILE = "collateral_log.csv"

def init_db():
    # 1. Initialize Main DB
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'INTEREST_RATE', 'DATE_ISSUED']).to_csv(DB_FILE, index=False)
    
    # 2. Initialize Payments
    if not os.path.exists(PAYMENT_FILE):
        pd.DataFrame(columns=['DATE', 'NAME', 'AMOUNT', 'REF']).to_csv(PAYMENT_FILE, index=False)
    
    # 3. Initialize Collateral with the CORRECT headers
    # If the file exists but is wrong (missing 'VAL'), we DELETE and FIX it automatically
    if os.path.exists(COLLATERAL_FILE):
        temp_df = pd.read_csv(COLLATERAL_FILE)
        if 'VAL' not in temp_df.columns:
            os.remove(COLLATERAL_FILE)
    
    if not os.path.exists(COLLATERAL_FILE):
        pd.DataFrame(columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS']).to_csv(COLLATERAL_FILE, index=False)

init_db() # Run the fix immediately

# --- RE-LOAD DATA ---
@st.cache_data
def load_collateral():
    return pd.read_csv(COLLATERAL_FILE)

# --- THE COLLATERAL TAB VIEW ---
# (Inside your menu_tabs[3] section)
with st.container():
    st.subheader("📑 Collateral Management")
    
    # Manual Reset Button just in case
    if st.button("🚨 Emergency Repair Collateral File"):
        if os.path.exists(COLLATERAL_FILE):
            os.remove(COLLATERAL_FILE)
        st.rerun()

    c_df = load_collateral()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        with st.form("new_collat"):
            # Use a dummy list if df is empty to prevent errors
            loan_ids = [1] if 'df' not in locals() or df.empty else df['SN'].tolist()
            l_id = st.selectbox("Loan ID", loan_ids)
            c_type = st.selectbox("Type", ["Logbook", "Title", "Other"])
            c_val = st.number_input("Value (UGX)", min_value=0)
            c_desc = st.text_input("Description")
            
            if st.form_submit_button("Save"):
                # Logic to get name
                name = "Unknown" 
                if 'df' in locals() and not df.empty:
                    name = df[df['SN'] == l_id]['CUSTOMER_NAME'].values[0]
                
                new_data = pd.DataFrame([[l_id, name, c_type, c_desc, c_val, "Held"]], 
                                     columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS'])
                new_data.to_csv(COLLATERAL_FILE, mode='a', header=False, index=False)
                st.cache_data.clear()
                st.success("Saved!")
                st.rerun()

    with col2:
        st.write("Current Records:")
        st.dataframe(c_df, use_container_width=True, hide_index=True)
