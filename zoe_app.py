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

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"
PAYMENT_FILE = "repayments_log.csv"
COLLATERAL_FILE = "collateral_log.csv"

def init_db():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'INTEREST_RATE', 'DATE_ISSUED']).to_csv(DB_FILE, index=False)
    # ... (rest of your init_db code)

@st.cache_data(show_spinner=False)
def load_data():
    init_db()
    if os.path.exists(DB_FILE):
        data = pd.read_csv(DB_FILE)
        if not data.empty:
            # Ensure numbers are treated as numbers, not text
            data['LOAN_AMOUNT'] = pd.to_numeric(data['LOAN_AMOUNT'], errors='coerce').fillna(0)
            data['AMOUNT_PAID'] = pd.to_numeric(data['AMOUNT_PAID'], errors='coerce').fillna(0)
            data['INTEREST_RATE'] = pd.to_numeric(data['INTEREST_RATE'], errors='coerce').fillna(0)
            data['INT_AMT'] = (data['LOAN_AMOUNT'] * data['INTEREST_RATE']) / 100
            data['TOTAL_DUE'] = data['LOAN_AMOUNT'] + data['INT_AMT']
            data['OUTSTANDING_AMOUNT'] = data['TOTAL_DUE'] - data['AMOUNT_PAID']
        return data
    return pd.DataFrame()

# NOW you can call the function safely
df = load_data()
 

# --- 3. COLLATERAL TAB RE-FIXED ---
with menu_tabs[3]:
    st.subheader("📑 Collateral Management")
    
    if st.button("🚨 Emergency Repair Collateral File"):
        if os.path.exists(COLLATERAL_FILE):
            os.remove(COLLATERAL_FILE)
        st.rerun()

    # Load collateral specifically for this tab
    c_df = pd.read_csv(COLLATERAL_FILE)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Check if df exists and has data
        if df is not None and not df.empty:
            with st.form("new_collat", clear_on_submit=True):
                loan_ids = df['SN'].tolist()
                l_id = st.selectbox("Assign to Loan ID", loan_ids)
                
                # Auto-find the name
                cust_name = df[df['SN'] == l_id]['CUSTOMER_NAME'].values[0]
                st.info(f"Borrower: **{cust_name}**")

                c_type = st.selectbox("Category", ["Logbook", "Land Title", "Electronics", "Household", "Other"])
                c_val = st.number_input("Estimated Value (UGX)", min_value=0, step=50000)
                c_desc = st.text_area("Item Details")
                
                if st.form_submit_button("🔒 Save Security"):
                    new_data = pd.DataFrame([[l_id, cust_name, c_type, c_desc, c_val, "Held"]], 
                                         columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS'])
                    new_data.to_csv(COLLATERAL_FILE, mode='a', header=False, index=False)
                    st.cache_data.clear()
                    st.success("Saved!")
                    st.rerun()
        else:
            st.warning("⚠️ No borrowers found. Please add a loan in the 'Borrowers' tab first.")

    with col2:
        st.write("**Current Records:**")
        if not c_df.empty:
            st.dataframe(
                c_df, 
                column_config={
                    "VAL": st.column_config.NumberColumn("Value", format="UGX %,d")
                },
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("No items registered.")
