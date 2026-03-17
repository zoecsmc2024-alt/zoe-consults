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

# --- TAB 0: OVERVIEW (Charts Restored) ---
with menu_tabs[0]:
    if not df.empty:
        # 1. KPI Metrics
        total_principal = df['LOAN_AMOUNT'].sum()
        total_collected = df['AMOUNT_PAID'].sum()
        total_outstanding = df['OUTSTANDING_AMOUNT'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Borrowers", len(df))
        c2.metric("Principal Issued", f"UGX {total_principal:,.0f}")
        c3.metric("Total Collections", f"UGX {total_collected:,.0f}")
        c4.metric("Outstanding", f"UGX {total_outstanding:,.0f}")
        
        st.write("---")

        # 2. Charts Section
        col_chart1, col_chart2 = st.columns([2, 1])
        with col_chart1:
            st.subheader("📊 Collection vs Principal")
            # Creating a simple bar chart for visual comparison
            chart_data = pd.DataFrame({
                "Category": ["Principal", "Collected", "Balance"],
                "Amount": [total_principal, total_collected, total_outstanding]
            })
            st.bar_chart(data=chart_data, x="Category", y="Amount", color="Category")

        with col_chart2:
            st.subheader("🎯 Loan Status")
            # Calculate status for the pie chart
            status_counts = df['OUTSTANDING_AMOUNT'].apply(lambda x: 'Paid' if x <= 0 else 'Active').value_counts()
            st.vega_lite_chart(df, {
                'mark': {'type': 'arc', 'innerRadius': 50},
                'encoding': {
                    'theta': {'field': 'SN', 'aggregate': 'count', 'type': 'quantitative'},
                    'color': {'field': 'OUTSTANDING_AMOUNT', 'bin': True, 'type': 'quantitative', 'scale': {'scheme': 'category20b'}}
                }
            }, use_container_width=True)

        st.write("---")
        st.subheader("📋 Portfolio Health")
        
        # 3. Data Table with COMMAS (st.column_config is key here)
        st.dataframe(
            filtered_df,
            column_config={
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                "TOTAL_DUE": st.column_config.NumberColumn("Total Due", format="UGX %,d"),
                "AMOUNT_PAID": st.column_config.NumberColumn("Paid", format="UGX %,d"),
                "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d"),
                "DATE_ISSUED": st.column_config.DateColumn("Issued Date"),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No data found. Add a loan to see the dashboard.")

# --- TAB 1: BORROWERS LIST (Commas Fixed) ---
with menu_tabs[1]:
    st.subheader("👥 Detailed Records")
    if not filtered_df.empty:
        st.dataframe(
            filtered_df[['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'INTEREST_RATE', 'INT_AMT', 'TOTAL_DUE', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']],
            column_config={
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                "INT_AMT": st.column_config.NumberColumn("Interest (UGX)", format="UGX %,d"),
                "TOTAL_DUE": st.column_config.NumberColumn("Total Debt", format="UGX %,d"),
                "AMOUNT_PAID": st.column_config.NumberColumn("Repaid", format="UGX %,d"),
                "OUTSTANDING_AMOUNT": st.column_config.ProgressColumn(
                    "Balance",
                    format="UGX %,d",
                    min_value=0,
                    max_value=int(df["TOTAL_DUE"].max())
                ),
            },
            use_container_width=True,
            hide_index=True,
        )

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

with menu_tabs[3]:
    st.subheader("📑 Collateral Management")
    
    # --- EMERGENCY REPAIR BUTTON ---
    # This button deletes the old file and makes a new one with the right columns
    with st.expander("🛠️ Troubleshooting & Repair"):
        if st.button("Flush & Reset Collateral Database"):
            if os.path.exists(COLLATERAL_FILE):
                os.remove(COLLATERAL_FILE) # Deletes the bad file
            # Recreate it immediately with the correct 'VAL' header
            pd.DataFrame(columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS']).to_csv(COLLATERAL_FILE, index=False)
            st.success("Database Repaired! You can now add collateral.")
            st.rerun()
    
    if not df.empty:
        col_form, col_stats = st.columns([1, 2])
        
        with col_form:
            with st.form("collat_form", clear_on_submit=True):
                loan_id = st.selectbox("Assign to Loan ID", options=df['SN'].tolist())
                i_type = st.selectbox("Category", ["Logbook", "Land Title", "Electronics", "Household", "Business Asset"])
                i_val = st.number_input("Estimated Value (UGX)", min_value=0, step=50000)
                i_desc = st.text_area("Item Details")
                
                if st.form_submit_button("🔒 Register Security"):
                    cust_name = df[df['SN'] == loan_id]['CUSTOMER_NAME'].values[0]
                    # This MUST match the columns in the Repair Button above
                    new_collat = pd.DataFrame([[loan_id, cust_name, i_type, i_desc, i_val, "Held"]], 
                                            columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS'])
                    new_collat.to_csv(COLLATERAL_FILE, mode='a', header=False, index=False)
                    st.success(f"Security registered for {cust_name}")
                    st.rerun()

        with col_stats:
            if os.path.exists(COLLATERAL_FILE):
                try:
                    c_df = pd.read_csv(COLLATERAL_FILE)
                    # If the file is empty or missing 'VAL', show the warning
                    if not c_df.empty and 'VAL' in c_df.columns:
                        total_security = pd.to_numeric(c_df['VAL'], errors='coerce').sum()
                        st.info(f"**Total Security Value Held:** UGX {total_security:,.0f}")
                        st.dataframe(c_df, use_container_width=True, hide_index=True)
                    else:
                        st.warning("⚠️ The database file is empty or formatted incorrectly. Use the 'Repair' button above.")
                except:
                    st.error("Could not read file. Please use the Repair button.")
    else:
        st.info("Please add a borrower in the 'Borrowers' tab first.")
