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

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"
PAYMENT_FILE = "repayments_log.csv"
COLLATERAL_FILE = "collateral_log.csv"

def init_db():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'INTEREST_RATE', 'DATE_ISSUED']).to_csv(DB_FILE, index=False)
    if not os.path.exists(PAYMENT_FILE):
        pd.DataFrame(columns=['DATE', 'NAME', 'AMOUNT', 'REF']).to_csv(PAYMENT_FILE, index=False)
    if not os.path.exists(COLLATERAL_FILE):
        pd.DataFrame(columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS']).to_csv(COLLATERAL_FILE, index=False)

@st.cache_data(show_spinner=False)
def load_data():
    init_db()
    data = pd.read_csv(DB_FILE)
    if not data.empty:
        # Standardize types to prevent math errors
        data['LOAN_AMOUNT'] = pd.to_numeric(data['LOAN_AMOUNT'], errors='coerce').fillna(0)
        data['AMOUNT_PAID'] = pd.to_numeric(data['AMOUNT_PAID'], errors='coerce').fillna(0)
        data['INTEREST_RATE'] = pd.to_numeric(data['INTEREST_RATE'], errors='coerce').fillna(0)
        # Dynamic calculation of total debt vs paid
        data['INT_AMT'] = (data['LOAN_AMOUNT'] * data['INTEREST_RATE']) / 100
        data['TOTAL_DUE'] = data['LOAN_AMOUNT'] + data['INT_AMT']
        data['OUTSTANDING_AMOUNT'] = data['TOTAL_DUE'] - data['AMOUNT_PAID']
    return data

df = load_data()

# --- 3. BRANDED HEADER ---
if 'custom_logo_b64' not in st.session_state:
    st.session_state['custom_logo_b64'] = None

logo_display = f'<img src="data:image/png;base64,{st.session_state["custom_logo_b64"]}" style="height: 40px; border-radius: 5px;">' if st.session_state['custom_logo_b64'] else '<img src="https://img.icons8.com/fluency/96/money-bag-euro.png" style="height: 40px;">'

header_html = f"""
    <div style="background-color: #0f172a; padding: 12px 25px; display: flex; justify-content: space-between; align-items: center; color: white; border-radius: 8px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 15px;">
            {logo_display}
            <div style="line-height: 1.1;">
                <b style="font-size: 1.2em;">Zoe Consults</b><br>
                <span style="font-size: 0.7em; opacity: 0.6;">Evans Ahuura | Admin</span>
            </div>
        </div>
        <div style="font-size: 0.8em; opacity: 0.4;">{datetime.now().strftime('%d %b %Y')}</div>
    </div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# --- 4. ACTION TOOLBAR ---
c_search, c_new, c_set, c_logout = st.columns([4, 0.5, 0.5, 0.5])

with c_search:
    search_query = st.text_input("", placeholder="🔍 Search borrower name...", label_visibility="collapsed")

with c_new:
    with st.popover("➕", help="New Loan"):
        st.subheader("📝 New Loan")
        with st.form("new_loan_form"):
            n_name = st.text_input("Customer Name")
            n_amt = st.number_input("Principal (UGX)", min_value=0, step=50000)
            n_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.5, value=10.0)
            n_date = st.date_input("Date Issued", value=datetime.now())
            if st.form_submit_button("Save Loan"):
                new_sn = df['SN'].max() + 1 if not df.empty else 1
                new_row = pd.DataFrame([[new_sn, n_name, n_amt, 0, n_rate, n_date]], 
                                     columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'INTEREST_RATE', 'DATE_ISSUED'])
                new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                st.cache_data.clear()
                st.rerun()

with c_set:
    with st.popover("⚙️"):
        new_file = st.file_uploader("Update Logo", type=["png", "jpg"])
        if new_file:
            st.session_state['custom_logo_b64'] = base64.b64encode(new_file.getvalue()).decode()
            st.rerun()
        if st.button("Reset Brand"):
            st.session_state['custom_logo_b64'] = None
            st.rerun()

with c_logout:
    if st.button("🚪"):
        st.session_state["password_correct"] = False
        st.rerun()

# --- 5. TABS ---
menu_tabs = st.tabs(["📊 Overview", "👥 Borrowers", "💰 Payments", "📑 Collateral", "📅 Schedule"])

# Filter logic for search
filtered_df = df[df['CUSTOMER_NAME'].str.contains(search_query, case=False)] if not df.empty else df

with menu_tabs[0]:
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Borrowers", len(df))
        c2.metric("Total Principal", f"UGX {df['LOAN_AMOUNT'].sum():,.00f}")
        c3.metric("Collected", f"UGX {df['AMOUNT_PAID'].sum():,.00f}")
        c4.metric("Realized Profit", f"UGX {(df['AMOUNT_PAID'] - df['LOAN_AMOUNT']).clip(lower=0).sum():,.00f}")
        
        st.subheader("Portfolio Health")
        st.dataframe(filtered_df[['SN', 'CUSTOMER_NAME', 'TOTAL_DUE', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'DATE_ISSUED']], 
                     use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")

with menu_tabs[1]:
    st.subheader("Detailed Records")
    st.dataframe(filtered_df, column_config={
        "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
        "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d"),
    }, use_container_width=True, hide_index=True)

with menu_tabs[2]:
    st.subheader("Record Payment")
    if not df.empty:
        with st.form("payment_form"):
            p_name = st.selectbox("Select Borrower", options=df[df['OUTSTANDING_AMOUNT'] > 0]['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount Paid", min_value=0)
            p_ref = st.text_input("Reference/Receipt #")
            if st.form_submit_button("Post Payment"):
                # Update Log
                pd.DataFrame([[datetime.now().date(), p_name, p_amt, p_ref]], 
                           columns=['DATE', 'NAME', 'AMOUNT', 'REF']).to_csv(PAYMENT_FILE, mode='a', header=False, index=False)
                # Update Master
                master = pd.read_csv(DB_FILE)
                idx = master[master['CUSTOMER_NAME'] == p_name].index[-1]
                master.at[idx, 'AMOUNT_PAID'] += p_amt
                master.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
                st.rerun()

with menu_tabs[4]:
    if not df.empty:
        df['DUE_DATE'] = pd.to_datetime(df['DATE_ISSUED']) + timedelta(days=30)
        overdue = df[(df['DUE_DATE'] < datetime.now()) & (df['OUTSTANDING_AMOUNT'] > 0)]
        st.error(f"Found {len(overdue)} Overdue Accounts")
        st.dataframe(overdue[['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT', 'DUE_DATE']], hide_index=True)
