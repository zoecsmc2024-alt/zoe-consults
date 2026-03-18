import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
import urllib.parse

# --- 0. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# --- 1. THE NAVY & TEAL STYLING ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #0b1425 !important;
        border-right: 3px solid #00a8b5;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    [data-testid="stSidebarContent"] {
        padding-top: 0rem !important;
    }
    /* Style for the sidebar logo */
    [data-testid="stSidebar"] img {
        display: block;
        margin: 5px auto !important;
        width: 80px !important;
        height: 80px !important;
        object-fit: cover;
        border-radius: 50% !important;
        border: 2px solid #00a8b5;
    }
    /* Action Buttons in Sidebar */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"
PAYMENT_FILE = "repayments_log.csv"
COLLATERAL_FILE = "collateral_log.csv"

def init_db():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED']).to_csv(DB_FILE, index=False)
    if not os.path.exists(PAYMENT_FILE):
        pd.DataFrame(columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF']).to_csv(PAYMENT_FILE, index=False)
    if not os.path.exists(COLLATERAL_FILE):
        pd.DataFrame(columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS']).to_csv(COLLATERAL_FILE, index=False)

init_db()
df = pd.read_csv(DB_FILE)

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown('<div style="margin-top: -30px;"></div>', unsafe_allow_html=True)
    
    # logo logic
    if 'custom_logo_b64' in st.session_state and st.session_state['custom_logo_b64']:
        st.markdown(f'<img src="data:image/png;base64,{st.session_state["custom_logo_b64"]}">', unsafe_allow_html=True)
    else:
        st.markdown('<div style="width:80px;height:80px;border-radius:50%;background-color:#1e293b;border:2px solid #00a8b5;margin:0 auto;display:flex;align-items:center;justify-content:center;color:white;font-size:30px;">💰</div>', unsafe_allow_html=True)
    
    st.markdown(f'<p style="text-align:center;color:white;margin-top:5px;"><b>Admin:</b> Evans Ahuura</p>', unsafe_allow_html=True)
    
    page = st.radio("Navigation", ["📊 Overview", "👥 Borrowers", "💰 Repayments", "📅 Calendar", "📑 Collateral", "📄 Client Ledger", "⚙️ Settings"])
    
    st.write("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# --- 4. THE ROOMS (Page Content) ---

if page == "📊 Overview":
    st.title("📈 Business Growth & Trends")
    if not df.empty:
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Principal", f"UGX {total_p:,.0f}")
        c2.metric("Total Collected", f"UGX {total_c:,.0f}")
        c3.metric("Outstanding", f"UGX {total_p - total_c:,.0f}")
        st.bar_chart(df.set_index('CUSTOMER_NAME')[['LOAN_AMOUNT', 'AMOUNT_PAID']])
    else:
        st.info("No data yet.")

elif page == "👥 Borrowers":
    st.title("👥 Active Loan Registry")
    # Search functionality
    search = st.text_input("🔍 Search Borrowers", "")
    display_df = df[df['CUSTOMER_NAME'].str.contains(search, case=False)] if search else df
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # New Loan Popover
    with st.popover("➕ New Loan Disbursal"):
        with st.form("new_loan"):
            name = st.text_input("Client Name")
            amt = st.number_input("Principal Amount", min_value=0)
            rate = st.number_input("Interest Rate (%)", value=10.0)
            if st.form_submit_button("✅ Disburse"):
                new_id = len(df) + 1
                new_row = pd.DataFrame([[new_id, name, amt, 0, amt, rate, datetime.now().date()]], columns=df.columns)
                new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                st.success("Loan Disbursed!")
                st.rerun()

elif page == "💰 Repayments":
    st.title("💰 Record a Payment")
    if not df.empty:
        with st.form("pay_form"):
            p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amount = st.number_input("Amount Paid", min_value=0)
            p_ref = st.text_input("Receipt / Reference No.")
            if st.form_submit_button("Submit Payment"):
                # Log to payment file
                new_p = pd.DataFrame([[datetime.now().date(), p_name, p_amount, p_ref]], columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                new_p.to_csv(PAYMENT_FILE, mode='a', header=False, index=False)
                # Update Master
                df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amount
                df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amount
                df.to_csv(DB_FILE, index=False)
                st.success("Payment Logged!")
                st.rerun()
    if os.path.exists(PAYMENT_FILE):
        st.write("---")
        st.subheader("Recent Payment History")
        st.dataframe(pd.read_csv(PAYMENT_FILE).iloc[::-1], use_container_width=True)

elif page == "📅 Calendar":
    st.title("📅 Collection Schedule")
    # RELOAD DATA TO ENSURE IT'S FRESH
    df = pd.read_csv(DB_FILE) 
    
    if not df.empty:
        cal_df = df.copy()
        # Ensure dates are readable
        cal_df['DATE_ISSUED'] = pd.to_datetime(cal_df['DATE_ISSUED'])
        cal_df['DUE_DATE'] = cal_df['DATE_ISSUED'] + pd.Timedelta(days=30)
        
        # Calculate how many days left
        today = pd.Timestamp(datetime.now().date())
        cal_df['DAYS_LEFT'] = (cal_df['DUE_DATE'] - today).dt.days
        
        # Filter for only unpaid loans
        active_loans = cal_df[cal_df['OUTSTANDING_AMOUNT'] > 0]
        
        st.subheader("🚨 Overdue & Upcoming Payments")
        st.dataframe(
            active_loans[['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT', 'DUE_DATE', 'DAYS_LEFT']], 
            use_container_width=True,
            column_config={
                "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d"),
                "DUE_DATE": st.column_config.DateColumn("Due on"),
                "DAYS_LEFT": st.column_config.NumberColumn("Days Remaining")
            }
        )
    else:
        st.info("No active loans found in the database.")

elif page == "📑 Collateral":
    st.title("📑 Collateral Management")
    with st.form("collat"):
        c_id = st.selectbox("Loan ID", options=df['SN'].tolist()) if not df.empty else 0
        c_type = st.selectbox("Item Type", ["Logbook", "Title", "Electronics", "Other"])
        c_val = st.number_input("Estimated Value", min_value=0)
        c_desc = st.text_area("Details")
        if st.form_submit_button("Register"):
            c_name = df[df['SN'] == c_id]['CUSTOMER_NAME'].values[0]
            pd.DataFrame([[c_id, c_name, c_type, c_desc, c_val, "Held"]], columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS']).to_csv(COLLATERAL_FILE, mode='a', header=False, index=False)
            st.success("Collateral Registered!")
    if os.path.exists(COLLATERAL_FILE):
        st.dataframe(pd.read_csv(COLLATERAL_FILE), use_container_width=True)

elif page == "📄 Client Ledger":
    st.title("📄 Client Transaction Ledger")
    df = pd.read_csv(DB_FILE)
    
    if not df.empty:
        target = st.selectbox("Select Client", options=df['CUSTOMER_NAME'].unique())
        
        if os.path.exists(PAYMENT_FILE):
            p_log = pd.read_csv(PAYMENT_FILE)
            # Filter for this specific client
            client_log = p_log[p_log['CUSTOMER_NAME'] == target].copy()
            
            if not client_log.empty:
                st.subheader(f"Payment History for {target}")
                st.dataframe(
                    client_log, 
                    use_container_width=True,
                    column_config={
                        "AMOUNT_PAID": st.column_config.NumberColumn("Amount", format="UGX %,d"),
                        "DATE": st.column_config.DateColumn("Date")
                    }
                )
                
                # Add a quick Balance check
                balance = df[df['CUSTOMER_NAME'] == target]['OUTSTANDING_AMOUNT'].values[0]
                st.metric("Remaining Balance", f"UGX {balance:,.0f}")
            else:
                st.warning(f"No payments found for {target} in {PAYMENT_FILE}")
        else:
            st.error("The Repayments Log file is missing!")

elif page == "⚙️ Settings":
    st.title("⚙️ System Settings")
    st.subheader("Branding")
    up_logo = st.file_uploader("Upload Sidebar Logo", type=["png", "jpg"])
    if up_logo:
        st.session_state['custom_logo_b64'] = base64.b64encode(up_logo.getvalue()).decode()
        st.success("Logo Uploaded!")
        st.rerun()
    if st.button("Reset to Default"):
        st.session_state['custom_logo_b64'] = None
        st.rerun()
