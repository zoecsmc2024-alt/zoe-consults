import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. CONFIG & UPDATED THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .box-card {
        background: white; border: 1px solid #e2e8f0;
        padding: 20px; border-radius: 8px; text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .box-title { color: #64748b; font-size: 0.85em; text-transform: uppercase; margin-bottom: 8px; font-weight: 600; }
    .box-value { color: #0f172a; font-size: 1.6em; font-weight: 800; }
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 4px 4px 0 0; padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
PAYMENT_FILE = "repayments_log.csv"

def init_db():
    # Existing Loan DB init...
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED']).to_csv(DB_FILE, index=False)
    
    # NEW: Repayment DB init
    if not os.path.exists(PAYMENT_FILE):
        pd.DataFrame(columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'RECEIPT_NO']).to_csv(PAYMENT_FILE, index=False)
        df.to_csv(DB_FILE, index=False)

@st.cache_data(show_spinner=False)
def load_data():
    if not os.path.exists(DB_FILE):
        init_db()
    try:
        data = pd.read_csv(DB_FILE)
        # Ensure numeric types so math doesn't break
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except Exception:
        return pd.DataFrame()

# Initial Load
df = load_data()

# --- 3. ERP NAVIGATION HEADER ---
st.markdown("""
    <div style="background-color: #0f172a; padding: 12px 25px; display: flex; justify-content: space-between; align-items: center; color: white; border-bottom: 3px solid #00acc1; margin-bottom: 20px;">
        <div style="display: flex; gap: 20px; align-items: center;">
            <span style="opacity: 0.8; font-size: 0.9em;">👤 Evans Ahuura</span>
            <b style="font-size: 1.4em; letter-spacing: 0.5px;">Zoe Consults</b>
            <span style="background: #00acc1; padding: 2px 12px; border-radius: 20px; font-size: 0.75em; font-weight: 700;">BRANCH #1</span>
        </div>
        <div style="display: flex; gap: 20px; font-size: 0.85em; opacity: 0.9;">
            <span>⚙️ Admin</span><span>🔗 Settings</span><span style="color: #fbbf24;">❓ Help</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 4. TOP CONTROLS (FULL FIX) ---
col_search, col_btn, col_dl = st.columns([3, 1, 0.5])

with col_search:
    search = st.text_input("", placeholder="🔍 Search borrower by name...", label_visibility="collapsed")

with col_btn:
    with st.popover("➕ New Loan Entry", use_container_width=True):
        # We use a unique key for the form to prevent conflicts
        with st.form("add_new_loan_form", clear_on_submit=True):
            st.markdown("### Client Details")
            f_name = st.text_input("Customer Name")
            f_amount = st.number_input("Principal Amount (UGX)", min_value=0, step=50000)
            f_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.5)
            
            # The button is the gatekeeper
            submitted = st.form_submit_button("Confirm & Save")
            
            if submitted:
                if f_name:
                    # new_data is created ONLY when button is clicked
                    new_data = pd.DataFrame([{
                        'SN': len(df) + 1,
                        'CUSTOMER_NAME': f_name,
                        'LOAN_AMOUNT': f_amount,
                        'AMOUNT_PAID': 0,
                        'OUTSTANDING_AMOUNT': f_amount,
                        'INTEREST_RATE': f_rate,
                        'DATE_ISSUED': datetime.now().strftime("%Y-%m-%d")
                    }])
                    
                    # Saving happens ONLY inside this specific 'if' block
                    new_data.to_csv(DB_FILE, mode='a', header=False, index=False)
                    
                    st.success(f"Successfully added {f_name}!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Please provide a name.")

with col_dl:
    # This just provides a download of whatever is currently in 'df'
    if not df.empty:
        csv_output = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥", data=csv_output, file_name="Zoe_Lend_Data.csv", mime="text/csv")

# --- 5. DASHBOARD TABS ---
menu_tabs = st.tabs(["📊 Overview", "👥 Borrowers List", "💰 Repayments", "📅 Calendar"])

with menu_tabs[2]:
    st.subheader("Record New Payment")
    
    # 1. Payment Form
    with st.expander("➕ Log a Transaction", expanded=True):
        with st.form("repayment_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                # Get list of names from our main DB for the dropdown
                names = df['CUSTOMER_NAME'].tolist() if not df.empty else ["No Customers"]
                p_name = st.selectbox("Select Borrower", options=names)
            with col_b:
                p_amount = st.number_input("Amount Paid (UGX)", min_value=0, step=5000)
            
            p_date = st.date_input("Payment Date")
            p_receipt = st.text_input("Receipt / Reference Number")

            if st.form_submit_button("Submit Payment"):
                # Save to Repayment Log
                new_payment = pd.DataFrame([[p_date, p_name, p_amount, p_receipt]], 
                                         columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'RECEIPT_NO'])
                new_payment.to_csv(PAYMENT_FILE, mode='a', header=False, index=False)

                # UPDATE MAIN DATABASE: Add this amount to the total paid for this customer
                df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amount
                df['OUTSTANDING_AMOUNT'] = df['LOAN_AMOUNT'] - df['AMOUNT_PAID']
                df.to_csv(DB_FILE, index=False)

                st.success(f"Recorded UGX {p_amount:,.0f} for {p_name}")
                st.cache_data.clear()
                st.rerun()

    # 2. History Table
    st.write("---")
    st.subheader("Payment History Log")
    if os.path.exists(PAYMENT_FILE):
        pay_df = pd.read_csv(PAYMENT_FILE)
        st.dataframe(pay_df.sort_index(ascending=False), use_container_width=True) # Newest payments on top
    else:
        st.info("No payment history available yet.")
