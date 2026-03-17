import streamlit as st
import pandas as pd
from datetime import datetime
import os
# --- 0. SECURITY GATE ---
def check_password():
    def login_clicked():
        # You can change 'admin' and 'Zoe2026' to whatever you prefer!
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

def calculate_reducing_balance(principal, annual_rate, periods=12):
    # Monthly rate and payment calculation
    monthly_rate = (annual_rate / 100) / 12
    # Formula: M = P [ i(1 + i)^n ] / [ (1 + i)^n – 1 ]
    if monthly_rate > 0:
        monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**periods) / ((1 + monthly_rate)**periods - 1)
    else:
        monthly_payment = principal / periods

    schedule = []
    remaining_balance = principal
    
    for i in range(1, periods + 1):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment
        
        schedule.append({
            "Month": i,
            "Payment": monthly_payment,
            "Principal": principal_payment,
            "Interest": interest_payment,
            "Balance": max(0, remaining_balance)
        })
    return pd.DataFrame(schedule), monthly_payment
# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #f1f5f9;
    }
    
    /* Style for the sidebar and containers */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
    }

    /* Target the buttons we created */
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

# --- 3. INTEGRATED NAVIGATION & ICON BAR ---
import base64

# Function to convert local image to base64 (required for HTML in Streamlit)
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

# --- 3. BRANDED LOGO HEADER (Fail-Proof Version) ---

# OPTION A: Use a direct URL (Best for Cloud/GitHub)
# Replace the URL below with your actual hosted logo link
LOGO_URL = "https://img.icons8.com/fluency/96/money-bag-euro.png" 

import base64
import io

# --- 1. LOGO STORAGE LOGIC ---
# This ensures the image stays visible while you navigate tabs
if 'custom_logo_b64' not in st.session_state:
    st.session_state['custom_logo_b64'] = None

# --- 2. THE BLUE BRANDING BAR ---
# We use the session state logo if it exists, otherwise a default icon
logo_display = f'<img src="data:image/png;base64,{st.session_state["custom_logo_b64"]}" style="height: 40px; border-radius: 5px;">' if st.session_state['custom_logo_b64'] else '<img src="https://img.icons8.com/fluency/96/money-bag-euro.png" style="height: 40px;">'

header_html = f"""
    <div style="background-color: #0f172a; padding: 12px 25px; display: flex; justify-content: space-between; align-items: center; color: white; border-bottom: 3px solid #00acc1; border-radius: 8px 8px 0 0; margin-bottom: 10px;">
        <div style="display: flex; align-items: center; gap: 15px;">
            {logo_display}
            <div style="display: flex; flex-direction: column; line-height: 1.1;">
                <b style="font-size: 1.2em; letter-spacing: 0.5px;">Zoe Consults</b>
                <span style="font-size: 0.7em; opacity: 0.6; font-weight: 300;">Evans Ahuura | Admin</span>
            </div>
        </div>
        <div style="font-size: 0.8em; opacity: 0.4;">{datetime.now().strftime('%d %b %H:%M')}</div>
    </div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# --- REFRESHED ACTION BAR ---
with st.container():
    # We allocate more space for the text buttons
    c_search, c_new, c_del, c_dl, c_set, c_logout = st.columns([3, 1.2, 1.2, 1.2, 0.6, 0.6])

    with c_search:
        search_query = st.text_input("", placeholder="🔍 Search borrowers...", label_visibility="collapsed")

    with c_new:
        # Green "New Loan" Button
        with st.popover("➕ New Loan", use_container_width=True):
            with st.form("new_loan_form_v3", clear_on_submit=True):
                st.markdown("#### 📝 Add Borrower")
                f_name = st.text_input("Full Name")
                f_nin = st.text_input("NIN")
                f_amt = st.number_input("Principal (UGX)", min_value=0)
                f_rate = st.number_input("Rate (%)", value=2.8)
                if st.form_submit_button("✅ Disburse Loan", use_container_width=True):
                    if f_name and f_amt > 0:
                        # --- YOUR SAVE LOGIC HERE ---
                        st.success("Loan Added!")
                        st.rerun()

    with c_del:
        # Red "Delete" Button
        with st.popover("🗑️ Delete", use_container_width=True):
            st.markdown("#### ⚠️ Remove Record")
            if not df.empty:
                to_delete = st.selectbox("Select ID to Remove", options=df['SN'].tolist())
                if st.button("Confirm Permanent Delete", type="primary", use_container_width=True):
                    # --- YOUR DELETE LOGIC HERE ---
                    st.rerun()

    with c_dl:
        # Blue "Export" Button
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export CSV",
                data=csv,
                file_name=f"Zoe_Consults_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    with c_set:
        with st.popover("⚙️", help="Settings"):
            # (Your Branding/Excel Import logic goes here)
            st.write("Settings Menu")

    with c_logout:
        if st.button("🚪", help="Logout", use_container_width=True):
            st.session_state["password_correct"] = False
            st.rerun()
st.write("---") # Visual separator before the tabs
# --- 5. DASHBOARD TABS ---
# We now have 6 tabs (Index 0 to 5)
menu_tabs = st.tabs([
    "📊 Overview", 
    "👥 Borrowers List", 
    "💰 Repayments", 
    "📑 Collateral", 
    "📅 Calendar", 
    "📄 Client Report"  # <--- This adds Tab 5
])
# --- TAB 0: OVERVIEW (The Eye-Catching FinTech Dashboard) ---
with menu_tabs[0]:
    if not df.empty:
        # 1. CALCULATE FINANCIALS
        total_principal = df['LOAN_AMOUNT'].sum()
        total_collected = df['AMOUNT_PAID'].sum()
        total_interest_expected = (df['LOAN_AMOUNT'] * df['INTEREST_RATE'] / 100).sum()
        actual_profit = (total_collected / total_principal * total_interest_expected) if total_principal > 0 else 0

        # 2. ENHANCED KPI CARDS (With Hover Effects & Colored Accents)
        c1, c2, c3, c4 = st.columns(4)
        
        # We use HTML/CSS for that "Premium" feel
        card_style = 'style="background: white; padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 5px solid'
        
        c1.markdown(f'<div {card_style} #6366f1;"><div style="color: #64748b; font-size: 0.8em; font-weight: 600;">👥 TOTAL BORROWERS</div><div style="font-size: 1.8em; font-weight: 800;">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div {card_style} #0ea5e9;"><div style="color: #64748b; font-size: 0.8em; font-weight: 600;">💰 PRINCIPAL ISSUED</div><div style="font-size: 1.8em; font-weight: 800;">{total_principal:,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div {card_style} #f59e0b;"><div style="color: #64748b; font-size: 0.8em; font-weight: 600;">📥 TOTAL COLLECTIONS</div><div style="font-size: 1.8em; font-weight: 800;">{total_collected:,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div {card_style} #10b981;"><div style="color: #64748b; font-size: 0.8em; font-weight: 600;">📈 REALIZED PROFIT</div><div style="font-size: 1.8em; font-weight: 800; color: #10b981;">{actual_profit:,.0f}</div></div>', unsafe_allow_html=True)
        
        st.write("---")

       # --- 3. PERFORMANCE VISUALS ---
        chart_col1, chart_col2 = st.columns([2, 1])
        
        with chart_col1:
            st.subheader("📈 Cash Flow Analysis")
            perf_df = pd.DataFrame({
                "Metric": ["Principal", "Collections", "Profit"],
                "Amount": [total_principal, total_collected, actual_profit]
            })
            st.bar_chart(data=perf_df, x="Metric", y="Amount", color="Metric")

       # --- 5. TIME-SERIES PERFORMANCE TRENDS (Error-Proof Version) ---
        st.write("---")
        st.subheader("📉 Growth & Liquidity Trends")

        if not df.empty and os.path.exists(PAYMENT_FILE):
            try:
                # 1. Process Loans
                loan_trend_df = df.copy()
                loan_trend_df['MONTH'] = pd.to_datetime(loan_trend_df['DATE_ISSUED']).dt.strftime('%Y-%m')
                monthly_loans = loan_trend_df.groupby('MONTH')['LOAN_AMOUNT'].sum().reset_index()
                
                # 2. Process Payments (Safe Column Detection)
                pay_df = pd.read_csv(PAYMENT_FILE)
                pay_df['MONTH'] = pd.to_datetime(pay_df['DATE']).dt.strftime('%Y-%m')
                
                # Check for column name variations
                pay_col = 'AMOUNT' if 'AMOUNT' in pay_df.columns else 'AMOUNT_PAID'
                monthly_pays = pay_df.groupby('MONTH')[pay_col].sum().reset_index()
                monthly_pays.columns = ['MONTH', 'Total Collected'] # Rename for merge

                # 3. Merge and Chart
                trend_df = pd.merge(monthly_loans, monthly_pays, on='MONTH', how='outer').fillna(0)
                trend_df.columns = ['Month', 'Principal Issued', 'Total Collected']
                trend_df = trend_df.sort_values('Month')

                st.line_chart(
                    trend_df.set_index('Month'), 
                    color=["#0ea5e9", "#10b981"]
                )
                st.caption("🔵 Principal Issued (Investment) vs 🟢 Total Collected (Recovery)")
            
            except Exception as e:
                st.warning(f"Could not generate trends: Ensure your dates are in YYYY-MM-DD format.")
        else:
            st.info("Growth trends will appear once you have a history of payments recorded.")

        with chart_col2:
            st.subheader("🎯 Risk Distribution")
            status_df = df.copy()
            def get_stat(row):
                due = pd.to_datetime(row['DATE_ISSUED']) + pd.Timedelta(days=30)
                if row['OUTSTANDING_AMOUNT'] <= 0: return "Paid"
                elif datetime.now() > due: return "Overdue"
                else: return "Active"
            status_df['Status'] = status_df.apply(get_stat, axis=1)
            
            st.vega_lite_chart(status_df, {
                'mark': {'type': 'arc', 'innerRadius': 45},
                'encoding': {
                    'theta': {'field': 'SN', 'aggregate': 'count', 'type': 'quantitative'},
                    'color': {
                        'field': 'Status', 
                        'type': 'nominal', 
                        'scale': {'domain': ['Active', 'Overdue', 'Paid'], 'range': ['#0ea5e9', '#ef4444', '#10b981']}
                    }
                },
                'view': {'stroke': None}
            }, use_container_width=True)

        st.write("---")
        st.subheader("📋 Detailed Portfolio")
        
        # --- 4. DATA TABLE ---
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

        cols_to_show = ['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'INT_AMT', 'TOTAL_DUE', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'DUE_DATE', 'STATUS']
        
        st.dataframe(
            display_df[cols_to_show],
            column_config={
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                "INT_AMT": st.column_config.NumberColumn("Interest", format="UGX %,d"),
                "TOTAL_DUE": st.column_config.NumberColumn("Total Due", format="UGX %,d"),
                "AMOUNT_PAID": st.column_config.NumberColumn("Repaid", format="UGX %,d"),
                "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d"),
                "DUE_DATE": st.column_config.DateColumn("Due Date"),
            },
            use_container_width=True, 
            hide_index=True
        ) # <--- Only ONE closing parenthesis here!
        
    else:
        st.info("👋 Welcome! Please add a loan to see your dashboard come to life.")
# --- TAB 1: BORROWERS LIST (Formatted & Editable) ---
with menu_tabs[1]:
    st.subheader("👥 Manage Loan Records")
    
    # 1. PRE-PROCESS THE MATH (Same logic as Overview)
    def calculate_row_data(row):
        interest_amt = (row['LOAN_AMOUNT'] * row['INTEREST_RATE']) / 100
        total_due = row['LOAN_AMOUNT'] + interest_amt
        return pd.Series([interest_amt, total_due])

    if not df.empty:
        display_df = df.copy()
        # Ensure your missing columns (Interest & Total Due) are calculated first
        display_df[['INT_AMT', 'TOTAL_DUE']] = display_df.apply(calculate_row_data, axis=1)

        # 2. EDIT TOGGLE
        edit_mode = st.toggle("✏️ Enable Edit Mode", help="Modify principal, rates, or names.")

        # 3. UNIFIED COLUMN CONFIG (This brings back the commas!)
        col_setup = {
            "SN": st.column_config.NumberColumn("ID", disabled=True),
            "CUSTOMER_NAME": "Client Name",
            "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
            "INT_AMT": st.column_config.NumberColumn("Interest", format="UGX %,d", disabled=True),
            "TOTAL_DUE": st.column_config.NumberColumn("Total Due", format="UGX %,d", disabled=True),
            "AMOUNT_PAID": st.column_config.NumberColumn("Repaid", format="UGX %,d"),
            "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d", disabled=True),
            "INTEREST_RATE": st.column_config.NumberColumn("Rate %", format="%.1f%%"),
            "DATE_ISSUED": st.column_config.DateColumn("Date Issued")
        }

        if edit_mode:
            st.warning("⚠️ Manual edits will recalculate totals after saving.")
            # Editable table
            edited_df = st.data_editor(
                display_df, 
                key="borrower_editor_pro",
                use_container_width=True,
                hide_index=True,
                column_config=col_setup
            )

            if st.button("💾 Save All Changes", type="primary"):
                # We only save the original columns back to the CSV (to avoid duplicating math columns)
                original_cols = ['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED']
                edited_df[original_cols].to_csv(DB_FILE, index=False)
                st.success("Database updated!")
                st.rerun()
        else:
            # Standard View (All columns with commas)
            st.dataframe(
                display_df, 
                use_container_width=True, 
                hide_index=True,
                column_config=col_setup
            )
    else:
        st.info("No records to display.")
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

# --- TAB 5: DYNAMIC CLIENT LEDGER (Fixed Indentation) ---
with menu_tabs[5]:
    st.subheader("📄 Transaction Ledger")
    
    if not df.empty:
        # 1. Selection
        client_name = st.selectbox("Select Client for Ledger", options=df['CUSTOMER_NAME'].unique(), key="ledger_select")
        c_details = df[df['CUSTOMER_NAME'] == client_name].iloc[0]
        
        # --- CLIENT HEADER ---
        st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border-left: 5px solid #0ea5e9; margin-bottom: 20px;">
                <h3 style="margin:0; color: #0f172a;">{client_name.upper()}</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; font-size: 0.9em;">
                    <span><b>NIN:</b> {c_details.get('NIN', 'N/A')}</span>
                    <span><b>Contact:</b> {c_details.get('CONTACT', 'N/A')}</span>
                    <span><b>Address:</b> {c_details.get('ADDRESS', 'Kampala, Uganda')}</span>
                    # --- FIXED LINE ---
                    # 1. Format the money first
formatted_principal = f"{int(c_details['LOAN_AMOUNT']):,.0f}"

# 2. The HTML Block (Carefully balanced quotes)
st.markdown(f"""
    <div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; border-left: 5px solid #0ea5e9; margin-bottom: 20px;">
        <h3 style="margin:0; color: #0f172a;">{client_name.upper()}</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; font-size: 0.9em;">
            <span><b>NIN:</b> {c_details.get('NIN', 'N/A')}</span>
            <span><b>Contact:</b> {c_details.get('CONTACT', 'N/A')}</span>
            <span><b>Address:</b> {c_details.get('ADDRESS', 'Kampala, Uganda')}</span>
            <span><b>Principal:</b> UGX {formatted_principal}</span>
        </div>
    </div>
""", unsafe_allow_html=True)
        </div>
    </div>
""", unsafe_allow_html=True)
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 2. LEDGER PROCESSING
        if os.path.exists(PAYMENT_FILE):
            all_payments = pd.read_csv(PAYMENT_FILE)
            client_pays = all_payments[all_payments['CUSTOMER_NAME'] == client_name].copy()
            
            ledger_entries = []
            curr_bal = c_details['LOAN_AMOUNT']
            rate = c_details['INTEREST_RATE']
            
            # Use 'AMOUNT' or 'AMOUNT_PAID' depending on your CSV
            amt_col = 'AMOUNT' if 'AMOUNT' in client_pays.columns else 'AMOUNT_PAID'

            for _, pay in client_pays.iterrows():
                int_chg = (curr_bal * (rate / 100) / 12)
                p_amt = pay[amt_col]
                curr_bal = (curr_bal + int_chg) - p_amt
                
                ledger_entries.append({
                    "Date": pd.to_datetime(pay['DATE']).strftime('%Y-%m-%d'),
                    "Description": f"Repayment (Ref: {pay.get('REF', 'N/A')})",
                    "Interest": int_chg,
                    "Paid": p_amt,
                    "Balance": max(0, curr_bal)
                })

            ledger_df = pd.DataFrame(ledger_entries)

            if not ledger_df.empty:
                m1, m2 = st.columns(2)
                m1.metric("Current Outstanding", f"UGX {curr_bal:,.0f}")
                m2.metric("Total Interest Accrued", f"UGX {ledger_df['Interest'].sum():,.0f}")

                st.dataframe(
                    ledger_df,
                    column_config={
                        "Interest": st.column_config.NumberColumn(format="UGX %,d"),
                        "Paid": st.column_config.NumberColumn(format="UGX %,d"),
                        "Balance": st.column_config.NumberColumn(format="UGX %,d"),
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("No payments recorded yet. The balance is still at the full principal.")
        else:
            st.error("Payment database file not found.")
    else:
        st.info("Please add a borrower to view the ledger.")
