import streamlit as st
import pandas as pd
from datetime import datetime
import os

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
            if st.form_submit_button("Confirm & Save"):
                if f_name:
                    new_row = pd.DataFrame([{
                        'SN': len(df) + 1, 'CUSTOMER_NAME': f_name, 'LOAN_AMOUNT': f_amount,
                        'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': f_amount,
                        'INTEREST_RATE': f_rate, 'DATE_ISSUED': datetime.now().strftime('%Y-%m-%d')
                    }])
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
# DEFINITION ORDER: 0=Overview, 1=Borrowers List, 2=Repayments, 3=Calendar/Collateral
menu_tabs = st.tabs(["📊 Overview", "👥 Borrowers List", "💰 Repayments", "📑 Collateral"])

# --- TAB 0: OVERVIEW ---
with menu_tabs[0]:
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="box-card"><div class="box-title">Borrowers</div><div class="box-value">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="box-card"><div class="box-title">Principal</div><div class="box-value">UGX {df["LOAN_AMOUNT"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="box-card"><div class="box-title">Collections</div><div class="box-value">UGX {df["AMOUNT_PAID"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        active_count = len(df[df['OUTSTANDING_AMOUNT'] > 0])
        c4.markdown(f'<div class="box-card"><div class="box-title">Active Loans</div><div class="box-value">{active_count}</div></div>', unsafe_allow_html=True)
        
        st.write("---")
        st.subheader("Quick Portfolio View")
        
        def process_display(row):
            interest_amt = (row['LOAN_AMOUNT'] * row['INTEREST_RATE']) / 100
            due_date = pd.to_datetime(row['DATE_ISSUED']) + pd.Timedelta(days=30)
            if row['OUTSTANDING_AMOUNT'] <= 0: status = "✅ Paid"
            elif datetime.now() > due_date: status = "🚩 Overdue"
            else: status = "🔵 Active"
            return pd.Series([interest_amt, due_date.strftime('%Y-%m-%d'), status])

        display_df = df.copy()
        display_df[['INT_AMT', 'DUE_DATE', 'STATUS']] = display_df.apply(process_display, axis=1)
        st.dataframe(display_df[['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'STATUS']], use_container_width=True, hide_index=True)
    else:
        st.info("No data found.")

# --- TAB 1: BORROWERS LIST (NEW!) ---
with menu_tabs[1]:
    st.subheader("👥 Detailed Borrower Records")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No borrowers registered.")

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
