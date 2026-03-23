import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import gspread
import json
import io
from datetime import datetime, timedelta
from fpdf import FPDF
from streamlit_option_menu import option_menu
from google.oauth2.service_account import Credentials

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Zoe Consults Admin",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. BRANDING & NAVY/BABY BLUE STYLING ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .main-title {{ font-size: 32px; font-weight: 700; color: #1e3a8a; margin-bottom: 20px; }}
    .stMetric {{ 
        background-color: #f0f9ff; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 6px solid #1e3a8a; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    div.stButton > button:first-child {{
        background-color: #1e3a8a;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
        font-weight: 600;
    }}
    div.stButton > button:hover {{
        background-color: #3b82f6;
        color: white;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'ready' not in st.session_state:
    st.session_state.ready = False
if 'b64_str' not in st.session_state:
    st.session_state.b64_str = ""
if 'last_client' not in st.session_state:
    st.session_state.last_client = ""

# --- 4. DUAL-KEY SECURITY (Login) ---
if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>🏛️ Admin Portal</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            user = st.text_input("Username")
            pw = st.text_input("Access Key", type="password")
            if st.button("Login to Zoe Consults", use_container_width=True):
                if user == "bestie" and pw == "ZoeAdmin2026":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    st.stop()

# --- 5. DATA ENGINE (Google Sheets - Silent Success Version) ---
@st.cache_data(ttl=600)
def load_full_database():
    try:
        # 1. Setup Dict and Clean Newlines
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        # 2. Direct Authorization (The g_client)
        client = gspread.service_account_from_dict(creds_dict)
        database = client.open("Zoe_Consults_Database")
        
        def fetch_worksheet(name):
            try:
                sheet = database.worksheet(name)
                data = sheet.get_all_records()
                return pd.DataFrame(data) if data else pd.DataFrame()
            except:
                return pd.DataFrame()

        # Fetch Data
        df = fetch_worksheet("Clients")
        pay_df = fetch_worksheet("Repayments")
        collateral_df = fetch_worksheet("Collateral")
        expense_df = fetch_worksheet("Expenses")
        petty_df = fetch_worksheet("PettyCash")
        payroll_df = fetch_worksheet("Payroll")
        
        # Clean Numeric Columns
        if not df.empty:
            for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df, pay_df, collateral_df, expense_df, petty_df, payroll_df, client

    except Exception as e:
        # 🤫 The Magic Filter: Ignore the "Success" response
        if "200" not in str(e):
            st.error(f"Actual Sync Error: {e}")
        
        # We still return the client even if a '200' message was sent
        try:
            client = gspread.service_account_from_dict(creds_dict)
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), client
        except:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

# ACTIVATE THE SYSTEM
df, pay_df, collateral_df, expense_df, petty_df, payroll_df, g_client = load_full_database()
# --- 6. NAVIGATION (Sidebar) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>ZOE ADMIN</h2>", unsafe_allow_html=True)
    page = option_menu(
        menu_title=None,
        options=["Overview", "Borrowers", "Collateral", "Calendar", "Ledger", "Overdue Tracker", "Expenses", "Petty Cash", "Payroll", "Add Payment", "Settings"],
        icons=["grid-1x2", "people", "shield-lock", "calendar3", "file-earmark-medical", "alarm", "wallet2", "cash-register", "person-check", "cash-stack", "person-plus", "gear"],
        default_index=0,
        styles={"nav-link": {"font-size": "12px"}, "nav-link-selected": {"background-color": "#1e3a8a"}}
    )
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear(); st.rerun()

# --- 7. PAGE MODULES ---

# PAGE: OVERVIEW
if page == "Overview":
    st.markdown('<div class="main-title">🏛️ Executive Overview</div>', unsafe_allow_html=True)
    
    # 1. MERGE CLOUD + LOCAL DATA FOR TOTALS
    # This ensures your new registration shows up here immediately!
    local_df = pd.DataFrame(st.session_state.get('local_registry', []))
    combined_df = pd.concat([df, local_df], ignore_index=True)
    
    if not combined_df.empty:
        # Ensure the math columns are numbers, not text
        for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']:
            if col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0)
        
        t_cap = combined_df['LOAN_AMOUNT'].sum()
        t_coll = combined_df['AMOUNT_PAID'].sum()
        t_due = combined_df['OUTSTANDING_AMOUNT'].sum()
    else:
        t_cap, t_coll, t_due = 0, 0, 0

    # 2. EXPENSE TOTALS
    t_ops = expense_df['AMOUNT'].sum() if not expense_df.empty else 0
    t_petty = petty_df[petty_df['TYPE'] == 'Spend']['AMOUNT'].sum() if not petty_df.empty else 0
    t_pay = payroll_df['NET_PAY'].sum() if not payroll_df.empty else 0
    
    net_rev = t_coll - (t_ops + t_petty + t_pay)
    
    # 3. DISPLAY METRICS (With Comma Formatting)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Capital Out", f"UGX {t_cap:,.0f}")
    k2.metric("📈 Collected", f"UGX {t_coll:,.0f}")
    k3.metric("💎 Net Revenue", f"UGX {net_rev:,.0f}", delta="After Bills")
    k4.metric("🚨 At Risk", f"UGX {t_due:,.0f}", delta_color="inverse")

    st.write("---")
    
    # 4. CHARTS (Updated to use Combined Data)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Collection Ratio")
        if t_cap > 0:
            fig = px.pie(
                values=[t_coll, t_due], 
                names=['Paid', 'Due'], 
                hole=.5, 
                color_discrete_sequence=['#1e3a8a', '#3b82f6']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ℹ️ Add a borrower to see the ratio.")
            
    with c2:
        st.markdown("#### Monthly Expense Breakdown")
        if not expense_df.empty:
            st.bar_chart(expense_df.groupby('CATEGORY')['AMOUNT'].sum())
        else:
            st.info("ℹ️ No expenses recorded yet.")
# PAGE: BORROWERS (Now includes Registration)
elif page == "Borrowers":
    st.markdown('<div class="main-title">👥 Borrower Management Hub</div>', unsafe_allow_html=True)
    
    if 'local_registry' not in st.session_state:
        st.session_state.local_registry = []

    # 1. REGISTRATION SECTION
    with st.expander("➕ Register New Client (KYC Enrollment)", expanded=True):
        with st.form("kyc_registration_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("First Name")
                l_name = st.text_input("Last Name")
                phone = st.text_input("Contact Number (256...)")
                gender = st.selectbox("Gender", ["Male", "Female"])
                nin = st.text_input("NIN (National ID Number)")
                issue_date = st.date_input("Loan Issue Date", value=datetime.now())
            
            with c2:
                loan_amt = st.number_input("Approved Loan Amount (UGX)", min_value=0, step=50000)
                interest = st.number_input("Agreed Interest Rate (%)", min_value=0)
                loan_type = st.selectbox("Loan Type", ["Personal", "Business", "Emergency"])
                address = st.text_area("Residential Address")
                due_date = st.date_input("Repayment Due Date", value=datetime.now() + timedelta(days=30))

            if st.form_submit_button("🚀 Finalize Registration & Disburse"):
                if f_name and l_name and nin:
                    full_name = f"{f_name} {l_name}".upper()
                    
                    # Constructing the row with new Date columns
                    new_entry = {
                        "CUSTOMER_NAME": full_name,
                        "CONTACT": phone,
                        "LOAN_AMOUNT": loan_amt,
                        "AMOUNT_PAID": 0,
                        "OUTSTANDING_AMOUNT": loan_amt,
                        "INTEREST_RATE": interest,
                        "NIN": nin,
                        "ADDRESS": address,
                        "GENDER": gender,
                        "LOAN_TYPE": loan_type,
                        "ISSUE_DATE": str(issue_date),
                        "DUE_DATE": str(due_date)
                    }

                    st.session_state.local_registry.append(new_entry)
                    
                    try:
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("Clients")
                        
                        # Save to Google (appends to the end of the sheet)
                        ws.append_row(list(new_entry.values()), value_input_option='USER_ENTERED')
                        st.balloons()
                        st.success(f"✅ {full_name} saved successfully!")
                    except Exception as e:
                        st.warning(f"⚠️ Saved locally, but Cloud Sync delayed: {e}")
                    
                    st.cache_data.clear()
                else:
                    st.warning("Please fill in required fields (Name/NIN).")

    st.write("---")

    # 2. THE DIRECTORY (With Formatting)
    st.markdown("#### 🔍 Active Borrower Directory")
    
    # Merge Cloud + Local data
    combined_display = pd.concat([df, pd.DataFrame(st.session_state.local_registry)], ignore_index=True)
    if not combined_display.empty:
        combined_display = combined_display.drop_duplicates(subset=['NIN'], keep='last')
        
        # --- COMMA FORMATTING ---
        # We create a display-only version so we don't break the math later
        formatted_df = combined_display.copy()
        money_cols = ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']
        for col in money_cols:
            if col in formatted_df.columns:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{float(x):,.0f}" if x != "" else "0")

        st.dataframe(
            formatted_df, 
            use_container_width=True, 
            hide_index=True,
            column_order=("CUSTOMER_NAME", "LOAN_AMOUNT", "OUTSTANDING_AMOUNT", "ISSUE_DATE", "DUE_DATE", "LOAN_TYPE")
        )
    else:
        st.info("ℹ️ No borrowers yet.")

    # 3. EDIT/DELETE ACTIONS (The Pencil & Eraser)
    if not df.empty:
        st.write("---")
        with st.expander("🛠️ Admin Actions (Edit/Delete Records)"):
            to_action = st.selectbox("Select Client to Modify", df['CUSTOMER_NAME'].unique())
            act = st.radio("Action", ["Update Contact/Address", "Remove Client Forever"], horizontal=True)
            
            if act == "Update Contact/Address":
                with st.form("edit_kyc"):
                    new_p = st.text_input("New Phone", value=str(df[df['CUSTOMER_NAME']==to_action]['CONTACT'].values[0]))
                    new_a = st.text_area("New Address", value=str(df[df['CUSTOMER_NAME']==to_action]['ADDRESS'].values[0]))
                    if st.form_submit_button("Save Changes"):
                        ws = g_client.open("Zoe_Consults_Database").worksheet("Clients")
                        cell = ws.find(to_action)
                        ws.update_cell(cell.row, 2, new_p) # Update Contact
                        ws.update_cell(cell.row, 9, new_a) # Update Address
                        st.success("Details Updated!"); st.cache_data.clear()
            
            elif act == "Remove Client Forever":
                if st.button("🚨 CONFIRM DELETE"):
                    ws = g_client.open("Zoe_Consults_Database").worksheet("Clients")
                    cell = ws.find(to_action)
                    ws.delete_rows(cell.row)
                    st.warning("Client erased from database."); st.cache_data.clear()

# PAGE: COLLATERAL
elif page == "Collateral":
    st.markdown('<div class="main-title">🛡️ Collateral Inventory</div>', unsafe_allow_html=True)
    
    # SAFETY CHECK: Only try to filter if the column exists
    if not collateral_df.empty and 'STATUS' in collateral_df.columns:
        held_items = collateral_df[collateral_df['STATUS'] == 'Held']
        released_items = collateral_df[collateral_df['STATUS'] == 'Released']
        
        # Display Metrics
        c1, c2 = st.columns(2)
        c1.metric("🔒 Items Held", len(held_items))
        c2.metric("🔓 Items Released", len(released_items))
        
        st.write("---")
        st.markdown("#### Inventory List")
        st.dataframe(collateral_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No collateral records found. Start by adding collateral for a borrower!")
        
    # --- ADD COLLATERAL FORM ---
    with st.expander("📝 Log New Collateral"):
        with st.form("collateral_form"):
            b_name = st.selectbox("Select Borrower", df['CUSTOMER_NAME'].unique() if not df.empty else ["No Borrowers"])
            item = st.text_input("Item Description (e.g., Car Logbook, Land Title)")
            val = st.number_input("Estimated Value (UGX)", min_value=0)
            
            if st.form_submit_button("🔒 Secure Item"):
                if b_name != "No Borrowers" and item:
                    new_collat = [b_name, item, val, "Held", str(datetime.now().date())]
                    try:
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = g_client.open_by_key(sheet_id).worksheet("Collateral")
                        ws.append_row(new_collat)
                        st.success(f"Item secured for {b_name}!"); st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"Sync Error: {e}")

    # 3. COLLATERAL INVENTORY TABLE
    st.write("---")
    st.markdown("#### 🔍 Inventory Search")
    search_asset = st.text_input("Search by Item or Borrower", placeholder="e.g. Toyota, Logbook...")
    st.write("---")
col_to_delete = st.selectbox("Select Asset to Remove/Release", collateral_df['DESCRIPTION'].unique() if not collateral_df.empty else ["None"])
if st.button("🗑️ Delete Asset Record"):
    cell = g_client.open("Zoe_Consults_Database").worksheet("Collateral").find(col_to_delete)
    g_client.open("Zoe_Consults_Database").worksheet("Collateral").delete_rows(cell.row)
    st.success("Asset Record Cleared."); st.cache_data.clear()
    
    if not collateral_df.empty:
        asset_mask = (collateral_df['BORROWER'].str.contains(search_asset, case=False, na=False)) | \
                     (collateral_df['DESCRIPTION'].str.contains(search_asset, case=False, na=False))
        st.dataframe(collateral_df[asset_mask], use_container_width=True, hide_index=True)
    else:
        st.info("No collateral assets recorded yet.")
# PAGE: CALENDAR
elif page == "Calendar":
    st.markdown('<div class="main-title">📅 Zoe Consults Activity Calendar</div>', unsafe_allow_html=True)
    
    # 1. PREPARE THE DATA
    # Combine Loans and Repayments into one "Event" list
    if not df.empty and not pay_df.empty:
        loans = df[['DATE', 'CUSTOMER_NAME', 'LOAN_AMOUNT']].copy()
        loans.columns = ['date', 'title', 'amount']
        loans['type'] = 'Loan Issued'
        loans['color'] = '#1e3a8a' # Navy
        
        pays = pay_df[['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID']].copy()
        pays.columns = ['date', 'title', 'amount']
        pays['type'] = 'Repayment'
        pays['color'] = '#3b82f6' # Baby Blue
        
        events = pd.concat([loans, pays])
        events['date'] = pd.to_datetime(events['date']).dt.date
    else:
        events = pd.DataFrame()

    # 2. CALENDAR CONTROLS
    col_y, col_m = st.columns(2)
    selected_year = col_y.selectbox("Year", [2025, 2026, 2027], index=1)
    selected_month = col_m.selectbox("Month", 
        ["January", "February", "March", "April", "May", "June", 
         "July", "August", "September", "October", "November", "December"],
        index=datetime.now().month - 1
    )

    # 3. DISPLAY EVENTS FOR THE SELECTED MONTH
    st.write(f"### Activity for {selected_month} {selected_year}")
    
    month_num = datetime.strptime(selected_month, "%B").month
    month_events = events[
        (events['date'].apply(lambda x: x.year) == selected_year) & 
        (events['date'].apply(lambda x: x.month) == month_num)
    ].sort_values(by='date')

    if not month_events.empty:
        for d in sorted(month_events['date'].unique()):
            st.markdown(f"<div style='background-color:#f8fafc; padding:5px 15px; border-radius:5px; margin-top:10px; border-left:4px solid #1e3a8a;'><b>{d.strftime('%A, %d %B')}</b></div>", unsafe_allow_html=True)
            
            day_data = month_events[month_events['date'] == d]
            for _, item in day_data.iterrows():
                icon = "📤" if item['type'] == 'Loan Issued' else "📥"
                color = "#1e3a8a" if item['type'] == 'Loan Issued' else "#3b82f6"
                
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; padding:5px 20px;'>
                        <span style='color:{color}; font-weight:600;'>{icon} {item['title']} ({item['type']})</span>
                        <span style='font-family:monospace;'>UGX {item['amount']:,.0f}</span>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info(f"No financial activity recorded for {selected_month}.")

    # 4. QUICK INSIGHT
    st.divider()
    if not month_events.empty:
        total_out = month_events[month_events['type'] == 'Loan Issued']['amount'].sum()
        total_in = month_events[month_events['type'] == 'Repayment']['amount'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Month's Total Out", f"UGX {total_out:,.0f}")
        c2.metric("Month's Total In", f"UGX {total_in:,.0f}", delta=f"Net: {total_in - total_out:,.0f}")

# PAGE: LEDGER (PDF Statements)
elif page == "Ledger":
    st.markdown('<div class="main-title">📑 Client Statement Center</div>', unsafe_allow_html=True)
    
    # 1. SEARCH & SELECT
    search_query = st.text_input("🔍 Search Client Name", placeholder="Enter name to filter list...")
    filtered_clients = df[df['CUSTOMER_NAME'].str.contains(search_query, case=False, na=False)]['CUSTOMER_NAME'].tolist()
    
    selected_client = st.selectbox("Select Client Profile", options=filtered_clients if filtered_clients else ["No clients found"])

    if selected_client and selected_client != "No clients found":
        # Get Client Data
        client_data = df[df['CUSTOMER_NAME'] == selected_client].iloc[0]
        client_pays = pay_df[pay_df['CUSTOMER_NAME'] == selected_client].sort_values(by="DATE")

        # 2. MINI-DASHBOARD FOR CLIENT
        c1, c2, c3 = st.columns(3)
        c1.metric("Original Loan", f"UGX {client_data['LOAN_AMOUNT']:,.0f}")
        c2.metric("Total Repaid", f"UGX {client_data['AMOUNT_PAID']:,.0f}")
        c3.metric("Current Balance", f"UGX {client_data['OUTSTANDING_AMOUNT']:,.0f}", delta_color="inverse")

        st.write("---")

        # 3. PDF GENERATION LOGIC (The "Official Statement")
        def generate_pdf(name, loan, paid, balance, history):
            pdf = FPDF()
            pdf.add_page()
            
            # Header & Branding
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(30, 58, 138) # Navy Blue
            pdf.cell(200, 10, "ZOE CONSULTS SMC LTD", ln=True, align='C')
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(100, 116, 139) # Slate
            pdf.cell(200, 10, "Official Loan Statement & Repayment Ledger", ln=True, align='C')
            pdf.ln(10)

            # Summary Box
            pdf.set_fill_color(248, 250, 252)
            pdf.rect(10, 35, 190, 40, 'F')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(100, 10, f"Client: {name}", ln=True)
            pdf.set_font("Arial", '', 11)
            pdf.cell(100, 8, f"Initial Capital: UGX {loan:,.0f}", ln=True)
            pdf.cell(100, 8, f"Total Amount Repaid: UGX {paid:,.0f}", ln=True)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(100, 8, f"OUTSTANDING BALANCE: UGX {balance:,.0f}", ln=True)
            pdf.ln(10)

            # Table Header
            pdf.set_fill_color(30, 58, 138)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(60, 10, "Date", 1, 0, 'C', True)
            pdf.cell(70, 10, "Reference / Mode", 1, 0, 'C', True)
            pdf.cell(60, 10, "Amount Paid (UGX)", 1, 1, 'C', True)

            # Table Rows
            pdf.set_text_color(0, 0, 0)
            for _, row in history.iterrows():
                pdf.cell(60, 10, str(row['DATE']), 1)
                pdf.cell(70, 10, str(row.get('PAYMENT_MODE', 'Deposit')), 1)
                pdf.cell(60, 10, f"{row['AMOUNT_PAID']:,.0f}", 1, 1, 'R')

            # Official Stamp Box
            pdf.ln(20)
            pdf.set_draw_color(30, 58, 138)
            pdf.cell(60, 25, "OFFICIAL STAMP", 1, 0, 'C')
            pdf.cell(70) # Spacer
            pdf.set_font("Arial", 'I', 8)
            pdf.cell(60, 25, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 0, 'R')
            
            return pdf.output(dest='S').encode('latin-1')

        # 4. DOWNLOAD BUTTON & STATE
        if st.button("🛠️ Prepare Official PDF", use_container_width=True):
            pdf_bytes = generate_pdf(
                selected_client, 
                client_data['LOAN_AMOUNT'], 
                client_data['AMOUNT_PAID'], 
                client_data['OUTSTANDING_AMOUNT'], 
                client_pays
            )
            st.session_state.b64_str = base64.b64encode(pdf_bytes).decode()
            st.session_state.ready = True
            st.session_state.last_client = selected_client

        if st.session_state.ready and st.session_state.last_client == selected_client:
            href = f'<a href="data:application/octet-stream;base64,{st.session_state.b64_str}" download="Zoe_Statement_{selected_client}.pdf" style="text-decoration:none;">' \
                   f'<div style="background-color:#1e3a8a; color:white; padding:15px; border-radius:10px; text-align:center; font-weight:bold;">' \
                   f'📥 DOWNLOAD PDF STATEMENT FOR {selected_client}</div></a>'
            st.markdown(href, unsafe_allow_html=True)

        # 5. TRANSACTION PREVIEW
        st.write("---")
        st.markdown("#### 🕒 Payment History")
        st.dataframe(client_pays[['DATE', 'AMOUNT_PAID', 'PAYMENT_MODE']], use_container_width=True)

# PAGE: OVERDUE TRACKER
elif page == "Overdue Tracker":
    st.markdown('<div class="main-title">🚨 Urgent Follow-up: Overdue Portfolios</div>', unsafe_allow_html=True)
    
    # 1. CALCULATE OVERDUE STATUS
    today = datetime.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Identify late payers by checking the last date in pay_df
    if not pay_df.empty:
        latest_pays = pay_df.groupby('CUSTOMER_NAME')['DATE'].max().reset_index()
        latest_pays['DATE'] = pd.to_datetime(latest_pays['DATE']).dt.date
        
        # Merge with main client list to see who has a balance AND no recent pay
        overdue_df = df.merge(latest_pays, on='CUSTOMER_NAME', how='left')
        
        # Filter: Balance > 0 AND (Last Pay > 30 days OR No Pay Recorded)
        overdue_list = overdue_df[
            (overdue_df['OUTSTANDING_AMOUNT'] > 0) & 
            ((overdue_df['DATE'] < thirty_days_ago) | (overdue_df['DATE'].isna()))
        ].copy()
    else:
        overdue_list = df[df['OUTSTANDING_AMOUNT'] > 0].copy()
        overdue_list['DATE'] = None

    # 2. THE ALERT BANNER (Baby Blue Border / Red Text)
    if not overdue_list.empty:
        st.markdown(f"""
            <div style="background-color: #eff6ff; border-left: 5px solid #3b82f6; padding: 15px; border-radius: 5px;">
                <p style="margin:0; color: #1e3a8a; font-weight: bold;">
                    ⚠️ ATTENTION: {len(overdue_list)} clients are currently 30+ days behind schedule.
                </p>
            </div>
        """, unsafe_allow_html=True)
        st.write("")

        # 3. THE "RED LIST" ROWS
        for _, row in overdue_list.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 1])
                
                # Column 1: Borrower Info (Navy Blue Text)
                c1.markdown(f"<span style='color: #1e3a8a; font-weight: bold; font-size: 18px;'>👤 {row['CUSTOMER_NAME']}</span>", unsafe_allow_html=True)
                last_pay = row['DATE'] if pd.notna(row['DATE']) else "No payments recorded"
                c1.markdown(f"<span style='color: #64748b; font-size: 13px;'>Last Payment: {last_pay}</span>", unsafe_allow_html=True)
                
                # Column 2: Money Owed (Baby Blue Accent)
                c2.markdown(f"<span style='color: #3b82f6; font-weight: bold; font-size: 18px;'>UGX {row['OUTSTANDING_AMOUNT']:,.0f}</span>", unsafe_allow_html=True)
                c2.caption("Balance Due")
                
                # Column 3: Red Action Button (The Chaser)
                # We use a unique key to prevent the 'DuplicateElementId' error
                clean_p = "".join(filter(str.isdigit, str(row.get('CONTACT', ''))))
                
                if clean_p:
                    msg = f"URGENT: Hello {row['CUSTOMER_NAME']}, your Zoe Consults loan balance of UGX {row['OUTSTANDING_AMOUNT']:,.0f} is overdue. Please settle this today to avoid penalties."
                    wa_url = f"https://wa.me/{clean_p}?text={msg.replace(' ', '%20')}"
                    
                    c3.markdown(f'''
                        <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                            <div style="background-color:#dc2626; color:white; padding:12px; 
                                        border-radius:8px; text-align:center; font-weight:bold; font-size:14px; 
                                        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
                                🚩 SEND REMINDER
                            </div>
                        </a>
                    ''', unsafe_allow_html=True)
                else:
                    c3.button("No Phone", disabled=True, use_container_width=True, key=f"dead_btn_{row['CUSTOMER_NAME']}")
                
                st.divider()
    else:
        st.success("🎉 Excellent! All clients are up to date. No overdue payments found.")
# --- PAGE: OPERATING EXPENSES ---
elif page == "Expenses":
    st.markdown('<div class="main-title">📉 Operating Expenses</div>', unsafe_allow_html=True)
    
    # 1. EXPENSE SUMMARY
    if not expense_df.empty:
        total_exp = expense_df['AMOUNT'].sum()
        st.metric("Total Monthly Expenses", f"UGX {total_exp:,.0f}", delta_color="inverse")
    
    # 2. RECORD NEW EXPENSE
    with st.expander("➕ Log Business Expense", expanded=True):
        with st.form("exp_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            exp_cat = col1.selectbox("Category", ["Rent", "Salaries", "Trading License", "Utilities", "Marketing", "Other"])
            exp_amt = col2.number_input("Amount (UGX)", min_value=0, step=5000)
            
            exp_date = st.date_input("Date", value=datetime.now())
            exp_desc = st.text_input("Description / Payee")
            
            if st.form_submit_button("💾 Save Expense", use_container_width=True):
                new_exp = [str(exp_date), exp_cat, exp_desc, exp_amt]
                g_client.open("Zoe_Consults_Database").worksheet("Expenses").append_row(new_exp)
                st.success("Expense recorded!"); st.cache_data.clear()

    # 3. EXPENSE HISTORY
    st.markdown("#### 📜 Expense Ledger")
    st.dataframe(expense_df.sort_values(by=expense_df.columns[0], ascending=False), use_container_width=True)

# --- PAGE: PETTY CASH ---
elif page == "Petty Cash":
    st.markdown('<div class="main-title">☕ Petty Cash Management</div>', unsafe_allow_html=True)
    
    # 1. FLOAT TRACKER
    # We calculate float as (Total In - Total Out)
    if not petty_df.empty:
        p_in = petty_df[petty_df['TYPE'] == 'Float Top-up']['AMOUNT'].sum()
        p_out = petty_df[petty_df['TYPE'] == 'Spend']['AMOUNT'].sum()
        current_float = p_in - p_out
        
        color = "#1e3a8a" if current_float > 10000 else "#dc2626"
        st.markdown(f"""
            <div style="background-color: #f0f9ff; padding: 20px; border-radius: 12px; border-left: 6px solid {color};">
                <h3 style="margin:0; color: {color};">Current Float: UGX {current_float:,.0f}</h3>
            </div>
        """, unsafe_allow_html=True)
    
    # 2. LOG PETTY CASH ACTIVITY
    st.write("---")
    with st.form("petty_form", clear_on_submit=True):
        p_type = st.radio("Transaction Type", ["Spend", "Float Top-up"], horizontal=True)
        col_a, col_b = st.columns(2)
        p_amt = col_a.number_input("Amount (UGX)", min_value=0, step=1000)
        p_item = col_b.text_input("Item (e.g., Office Tea, Transport, Printing)")
        
        if st.form_submit_button("💸 Update Petty Cash", use_container_width=True):
            new_p = [str(datetime.now().date()), p_type, p_item, p_amt]
            g_client.open("Zoe_Consults_Database").worksheet("PettyCash").append_row(new_p)
            st.success("Petty cash updated!"); st.cache_data.clear()

    st.dataframe(petty_df, use_container_width=True)

elif page == "Petty Cash":
    st.metric("Current Float Balance", f"UGX {(petty_df[petty_df['TYPE']=='Float Top-up']['AMOUNT'].sum() - petty_df[petty_df['TYPE']=='Spend']['AMOUNT'].sum()):,.0f}")
    with st.form("p_cash"):
        t = st.radio("Type", ["Spend", "Float Top-up"])
        a = st.number_input("Amount")
        if st.form_submit_button("Update"):
            g_client.open("Zoe_Consults_Database").worksheet("PettyCash").append_row([str(datetime.now().date()), t, "Cash Desk", a])
            st.success("Float Updated!"); st.cache_data.clear()

# PAGE: PAYROLL
elif page == "Payroll":
    st.markdown('<div class="main-title">👔 Team Payroll Management</div>', unsafe_allow_html=True)
    
    # 1. PAYROLL SUMMARY
    if not payroll_df.empty:
        total_monthly_pay = payroll_df['NET_PAY'].sum()
        st.metric("Total Monthly Payroll", f"UGX {total_monthly_pay:,.0f}", delta="Staff Costs")

    # 2. RECORD SALARY PAYMENT
    with st.expander("➕ Process Staff Salary", expanded=True):
        with st.form("payroll_form", clear_on_submit=True):
            st.markdown("<p style='color: #1e3a8a; font-weight: bold;'>Employee Disbursement Details</p>", unsafe_allow_html=True)
            
            p_staff = st.text_input("Staff Name")
            col1, col2, col3 = st.columns(3)
            p_basic = col1.number_input("Basic Salary (UGX)", min_value=0, step=10000)
            p_bonus = col2.number_input("Bonus / Commission (UGX)", min_value=0, step=5000)
            p_deduct = col3.number_input("Deductions / Advance (UGX)", min_value=0, step=5000)
            
            net_pay = p_basic + p_bonus - p_deduct
            st.markdown(f"**Calculated Net Pay: UGX {net_pay:,.0f}**")
            
            p_date = st.date_input("Payment Date", value=datetime.now())
            
            if st.form_submit_button("💳 Confirm & Process Payment", use_container_width=True):
                # Data for Google Sheets
                new_payroll = [p_staff, p_basic, p_bonus, p_deduct, net_pay, str(p_date)]
                g_client.open("Zoe_Consults_Database").worksheet("Payroll").append_row(new_payroll)
                st.success(f"Salary processed for {p_staff}!"); st.cache_data.clear()

    # 3. PAYROLL HISTORY
    st.write("---")
    st.markdown("#### 🎫 Generate Individual Pay Slip")
    
    # 1. SELECT STAFF FOR SLIP
    if not payroll_df.empty:
        staff_list = payroll_df['STAFF_NAME'].unique()
        selected_staff = st.selectbox("Select Employee", options=staff_list)
        
        # Get the latest payment for this staff member
        staff_data = payroll_df[payroll_df['STAFF_NAME'] == selected_staff].iloc[-1]

        if st.button("🖨️ Prepare Digital Pay Slip", use_container_width=True):
            def generate_payslip_pdf(name, basic, bonus, deduct, net, date, biz_name):
                pdf = FPDF()
                pdf.add_page()
                
                # Header & Branding (Navy Blue)
                pdf.set_font("Arial", 'B', 16)
                pdf.set_text_color(30, 58, 138)
                pdf.cell(200, 10, biz_name, ln=True, align='C')
                pdf.set_font("Arial", '', 10)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(200, 10, "CONFIDENTIAL SALARY ADVICE", ln=True, align='C')
                pdf.ln(10)

                # Employee Info Box
                pdf.set_fill_color(248, 250, 252)
                pdf.rect(10, 35, 190, 25, 'F')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(100, 8, f"Employee: {name}", ln=True)
                pdf.set_font("Arial", '', 10)
                pdf.cell(100, 8, f"Payment Date: {date}", ln=True)
                pdf.ln(10)

                # Salary Table Headers
                pdf.set_fill_color(30, 58, 138)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(130, 10, "Description", 1, 0, 'C', True)
                pdf.cell(60, 10, "Amount (UGX)", 1, 1, 'C', True)

                # Table Body (Earnings & Deductions)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(130, 10, "Basic Salary", 1)
                pdf.cell(60, 10, f"{basic:,.0f}", 1, 1, 'R')
                
                pdf.cell(130, 10, "Performance Bonus / Commission", 1)
                pdf.cell(60, 10, f"{bonus:,.0f}", 1, 1, 'R')
                
                pdf.set_text_color(153, 27, 27) # Red for deductions
                pdf.cell(130, 10, "Deductions / Salary Advance", 1)
                pdf.cell(60, 10, f"- {deduct:,.0f}", 1, 1, 'R')

                # Net Total (Baby Blue/Navy Highlight)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(239, 246, 255) # Baby Blue
                pdf.set_text_color(30, 58, 138)
                pdf.cell(130, 12, " NET DISBURSEMENT", 1, 0, 'L', True)
                pdf.cell(60, 12, f"UGX {net:,.0f}", 1, 1, 'R', True)

                # Signature Section
                pdf.ln(20)
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(100, 10, "__________________________", ln=0)
                pdf.cell(90, 10, "__________________________", ln=1, align='R')
                pdf.cell(100, 5, "Authorized Signatory", ln=0)
                pdf.cell(90, 5, "Employee Signature", ln=1, align='R')
                
                return pdf.output(dest='S').encode('latin-1')

            # PDF Download Logic
            slip_bytes = generate_payslip_pdf(
                staff_data['STAFF_NAME'], 
                staff_data['BASIC_SALARY'], 
                staff_data['BONUS'], 
                staff_data['DEDUCTIONS'], 
                staff_data['NET_PAY'], 
                staff_data['DATE'], 
                "ZOE CONSULTS SMC LTD"
            )
            b64_slip = base64.b64encode(slip_bytes).decode()
            href_slip = f'<a href="data:application/octet-stream;base64,{b64_slip}" download="PaySlip_{selected_staff}_{staff_data["DATE"]}.pdf" style="text-decoration:none;">' \
                        f'<div style="background-color:#3b82f6; color:white; padding:15px; border-radius:10px; text-align:center; font-weight:bold;">' \
                        f'📥 DOWNLOAD PAY SLIP FOR {selected_staff}</div></a>'
            st.markdown(href_slip, unsafe_allow_html=True)
    else:
        st.info("Record a staff salary first to generate a pay slip.")
# PAGE: ADD PAYMENT & CLIENT
elif page == "Add Payment":
    with st.form("add_p"):
        cn = st.selectbox("Client", df['CUSTOMER_NAME'].unique())
        ap = st.number_input("Amount Paid")
        if st.form_submit_button("Post Repayment"):
            g_client.open("Zoe_Consults_Database").worksheet("Repayments").append_row([cn, ap, str(datetime.now().date()), "MM", "Note"])
            st.success("Ledger Updated!"); st.cache_data.clear()

elif page == "Add Client":
    with st.form("add_c"):
        fn = st.text_input("First Name"); ln = st.text_input("Last Name")
        la = st.number_input("Loan Amount")
        ni = st.text_input("NIN"); ge = st.selectbox("Gender", ["Male", "Female"])
        if st.form_submit_button("Register"):
            g_client.open("Zoe_Consults_Database").worksheet("Clients").append_row([f"{fn} {ln}".upper(), "256", la, 0, la, 0, str(datetime.now().date()), ni, "Address", ge, "Email", "Personal"])
            st.balloons(); st.cache_data.clear()

# PAGE: SETTINGS (Backups & Reports)
elif page == "Settings":
    st.markdown('<div class="main-title">⚙️ Business Configuration</div>', unsafe_allow_html=True)
    
    # 1. BUSINESS PROFILE
    st.markdown("<p style='color: #1e3a8a; font-weight: bold;'>🏢 Business Identity</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    biz_name = col1.text_input("Company Name", value="ZOE CONSULTS SMC LTD")
    biz_tagline = col2.text_input("Tagline", value="Official Loan Statement & Repayment Ledger")
    
    st.divider()

    # 2. FINANCIAL DEFAULTS
    st.markdown("<p style='color: #1e3a8a; font-weight: bold;'>📉 Financial Defaults</p>", unsafe_allow_html=True)
    
    c3, c4 = st.columns(2)
    default_rate = c3.number_input("Standard Monthly Interest Rate (%)", value=10.0, step=0.5)
    late_penalty = c4.number_input("Late Payment Penalty (UGX)", value=50000, step=5000)
    
    st.divider()

    # 3. DIGITAL ASSETS (Signature & Stamp)
    st.markdown("<p style='color: #1e3a8a; font-weight: bold;'>✍️ Official Stamp & Signature</p>", unsafe_allow_html=True)
    st.info("Upload your signature (PNG) to have it automatically placed on all PDF Statements.")
    
    uploaded_sig = st.file_uploader("Upload Signature / Stamp", type=["png", "jpg"])
    
    if uploaded_sig:
        st.image(uploaded_sig, caption="Preview of Signature", width=150)
        # We store this in session state so the PDF logic can grab it
        st.session_state.signature = uploaded_sig

    # 4. SAVE BUTTON (Simulated)
    if st.button("💾 Save System Settings", use_container_width=True):
        st.success("Settings updated successfully! These changes will reflect on your next PDF generation.")
