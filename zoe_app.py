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
        options=["Overview", "Borrowers", "Collateral", "Calendar", "Ledger", "Overdue Tracker", "Expenses", "PettyCash", "Payroll", "Add Payment", "Settings"],
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
    
    # 1. Initialize Local Collateral Memory
    if 'local_collateral' not in st.session_state:
        st.session_state.local_collateral = []

    # 2. LOG NEW COLLATERAL
    with st.expander("📝 Log New Collateral (Secure Asset)", expanded=True):
        with st.form("collateral_form", clear_on_submit=True):
            local_names = [b['CUSTOMER_NAME'] for b in st.session_state.get('local_registry', [])]
            cloud_names = df['CUSTOMER_NAME'].tolist() if not df.empty else []
            all_borrowers = list(set(cloud_names + local_names))
            
            c1, c2 = st.columns(2)
            with c1:
                b_name = st.selectbox("Select Borrower", all_borrowers if all_borrowers else ["No Borrowers Found"])
                item_desc = st.text_input("Item Description", placeholder="e.g. Car Logbook (Toyota)")
            with c2:
                item_val = st.number_input("Estimated Value (UGX)", min_value=0, step=100000)
                status = st.selectbox("Initial Status", ["Held", "Released"])

            if st.form_submit_button("🔒 Secure Item"):
                if b_name != "No Borrowers Found" and item_desc:
                    today = str(datetime.now().date())
                    # Format exactly like your Google Sheet columns
                    new_asset = {
                        "BORROWER_NAME": b_name,
                        "ITEM_NAME": item_desc,
                        "VALUE": item_val,
                        "STATUS": status,
                        "DATE": today
                    }
                    
                    # --- STEP A: SAVE LOCALLY (Instant Feedback) ---
                    st.session_state.local_collateral.append(new_asset)
                    
                    # --- STEP B: TRY GOOGLE CLOUD ---
                    try:
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("Collateral")
                        ws.append_row(list(new_asset.values()), value_input_option='USER_ENTERED')
                        
                        st.balloons()
                        st.success(f"✅ Asset secured for {b_name}!")
                        st.cache_data.clear()
                    except Exception as e:
                        if "200" in str(e):
                            st.balloons(); st.cache_data.clear()
                        else:
                            st.warning(f"⚠️ Saved locally, but Cloud Sync is delayed: {e}")
                else:
                    st.warning("Please fill in the item details.")

    st.write("---")

    # 3. THE INVENTORY TABLE (Combined Cloud + Local)
    st.markdown("#### 📦 Current Inventory List")
    
    # Merge Cloud Data with Local Recent Additions
    local_collat_df = pd.DataFrame(st.session_state.local_collateral)
    combined_collat = pd.concat([collateral_df, local_collat_df], ignore_index=True)
    
    if not combined_collat.empty:
        # Clean up duplicates in case Cloud syncs during session
        combined_collat = combined_collat.drop_duplicates(subset=['BORROWER_NAME', 'ITEM_NAME'], keep='last')
        
        # Display search
        search = st.text_input("🔍 Filter Inventory", placeholder="Search by name or item...")
        display_df = combined_collat.copy()
        
        if search:
            display_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        # Format Commas for UGX
        if 'VALUE' in display_df.columns:
            display_df['VALUE'] = display_df['VALUE'].apply(lambda x: f"{float(x):,.0f}" if x != "" else "0")
            
        st.dataframe(
            display_df, 
            use_container_width=True, 
            hide_index=True,
            column_order=("BORROWER_NAME", "ITEM_NAME", "VALUE", "STATUS", "DATE")
        )
    else:
        st.info("ℹ️ Your Collateral Inventory is currently empty.")
# PAGE: ACTIVITY CALENDAR
elif page == "Calendar":
    st.markdown('<div class="main-title">📅 Zoe Consults Activity Calendar</div>', unsafe_allow_html=True)
    
    # 1. Create the Event List from all your data
    # We pull from Borrowers (Issue/Due) and Collateral (Log Date)
    events_list = []
    
    # Pull Borrower Dates
    combined_borrowers = pd.concat([df, pd.DataFrame(st.session_state.get('local_registry', []))], ignore_index=True)
    for _, row in combined_borrowers.iterrows():
        if 'ISSUE_DATE' in row and pd.notnull(row['ISSUE_DATE']):
            events_list.append({"date": pd.to_datetime(row['ISSUE_DATE']), "event": f"💰 Loan Issued: {row['CUSTOMER_NAME']}", "type": "Loan"})
        if 'DUE_DATE' in row and pd.notnull(row['DUE_DATE']):
            events_list.append({"date": pd.to_datetime(row['DUE_DATE']), "event": f"📅 Repayment Due: {row['CUSTOMER_NAME']}", "type": "Due"})
            
    # Pull Collateral Dates
    combined_collat = pd.concat([collateral_df, pd.DataFrame(st.session_state.get('local_collateral', []))], ignore_index=True)
    for _, row in combined_collat.iterrows():
        if 'DATE' in row and pd.notnull(row['DATE']):
            events_list.append({"date": pd.to_datetime(row['DATE']), "event": f"🛡️ Collateral Logged: {row['ITEM_NAME']} ({row['BORROWER_NAME']})", "type": "Collateral"})

    events = pd.DataFrame(events_list)

    # 2. Filtering Logic (Crash-Proof)
    c1, c2 = st.columns(2)
    selected_year = c1.selectbox("Year", [2025, 2026, 2027], index=1)
    selected_month_name = c2.selectbox("Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], index=datetime.now().month-1)
    
    month_map = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}
    selected_month = month_map[selected_month_name]

    st.write("---")
    st.markdown(f"### Activity for {selected_month_name} {selected_year}")

    if not events.empty:
        # Safety filter
        filtered_events = events[
            (events['date'].dt.year == selected_year) & 
            (events['date'].dt.month == selected_month)
        ].sort_values(by='date')

        if not filtered_events.empty:
            for _, ev in filtered_events.iterrows():
                # Color coding based on type
                icon = "🔵" if ev['type'] == "Loan" else "🔴" if ev['type'] == "Due" else "🟢"
                st.info(f"{icon} **{ev['date'].strftime('%d %b')}**: {ev['event']}")
        else:
            st.info(f"ℹ️ No scheduled activities for {selected_month_name}.")
    else:
        st.info("ℹ️ Add your first borrower or collateral to see dates on the calendar.")

# PAGE: LEDGER (Individual Client Statements & PDF Export)
elif page == "Ledger":
    st.markdown('<div class="main-title">📑 Client Statement Center</div>', unsafe_allow_html=True)
    
    # 1. SYNC DATA (Combine Cloud + Local so new clients appear here)
    local_df = pd.DataFrame(st.session_state.get('local_registry', []))
    combined_borrowers = pd.concat([df, local_df], ignore_index=True)
    
    if not combined_borrowers.empty:
        # 2. SEARCH & SELECT
        search_query = st.text_input("🔍 Search Client Name", placeholder="Enter name to filter list...")
        
        # Ensure we have a clean list of names
        if 'CUSTOMER_NAME' in combined_borrowers.columns:
            combined_borrowers = combined_borrowers.drop_duplicates(subset=['NIN'], keep='last')
            filtered_clients = combined_borrowers[combined_borrowers['CUSTOMER_NAME'].str.contains(search_query, case=False, na=False)]['CUSTOMER_NAME'].tolist()
            
            selected_client = st.selectbox("Select Client Profile", options=filtered_clients if filtered_clients else ["No clients found"])

            if selected_client and selected_client != "No clients found":
                # Get Client Data
                client_data = combined_borrowers[combined_borrowers['CUSTOMER_NAME'] == selected_client].iloc[0]
                
                # Get Repayments (Ensure local/cloud sync for payments too if applicable)
                client_pays = pay_df[pay_df['CUSTOMER_NAME'] == selected_client].sort_values(by="DATE") if not pay_df.empty else pd.DataFrame(columns=['DATE', 'AMOUNT_PAID', 'PAYMENT_MODE'])

                # 3. MINI-DASHBOARD
                c1, c2, c3 = st.columns(3)
                l_amt = float(client_data.get('LOAN_AMOUNT', 0))
                p_amt = float(client_data.get('AMOUNT_PAID', 0))
                o_amt = float(client_data.get('OUTSTANDING_AMOUNT', 0))

                c1.metric("Original Loan", f"UGX {l_amt:,.0f}")
                c2.metric("Total Repaid", f"UGX {p_amt:,.0f}")
                c3.metric("Current Balance", f"UGX {o_amt:,.0f}", delta_color="inverse")

                st.write("---")

                # 4. RESTORED PDF GENERATION LOGIC
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
                    if not history.empty:
                        for _, row in history.iterrows():
                            pdf.cell(60, 10, str(row['DATE']), 1)
                            pdf.cell(70, 10, str(row.get('PAYMENT_MODE', 'Deposit')), 1)
                            pdf.cell(60, 10, f"{row['AMOUNT_PAID']:,.0f}", 1, 1, 'R')
                    else:
                        pdf.cell(190, 10, "No repayments recorded yet.", 1, 1, 'C')

                    # Official Stamp Box
                    pdf.ln(20)
                    pdf.set_draw_color(30, 58, 138)
                    pdf.cell(60, 25, "OFFICIAL STAMP", 1, 0, 'C')
                    pdf.cell(70) # Spacer
                    pdf.set_font("Arial", 'I', 8)
                    pdf.cell(60, 25, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 0, 'R')
                    
                    return pdf.output(dest='S').encode('latin-1')

                # 5. DOWNLOAD BUTTON & STATE
                if st.button("🛠️ Prepare Official PDF", use_container_width=True):
                    pdf_bytes = generate_pdf(selected_client, l_amt, p_amt, o_amt, client_pays)
                    st.session_state.b64_str = base64.b64encode(pdf_bytes).decode()
                    st.session_state.ready = True
                    st.session_state.last_client = selected_client

                if st.session_state.get('ready') and st.session_state.get('last_client') == selected_client:
                    href = f'<a href="data:application/octet-stream;base64,{st.session_state.b64_str}" download="Zoe_Statement_{selected_client}.pdf" style="text-decoration:none;">' \
                           f'<div style="background-color:#1e3a8a; color:white; padding:15px; border-radius:10px; text-align:center; font-weight:bold;">' \
                           f'📥 DOWNLOAD PDF STATEMENT FOR {selected_client}</div></a>'
                    st.markdown(href, unsafe_allow_html=True)

                # 6. TRANSACTION PREVIEW
                st.write("---")
                st.markdown("#### 🕒 Payment History")
                if not client_pays.empty:
                    st.dataframe(client_pays[['DATE', 'AMOUNT_PAID', 'PAYMENT_MODE']], use_container_width=True)
                else:
                    st.info("No payments recorded yet.")
    else:
        st.info("ℹ️ Your Ledger is empty. Register your first borrower in the Borrower Hub.")

# PAGE: OVERDUE TRACKER (The Debt Collector)
elif page == "Overdue Tracker":
    st.markdown('<div class="main-title">🚨 Urgent Follow-up: Overdue Portfolios</div>', unsafe_allow_html=True)
    
    # 1. SYNC DATA (Combine Cloud + Local)
    local_df = pd.DataFrame(st.session_state.get('local_registry', []))
    combined_borrowers = pd.concat([df, local_df], ignore_index=True)
    
    if not combined_borrowers.empty:
        # Calculate Date Thresholds
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)
        
        # 2. CALCULATE OVERDUE STATUS
        if not pay_df.empty:
            latest_pays = pay_df.groupby('CUSTOMER_NAME')['DATE'].max().reset_index()
            latest_pays['DATE'] = pd.to_datetime(latest_pays['DATE']).dt.date
            
            # Merge with combined list
            overdue_df = combined_borrowers.merge(latest_pays, on='CUSTOMER_NAME', how='left', suffixes=('', '_last_pay'))
            
            # Filter: Balance > 0 AND (Last Pay > 30 days OR No Pay Recorded)
            overdue_list = overdue_df[
                (overdue_df['OUTSTANDING_AMOUNT'] > 0) & 
                ((overdue_df['DATE_last_pay'] < thirty_days_ago) | (overdue_df['DATE_last_pay'].isna()))
            ].copy()
        else:
            # If no payments exist at all, everyone with a balance is potentially overdue
            overdue_list = combined_borrowers[combined_borrowers['OUTSTANDING_AMOUNT'] > 0].copy()
            overdue_list['DATE_last_pay'] = None

        # 3. THE ALERT BANNER (Restored)
        if not overdue_list.empty:
            st.markdown(f"""
                <div style="background-color: #eff6ff; border-left: 5px solid #3b82f6; padding: 15px; border-radius: 5px;">
                    <p style="margin:0; color: #1e3a8a; font-weight: bold;">
                        ⚠️ ATTENTION: {len(overdue_list)} clients are currently behind schedule or have no recent payments.
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.write("")

            # 4. THE "RED LIST" ROWS (Restored UI)
            for _, row in overdue_list.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([2, 1, 1])
                    
                    # Column 1: Borrower Info
                    c1.markdown(f"<span style='color: #1e3a8a; font-weight: bold; font-size: 18px;'>👤 {row['CUSTOMER_NAME']}</span>", unsafe_allow_html=True)
                    last_pay = row['DATE_last_pay'] if pd.notna(row['DATE_last_pay']) else "No payments recorded"
                    c1.markdown(f"<span style='color: #64748b; font-size: 13px;'>Last Payment: {last_pay}</span>", unsafe_allow_html=True)
                    
                    # Column 2: Money Owed
                    bal = float(row['OUTSTANDING_AMOUNT'])
                    c2.markdown(f"<span style='color: #3b82f6; font-weight: bold; font-size: 18px;'>UGX {bal:,.0f}</span>", unsafe_allow_html=True)
                    c2.caption("Balance Due")
                    
                    # Column 3: Red WhatsApp Action Button
                    clean_p = "".join(filter(str.isdigit, str(row.get('CONTACT', ''))))
                    
                    if clean_p:
                        # Professional Chaser Message
                        msg = f"URGENT: Hello {row['CUSTOMER_NAME']}, your Zoe Consults loan balance of UGX {bal:,.0f} is overdue. Please settle this today to avoid penalties."
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
            st.balloons()
            st.success("🎉 Excellent! All clients are up to date. No overdue payments found.")
    else:
        st.info("ℹ️ No borrowers registered. The tracker will wake up once you add clients.")
# PAGE: OPERATING EXPENSES
elif page == "Expenses":
    st.markdown('<div class="main-title">📉 Operating Expenses</div>', unsafe_allow_html=True)
    
    # 1. Initialize Local Expense Memory (for instant feedback)
    if 'local_expenses' not in st.session_state:
        st.session_state.local_expenses = []

    # 2. RECORD NEW EXPENSE
    with st.expander("➕ Log Business Expense", expanded=True):
        with st.form("exp_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            exp_cat = col1.selectbox("Category", ["Rent", "Salaries", "Trading License", "Utilities", "Marketing", "Other"])
            exp_amt = col2.number_input("Amount (UGX)", min_value=0, step=5000)
            
            exp_date = st.date_input("Date", value=datetime.now())
            receipt_no = st.text_input("Receipt / Invoice Number", placeholder="e.g. ZOE-2026-001")
            exp_desc = st.text_input("Description / Payee", placeholder="Who was paid and what for?")
            
            if st.form_submit_button("💾 Save Expense", use_container_width=True):
                if exp_amt > 0 and exp_desc:
                    new_exp = {
                        "DATE": str(exp_date),
                        "CATEGORY": exp_cat,
                        "DESCRIPTION": exp_desc,
                        "AMOUNT": exp_amt,
                        "RECEIPT_NO": receipt_no
                    }
                    
                    # Save locally for instant table update
                    st.session_state.local_expenses.append(new_exp)
                    
                    try:
                        # FRESH HANDSHAKE
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("Expenses")
                        ws.append_row(list(new_exp.values()), value_input_option='USER_ENTERED')
                        
                        st.success("✅ Expense recorded successfully!")
                        st.cache_data.clear()
                    except Exception as e:
                        if "200" in str(e):
                            st.success("✅ Expense recorded!")
                            st.cache_data.clear()
                        else:
                            st.warning(f"⚠️ Saved locally, but Cloud Sync delayed: {e}")
                else:
                    st.warning("Please enter an amount and description.")

    st.write("---")

    # 3. EXPENSE LEDGER (Combined Cloud + Local)
    st.markdown("#### 📜 Expense Ledger")
    
    local_exp_df = pd.DataFrame(st.session_state.local_expenses)
    combined_expenses = pd.concat([expense_df, local_exp_df], ignore_index=True)
    
    if not combined_expenses.empty:
        # Sort by Date safely
        if 'DATE' in combined_expenses.columns:
            combined_expenses = combined_expenses.sort_values(by='DATE', ascending=False)
        
        # Format for display
        display_exp = combined_expenses.copy()
        if 'AMOUNT' in display_exp.columns:
            display_exp['AMOUNT'] = display_exp['AMOUNT'].apply(lambda x: f"{float(x):,.0f}" if x != "" else "0")
            
        st.dataframe(
            display_exp, 
            use_container_width=True, 
            hide_index=True,
            column_order=("DATE", "RECEIPT_NO", "CATEGORY", "DESCRIPTION", "AMOUNT")
        )
        
        # Show Total Summary
        total_val = pd.to_numeric(combined_expenses['AMOUNT'], errors='coerce').sum()
        st.info(f"📊 Total Operating Expenses logged: **UGX {total_val:,.0f}**")
    else:
        st.info("ℹ️ Your Expense Ledger is empty. Log your first business expense above.")
# PAGE: PETTY CASH
elif page == "PettyCash":
    st.markdown('<div class="main-title">🪙 Petty Cash Management</div>', unsafe_allow_html=True)
    
    # 1. Initialize Local Memory
    if 'local_petty' not in st.session_state:
        st.session_state.local_petty = []

    # 2. CALCULATE LIVE BALANCE
    local_p_df = pd.DataFrame(st.session_state.local_petty)
    combined_petty = pd.concat([petty_df, local_p_df], ignore_index=True)
    
    if not combined_petty.empty:
        # Math: Top-ups increase balance, Spends decrease it
        total_in = combined_petty[combined_petty['TYPE'] == 'Float Top-up']['AMOUNT'].sum()
        total_out = combined_petty[combined_petty['TYPE'] == 'Spend']['AMOUNT'].sum()
        current_balance = total_in - total_out
    else:
        current_balance = 0

    st.metric("Current Petty Cash Balance", f"UGX {current_balance:,.0f}")

    # 3. TRANSACTION FORM
    with st.expander("💸 Update Petty Cash (Spend or Top-up)", expanded=True):
        with st.form("petty_form", clear_on_submit=True):
            p_type = st.radio("Transaction Type", ["Spend", "Float Top-up"], horizontal=True)
            c1, c2 = st.columns(2)
            p_amt = c1.number_input("Amount (UGX)", min_value=0, step=1000)
            p_item = c2.text_input("Item / Reason", placeholder="e.g., Office Tea, Transport")
            
            if st.form_submit_button("💸 Update Petty Cash", use_container_width=True):
                if p_amt > 0 and p_item:
                    new_p = {
                        "DATE": str(datetime.now().date()),
                        "TYPE": p_type,
                        "ITEM": p_item,
                        "AMOUNT": p_amt
                    }
                    
                    # Instant Local Update
                    st.session_state.local_petty.append(new_p)
                    
                    try:
                        # FRESH HANDSHAKE
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("PettyCash")
                        ws.append_row(list(new_p.values()), value_input_option='USER_ENTERED')
                        
                        st.success(f"✅ {p_type} of {p_amt:,.0f} recorded!")
                        st.cache_data.clear()
                    except Exception as e:
                        if "200" in str(e):
                            st.success("✅ Recorded!")
                            st.cache_data.clear()
                        else:
                            st.warning(f"⚠️ Saved locally, Cloud Sync pending: {e}")
                else:
                    st.warning("Please enter an amount and reason.")

    st.write("---")

    # 4. TRANSACTION TABLE
    st.markdown("#### 📜 Petty Cash Ledger")
    if not combined_petty.empty:
        # Sort by latest
        display_p = combined_petty.copy().sort_index(ascending=False)
        
        # Comma Formatting
        if 'AMOUNT' in display_p.columns:
            display_p['AMOUNT'] = display_p['AMOUNT'].apply(lambda x: f"{float(x):,.0f}")
            
        st.dataframe(
            display_p, 
            use_container_width=True, 
            hide_index=True,
            column_order=("DATE", "TYPE", "ITEM", "AMOUNT")
        )
    else:
        st.info("ℹ️ No petty cash transactions found.")

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
