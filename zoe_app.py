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
    # ... existing DB_FILE and PAYMENT_FILE code ...
    if not os.path.exists(COLLATERAL_FILE):
        pd.DataFrame(columns=['LOAN_ID', 'CUSTOMER_NAME', 'ITEM_TYPE', 'DESCRIPTION', 'ESTIMATED_VALUE', 'STATUS']).to_csv(COLLATERAL_FILE, index=False)

def init_db():
    if not os.path.exists(DB_FILE):
        pd.DataFrame(columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED']).to_csv(DB_FILE, index=False)
    if not os.path.exists(PAYMENT_FILE):
        pd.DataFrame(columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'RECEIPT_NO']).to_csv(PAYMENT_FILE, index=False)

@st.cache_data(show_spinner=False)
def load_data():
    init_db()
    try:
        data = pd.read_csv(DB_FILE)
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']:
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

# --- 4. TOP CONTROLS (With Delete Option) ---
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
                        'SN': len(df) + 1,
                        'CUSTOMER_NAME': f_name, 'LOAN_AMOUNT': f_amount,
                        'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': f_amount,
                        'INTEREST_RATE': f_rate, 'DATE_ISSUED': datetime.now().strftime('%Y-%m-%d')
                    }])
                    new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.cache_data.clear()
                    st.rerun()

with col_del:
    with st.popover("🗑️ Delete Entry", use_container_width=True):
        st.warning("Action cannot be undone!")
        if not df.empty:
            # Dropdown to select by SN and Name
            delete_id = st.selectbox("Select Loan to Delete", 
                                     options=df['SN'].tolist(),
                                     format_func=lambda x: f"ID {x}: {df[df['SN']==x]['CUSTOMER_NAME'].values[0]}")
            
            if st.button("Confirm Delete", type="primary", use_container_width=True):
                # Filter out the selected SN
                updated_df = df[df['SN'] != delete_id]
                # Save the new filtered dataframe back to CSV
                updated_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
                st.success(f"Loan ID {delete_id} removed.")
                st.rerun()
        else:
            st.write("No records to delete.")

with col_dl:
    if not df.empty:
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥", csv_bytes, "Zoe_Lend_Report.csv", "text/csv")

# Filter logic
if search_query:
    df = df[df['CUSTOMER_NAME'].str.contains(search_query, case=False, na=False)]

# --- 5. DASHBOARD TABS ---
menu_tabs = st.tabs(["📊 Overview", "👥 Borrowers List", "💰 Repayments", "📅 Calendar"])

with menu_tabs[0]:
    if not df.empty:
        # --- (Your KPI Cards code here) ---

        st.write("---")
        st.subheader("Loan Portfolio Status")

        # 1. Logic for Calculated Columns
        def process_display_data(row):
            # Calculate Interest Amount: (Principal * Rate) / 100
            interest_amt = (row['LOAN_AMOUNT'] * row['INTEREST_RATE']) / 100
            total_due = row['LOAN_AMOUNT'] + interest_amt
            
            # Calculate Due Date (30 days after Issue Date)
            issue_date = pd.to_datetime(row['DATE_ISSUED'])
            due_date = issue_date + pd.Timedelta(days=30)
            
            # Status Logic
            if row['OUTSTANDING_AMOUNT'] <= 0:
                status = "✅ Paid"
            elif datetime.now() > due_date and row['OUTSTANDING_AMOUNT'] > 0:
                status = "🚩 Overdue"
            elif row['AMOUNT_PAID'] == 0:
                status = "⚠️ Risky"
            else:
                status = "🔵 Active"
                
            return pd.Series([interest_amt, total_due, due_date.strftime('%Y-%m-%d'), status])

        # Apply the logic
        display_df = df.copy()
        display_df[['INT_AMT', 'TOTAL_PAYABLE', 'DUE_DATE', 'STATUS']] = display_df.apply(process_display_data, axis=1)

        # 2. Reorder Columns: Status is now LAST
        column_order = [
            'SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'INTEREST_RATE', 
            'INT_AMT', 'TOTAL_PAYABLE', 'AMOUNT_PAID', 
            'OUTSTANDING_AMOUNT', 'DATE_ISSUED', 'DUE_DATE', 'STATUS'
        ]
        
        st.dataframe(
            display_df[column_order],
            column_config={
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %d"),
                "INTEREST_RATE": st.column_config.NumberColumn("Rate %", format="%.1f"),
                "INT_AMT": st.column_config.NumberColumn("Interest UGX", format="UGX %d"),
                "TOTAL_PAYABLE": st.column_config.NumberColumn("Total Due", format="UGX %d"),
                "AMOUNT_PAID": st.column_config.NumberColumn("Paid", format="UGX %d"),
                "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %d"),
                "DUE_DATE": st.column_config.DateColumn("Due Date"),
                "STATUS": st.column_config.TextColumn("Loan Status")
            },
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No data found. Add a loan to begin.")

with menu_tabs[2]:
    st.subheader("Log a Payment")
    if not df.empty:
        with st.form("pay_form", clear_on_submit=True):
            p_name = st.selectbox("Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amount = st.number_input("Amount (UGX)", min_value=0, step=10000)
            p_ref = st.text_input("Receipt No.")
            if st.form_submit_button("Submit Payment"):
                # Log transaction
                pd.DataFrame([[datetime.now().date(), p_name, p_amount, p_ref]], 
                           columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'RECEIPT_NO']).to_csv(PAYMENT_FILE, mode='a', header=False, index=False)
               # Update Master DB using SN instead of Name
                master_df = pd.read_csv(DB_FILE)
                
                # We need to find the specific SN for the selected name
                # For now, let's pick the row where the Name matches AND there is a balance
                mask = (master_df['CUSTOMER_NAME'] == p_name) & (master_df['OUTSTANDING_AMOUNT'] > 0)
                
                if mask.any():
                    # Get the index of the first matching active loan
                    idx = master_df[mask].index[0]
                    
                    master_df.at[idx, 'AMOUNT_PAID'] += p_amount
                    master_df.at[idx, 'OUTSTANDING_AMOUNT'] = master_df.at[idx, 'LOAN_AMOUNT'] - master_df.at[idx, 'AMOUNT_PAID']
                    
                    master_df.to_csv(DB_FILE, index=False)
                    st.success(f"Payment recorded specifically for {p_name} (Loan ID: {master_df.at[idx, 'SN']})")
                else:
                    st.error("No active loan found for this customer.")
                
                st.cache_data.clear()
                st.rerun()
                
    with menu_tabs[3]:
        st.subheader("📑 Collateral Management")
    
        if not df.empty:
        # 1. Entry Form
          with st.expander("📝 Register Security Item", expanded=False):
            with st.form("collateral_form", clear_on_submit=True):
                # We show SN and Name to be precise
                loan_choice = st.selectbox("Select Loan ID", 
                                          options=df['SN'].tolist(),
                                          format_func=lambda x: f"ID {x}: {df[df['SN']==x]['CUSTOMER_NAME'].values[0]}")
                
                col1, col2 = st.columns(2)
                with col1:
                    item_type = st.selectbox("Item Category", ["Logbook", "Land Title", "Electronics", "Household", "Other"])
                    est_value = st.number_input("Estimated Value (UGX)", min_value=0, step=100000)
                with col2:
                    description = st.text_area("Item Description (Serial Nos, Color, etc.)")
                
                if st.form_submit_button("Save Collateral"):
                    owner_name = df[df['SN'] == loan_choice]['CUSTOMER_NAME'].values[0]
                    new_item = pd.DataFrame([[loan_choice, owner_name, item_type, description, est_value, "In Possession"]], 
                                          columns=['LOAN_ID', 'CUSTOMER_NAME', 'ITEM_TYPE', 'DESCRIPTION', 'ESTIMATED_VALUE', 'STATUS'])
                    new_item.to_csv(COLLATERAL_FILE, mode='a', header=False, index=False)
                    st.success(f"Registered {item_type} for {owner_name}")
                    st.rerun()

        # 2. Display Table
        st.write("---")
        if os.path.exists(COLLATERAL_FILE):
            collat_df = pd.read_csv(COLLATERAL_FILE)
            if not collat_df.empty:
                st.dataframe(
                    collat_df,
                    column_config={
                        "ESTIMATED_VALUE": st.column_config.NumberColumn("Est. Value", format="UGX %d"),
                        "LOAN_ID": "ID"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No collateral items registered yet.")
    else:
        st.warning("Please add a loan before registering collateral.")
