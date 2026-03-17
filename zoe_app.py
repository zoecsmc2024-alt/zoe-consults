import streamlit as st
import pandas as pd
from datetime import datetime
import os
# --- 0. SECURITY GATE (Username + Password) ---
def check_password():
    def password_entered():
        # Change these to whatever you like!
        if st.session_state["username"] == "admin" and st.session_state["password"] == "1234":
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🔐 ZoeLend IQ Pro Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔐 ZoeLend IQ Pro Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Username or Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()
# --- 1. CONFIG & THEME ---
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
        pd.DataFrame(columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'RECEIPT_NO']).to_csv(PAYMENT_FILE, index=False)
    if not os.path.exists(COLLATERAL_FILE):
        pd.DataFrame(columns=['LOAN_ID', 'CUSTOMER_NAME', 'ITEM_TYPE', 'DESCRIPTION', 'ESTIMATED_VALUE', 'STATUS']).to_csv(COLLATERAL_FILE, index=False)

@st.cache_data(show_spinner=False)
def load_data():
    init_db()
    try:
        data = pd.read_csv(DB_FILE)
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE']:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except:
        return pd.DataFrame()

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

# --- 4. TOP CONTROLS ---
col_search, col_btn, col_del, col_dl = st.columns([2.5, 1, 1, 0.5])

with col_search:
    search_query = st.text_input("", placeholder="🔍 Search borrower...", label_visibility="collapsed")

with col_btn:
    with st.popover("➕ New Loan", use_container_width=True):
        with st.form("new_loan_form", clear_on_submit=True):
            f_name = st.text_input("Customer Name")
            f_amount = st.number_input("Principal (UGX)", min_value=0, step=50000)
            f_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.5)
            
            # NEW: Take a photo of the borrower
            f_photo = st.camera_input("Take Borrower Photo")
            
            if st.form_submit_button("Confirm & Save"):
                if f_name:
                    # (Your existing saving code here...)
                    st.success(f"Loan for {f_name} saved with photo!")
                    new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.cache_data.clear()
                    st.rerun()

with col_del:
    with st.popover("🗑️ Delete Entry", use_container_width=True):
        if not df.empty:
            delete_id = st.selectbox("Select ID to Delete", options=df['SN'].tolist())
            if st.button("Confirm Delete", type="primary", use_container_width=True):
                updated_df = df[df['SN'] != delete_id]
                updated_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
                st.rerun()
        else: st.write("No records.")

with col_dl:
    if not df.empty:
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥", csv_bytes, "Zoe_Report.csv", "text/csv")

if search_query:
    df = df[df['CUSTOMER_NAME'].str.contains(search_query, case=False, na=False)]

# --- 5. DASHBOARD TABS ---
# We now have 5 tabs: 0=Overview, 1=Borrowers, 2=Repayments, 3=Collateral, 4=Calendar
menu_tabs = st.tabs(["📊 Overview", "👥 Borrowers List", "💰 Repayments", "📑 Collateral", "📅 Calendar"])
# --- TAB 0: OVERVIEW (With Performance Charts) ---
with menu_tabs[0]:
    if not df.empty:
        # 1. CALCULATE FINANCIALS
        total_principal = df['LOAN_AMOUNT'].sum()
        total_collected = df['AMOUNT_PAID'].sum()
        
        # Profit Calculation: Interest earned on the portion of principal already repaid
        total_interest_expected = (df['LOAN_AMOUNT'] * df['INTEREST_RATE'] / 100).sum()
        actual_profit = (total_collected / total_principal * total_interest_expected) if total_principal > 0 else 0

        # 2. KPI CARDS
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="box-card"><div class="box-title">Total Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="box-card"><div class="box-title">Principal Issued</div><div class="box-value">UGX {total_principal:,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="box-card"><div class="box-title">Total Collections</div><div class="box-value">UGX {total_collected:,.0f}</div></div>', unsafe_allow_html=True)
        
        profit_color = "#10b981" if actual_profit > 0 else "#ef4444"
        c4.markdown(f'<div class="box-card"><div class="box-title">Realized Profit</div><div class="box-value" style="color: {profit_color};">UGX {actual_profit:,.0f}</div></div>', unsafe_allow_html=True)
        
        st.write("---")
        
        # 3. PERFORMANCE CHARTS SECTION
        chart_col1, chart_col2 = st.columns([2, 1])
        
        with chart_col1:
            st.subheader("📈 Cash Flow Analysis")
            # Create a small dataframe for the bar chart
            performance_data = pd.DataFrame({
                "Metric": ["Principal", "Collections", "Profit"],
                "Amount": [total_principal, total_collected, actual_profit]
            })
            st.bar_chart(data=performance_data, x="Metric", y="Amount", color="#00acc1")

        with chart_col2:
            st.subheader("🎯 Collection %")
            # Simple Gauge-style calculation
            collection_rate = (total_collected / total_principal * 100) if total_principal > 0 else 0
            st.metric("Recovery Rate", f"{collection_rate:.1f}%", delta=f"{len(df)} Loans")
            st.write("This shows how much of your issued capital has returned to the business.")

        st.write("---")
        st.subheader("Loan Portfolio Details")

        # 4. TABLE DISPLAY LOGIC (Same as before)
        def process_full_display(row):
            interest_amt = (row['LOAN_AMOUNT'] * row['INTEREST_RATE']) / 100
            total_due = row['LOAN_AMOUNT'] + interest_amt
            due_date = pd.to_datetime(row['DATE_ISSUED']) + pd.Timedelta(days=30)
            if row['OUTSTANDING_AMOUNT'] <= 0: status = "✅ Paid"
            elif datetime.now() > due_date: status = "🚩 Overdue"
            elif row['AMOUNT_PAID'] == 0: status = "⚠️ Risky"
            else: status = "🔵 Active"
            return pd.Series([interest_amt, total_due, due_date.strftime('%Y-%m-%d'), status])

        display_df = df.copy()
        display_df[['INT_AMT', 'TOTAL_DUE', 'DUE_DATE', 'STATUS']] = display_df.apply(process_full_display, axis=1)

        cols_to_show = ['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'INT_AMT', 'TOTAL_DUE', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'STATUS']
        st.dataframe(
            display_df[cols_to_show],
            column_config={
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                "INT_AMT": st.column_config.NumberColumn("Interest", format="UGX %,d"),
                "TOTAL_DUE": st.column_config.NumberColumn("Total Due", format="UGX %,d"),
                "AMOUNT_PAID": st.column_config.NumberColumn("Paid", format="UGX %,d"),
                "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d"),
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No data found. Add a loan to see the charts!")
# --- TAB 1: BORROWERS LIST (Rearranged & Fixed) ---
with menu_tabs[1]:
    st.subheader("👥 Detailed Borrower Records")
    if not df.empty:
        # 1. ENSURE NUMERIC & MATH (Fixes the "interest not working" issue)
        crm_df = df.copy()
        crm_df['LOAN_AMOUNT'] = pd.to_numeric(crm_df['LOAN_AMOUNT'], errors='coerce').fillna(0)
        crm_df['INTEREST_RATE'] = pd.to_numeric(crm_df['INTEREST_RATE'], errors='coerce').fillna(0)
        
        # Calculate interest for display
        crm_df['INTEREST_VALUE'] = (crm_df['LOAN_AMOUNT'] * crm_df['INTEREST_RATE']) / 100
        
        # 2. REARRANGE COLUMNS (Issue Date moved up)
        # Defining the order here moves DATE_ISSUED before the financial math
        cols_ordered = [
            'SN', 'CUSTOMER_NAME', 'DATE_ISSUED', 'LOAN_AMOUNT', 
            'INTEREST_RATE', 'INTEREST_VALUE', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT'
        ]

        # 3. DISPLAY WITH COMMAS
        st.dataframe(
            crm_df[cols_ordered],
            column_config={
                "SN": "ID",
                "CUSTOMER_NAME": "Client Name",
                "DATE_ISSUED": st.column_config.DateColumn("Issue Date"),
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                "INTEREST_RATE": st.column_config.NumberColumn("Rate", format="%.1f%%"),
                "INTEREST_VALUE": st.column_config.NumberColumn("Interest Amount", format="UGX %,d"),
                "AMOUNT_PAID": st.column_config.NumberColumn("Total Repaid", format="UGX %,d"),
                "OUTSTANDING_AMOUNT": st.column_config.ProgressColumn(
                    "Balance Progress",
                    format="UGX %,d",
                    min_value=0,
                    max_value=int(crm_df["LOAN_AMOUNT"].max() if not crm_df.empty else 1),
                ),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No borrowers registered yet.")
# --- TAB 2: REPAYMENTS ---
with menu_tabs[2]:
    st.subheader("💰 Record a Payment")
    if not df.empty:
        with st.form("pay_form", clear_on_submit=True):
            p_name = st.selectbox("Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amount = st.number_input("Amount (UGX)", min_value=0, step=10000)
            p_ref = st.text_input("Receipt No.")
            if st.form_submit_button("Submit Payment"):
                # Log Transaction
                new_p = pd.DataFrame([[datetime.now().date(), p_name, p_amount, p_ref]], columns=['DATE', 'NAME', 'AMOUNT', 'REF'])
                new_p.to_csv(PAYMENT_FILE, mode='a', header=False, index=False)
                # Update Master
                master = pd.read_csv(DB_FILE)
                mask = (master['CUSTOMER_NAME'] == p_name) & (master['OUTSTANDING_AMOUNT'] > 0)
                if mask.any():
                    idx = master[mask].index[0]
                    master.at[idx, 'AMOUNT_PAID'] += p_amount
                    master.at[idx, 'OUTSTANDING_AMOUNT'] = master.at[idx, 'LOAN_AMOUNT'] - master.at[idx, 'AMOUNT_PAID']
                    master.to_csv(DB_FILE, index=False)
                    st.cache_data.clear()
                    st.rerun()
    if os.path.exists(PAYMENT_FILE):
        st.write("---")
        st.subheader("Recent Payments")
        st.dataframe(pd.read_csv(PAYMENT_FILE).iloc[::-1], use_container_width=True)

# --- TAB 3: COLLATERAL ---
with menu_tabs[3]:
    st.subheader("📑 Collateral Management")
    if not df.empty:
        with st.form("collat_form", clear_on_submit=True):
            loan_id = st.selectbox("Loan ID", options=df['SN'].tolist())
            i_type = st.selectbox("Category", ["Logbook", "Title", "Electronics", "Household", "Other"])
            i_val = st.number_input("Value (UGX)", min_value=0)
            i_desc = st.text_area("Item Details")
            if st.form_submit_button("Register Security"):
                name = df[df['SN'] == loan_id]['CUSTOMER_NAME'].values[0]
                pd.DataFrame([[loan_id, name, i_type, i_desc, i_val, "Held"]], columns=['ID', 'NAME', 'TYPE', 'DESC', 'VAL', 'STATUS']).to_csv(COLLATERAL_FILE, mode='a', header=False, index=False)
                st.success("Collateral recorded.")
    if os.path.exists(COLLATERAL_FILE):
        st.write("---")
        st.dataframe(pd.read_csv(COLLATERAL_FILE), use_container_width=True)

# --- TAB 4: CALENDAR & REMINDERS ---
with menu_tabs[4]:
    st.subheader("📅 Collection & Due Dates")
    
    if not df.empty:
        # Calculate days remaining for each loan
        cal_df = df.copy()
        cal_df['DUE_DATE'] = pd.to_datetime(cal_df['DATE_ISSUED']) + pd.Timedelta(days=30)
        cal_df['DAYS_TO_DUE'] = (cal_df['DUE_DATE'] - pd.Timestamp(datetime.now())).dt.days
        
        # Only show loans that aren't paid yet
        active_loans = cal_df[cal_df['OUTSTANDING_AMOUNT'] > 0]
        
        col_late, col_soon = st.columns(2)
        
        with col_late:
            st.error("🚨 Overdue (Immediate Action)")
            overdue = active_loans[active_loans['DAYS_TO_DUE'] < 0]
            st.dataframe(overdue[['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT', 'DUE_DATE']], use_container_width=True, hide_index=True)
            
        with col_soon:
            st.warning("⏳ Due within 7 Days")
            soon = active_loans[(active_loans['DAYS_TO_DUE'] >= 0) & (active_loans['DAYS_TO_DUE'] <= 7)]
            st.dataframe(soon[['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT', 'DUE_DATE']], use_container_width=True, hide_index=True)
    else:
        st.info("No active loans to track.")

