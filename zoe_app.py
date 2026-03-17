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
# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(to bottom, #f0f2f5, #ffffff); }
    .box-card {
        background: white; 
        border: none;
        padding: 24px; 
        border-radius: 15px; 
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .box-card:hover { transform: translateY(-5px); }
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

# --- 3. THE ACTION & EDIT TOOLBAR ---
with st.container():
    # Added a new 'Settings' column (c_set)
    c_search, c_new, c_del, c_dl, c_set, c_logout = st.columns([3.5, 0.4, 0.4, 0.4, 0.4, 0.4])

    with c_search:
        search_query = st.text_input("", placeholder="🔍 Search borrowers...", label_visibility="collapsed")

    with c_new:
        with st.popover("➕", help="New Loan"):
            st.markdown("### 📝 New Loan Entry")
            # ... (your existing form logic)
            
    with c_del:
        with st.popover("🗑️", help="Delete"):
            # ... (your existing delete logic)
            pass

    with c_dl:
        # ... (your existing download logic)
        pass

    with c_set:
        with st.popover("⚙️", help="Brand Settings"):
            st.markdown("#### 🖼️ Update Logo")
            new_file = st.file_uploader("Upload PNG/JPG", type=["png", "jpg", "jpeg"])
            
            if new_file:
                encoded = base64.b64encode(new_file.getvalue()).decode()
                st.session_state['custom_logo_b64'] = encoded
                st.success("Logo uploaded!")
                # Just a normal button, no callback needed
                if st.button("Refresh Dashboard"):
                    st.rerun()
            
            if st.button("Reset to Default"):
                st.session_state['custom_logo_b64'] = None
                st.rerun()

    with c_logout:
        if st.button("🚪", help="Logout"):
            st.session_state["password_correct"] = False
            st.rerun()
st.write("---") # Visual separator before the tabs
# --- 5. DASHBOARD TABS ---
# We now have 5 tabs: 0=Overview, 1=Borrowers, 2=Repayments, 3=Collateral, 4=Calendar
menu_tabs = st.tabs(["📊 Overview", "👥 Borrowers List", "💰 Repayments", "📑 Collateral", "📅 Calendar"])
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
# --- TAB 1: BORROWERS LIST (With Edit Pencil Logic) ---
with menu_tabs[1]:
    st.subheader("👥 Manage Loan Records")
    
    # 1. The Edit Toggle (The "Pencil" behavior)
    edit_mode = st.toggle("✏️ Enable Edit Mode", help="Turn this on to modify names, amounts, or rates directly in the table.")

    if not df.empty:
        if edit_mode:
            st.info("💡 Double-click any cell to edit. Changes are saved when you click 'Save Changes' below.")
            
            # The Magic Widget: st.data_editor
            edited_df = st.data_editor(
                df, 
                key="borrower_editor",
                num_rows="dynamic", # Allows you to add/delete rows too!
                use_container_width=True,
                hide_index=True,
                column_config={
                    "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                    "AMOUNT_PAID": st.column_config.NumberColumn("Repaid", format="UGX %,d"),
                    "INTEREST_RATE": st.column_config.NumberColumn("Rate %", format="%.1f%%"),
                }
            )

            # 2. Save Logic
            if st.button("💾 Save All Changes", type="primary"):
                edited_df.to_csv(DB_FILE, index=False)
                st.success("Database updated successfully!")
                st.rerun()
        
        else:
            # Standard View Mode (The clean table you already have)
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No records to edit.")
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

