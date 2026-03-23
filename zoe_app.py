import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import gspread
import json
import io
import os
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

# --- 5. DATA ENGINE (Google Sheets - High Performance Version) ---
@st.cache_data(ttl=60) # Changed from 600 to 60 (Checks Google every minute)
def load_full_database():
    try:
        # 1. Setup Dict and Clean Newlines
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        # 2. Direct Authorization
        client = gspread.service_account_from_dict(creds_dict)
        
        # 🎯 USE THE UNIQUE ID (This ensures it ALWAYS finds the right file)
        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
        database = client.open_by_key(sheet_id)

        def fetch_worksheet(name):
            try:
                sheet = database.worksheet(name)
                data = sheet.get_all_records()
                # If sheet is empty, return a DataFrame with your specific headers
                if not data:
                    return pd.DataFrame()
                return pd.DataFrame(data)
            except:
                return pd.DataFrame()

        # 3. Pull all tabs
        df = fetch_worksheet("Clients")
        pay_df = fetch_worksheet("Repayments")
        collat_df = fetch_worksheet("Collateral")
        exp_df = fetch_worksheet("Expenses")
        petty_df = fetch_worksheet("PettyCash")
        payroll_df = fetch_worksheet("Payroll")

        return df, pay_df, collat_df, exp_df, petty_df, payroll_df, client
    except Exception as e:
        st.error(f"FATAL CONNECTION ERROR: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

# ACTIVATE THE SYSTEM
df, pay_df, collateral_df, expense_df, petty_df, payroll_df, g_client = load_full_database()
# --- 6. NAVIGATION (Sidebar) ---
with st.sidebar:
    # 1. DYNAMIC LOGO LOADER
    if 'custom_logo' in st.session_state:
        # Show the logo the user just uploaded from their PC
        st.image(st.session_state.custom_logo, use_container_width=True)
    elif os.path.exists("logo.png"):
        # Fallback to GitHub file if it exists
        st.image("logo.png", use_container_width=True)
    else:
        # Fallback to text if everything else fails
        st.markdown(f"<h2 style='text-align: center; color: #1e3a8a;'>{st.session_state.get('biz_name', 'ZOE ADMIN')}</h2>", unsafe_allow_html=True)
    
    st.markdown("---")
    # ... rest of your option_menu code ...


    # 4. STATUS LIGHT
    if not df.empty:
        st.markdown("<p style='text-align: center; color: #16a34a; font-size: 11px;'>🟢 Cloud Database Connected</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align: center; color: #dc2626; font-size: 11px;'>🔴 Database Offline</p>", unsafe_allow_html=True)
    # 2. THE NAVIGATION MENU (Keeping your original setup)
    page = option_menu(
        menu_title=None,
        options=["Overview", "Borrowers", "Collateral", "Calendar", "Ledger", "Overdue Tracker", "Expenses", "PettyCash", "Payroll", "Add Payment", "Settings"],
        # Note: Added 'box-arrow-right' for Logout or others if you want to expand icons later
        icons=["grid-1x2", "people", "shield-lock", "calendar3", "file-earmark-medical", "alarm", "wallet2", "cash-register", "person-check", "cash-stack", "gear"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "nav-link": {"font-size": "13px", "text-align": "left", "margin":"0px", "--hover-color": "#eff6ff"},
            "nav-link-selected": {"background-color": "#1e3a8a"},
        }
    )
    
    st.markdown("---")

    # 3. CLOUD SYNC & LOGOUT (The "Engine Room")
    c1, c2 = st.columns(2)
    
    # Manual Sync Button
    if c1.button("🔄 Sync", use_container_width=True, help="Force pull latest data from Google Sheets"):
        st.cache_data.clear()
        st.rerun()

    # Logout Button
    # Added key="sidebar_exit_btn" to make it unique
if c2.button("🚪 Exit", use_container_width=True, key="sidebar_exit_btn"):
    st.session_state.clear()
    st.rerun()
    # 4. CONNECTION STATUS INDICATOR
    if not df.empty:
        st.markdown("<p style='color: #16a34a; font-size: 10px; text-align: center;'>● System Online (Cloud Synced)</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='color: #dc2626; font-size: 10px; text-align: center;'>○ System Offline (Check Connection)</p>", unsafe_allow_html=True)

# --- 7. PAGE MODULES ---

# PAGE: OVERVIEW
# Place this at the start of your Overview or Ledger page
t1, t2 = st.columns([1, 5])
with t1:
    # Updated Line 205 Logic
    if 'custom_logo' in st.session_state:
    # Use the logo you browsed from your PC
        st.image(st.session_state.custom_logo, width=80)
    elif os.path.exists("logo.png"):
    # Use the GitHub file ONLY if it exists
        st.image("logo.png", width=80)
    else:
    # Show a nice icon if no logo is found at all
        st.markdown("🏛️", help="Logo not found. Upload one in Settings.")
        with t2:
            st.markdown("# ZOE CONSULTS SMC LTD")
            st.caption("Professional Credit & Financial Management")
if page == "Overview":
    st.markdown('<div class="main-title">🏛️ Executive Overview</div>', unsafe_allow_html=True)
    
    # 1. MERGE ALL DATA (Cloud + Local)
    # Borrowers
    local_b = pd.DataFrame(st.session_state.get('local_registry', []))
    all_b = pd.concat([df, local_b], ignore_index=True)
    
    # Repayments (Revenue)
    local_r = pd.DataFrame(st.session_state.get('local_repayments', []))
    all_r = pd.concat([pay_df, local_r], ignore_index=True)
    
    # Expenses
    local_e = pd.DataFrame(st.session_state.get('local_expenses', []))
    all_e = pd.concat([expense_df, local_e], ignore_index=True)

    # 2. CALCULATE MASTER METRICS
    if not all_b.empty:
        # Convert to numbers safely
        cap_out = pd.to_numeric(all_b['LOAN_AMOUNT'], errors='coerce').sum()
        # Revenue is the sum of all payments collected
        collected = pd.to_numeric(all_r['AMOUNT_PAID'], errors='coerce').sum() if not all_r.empty else 0
        # Risk is Capital Out minus what has been paid back
        at_risk = cap_out - collected
    else:
        cap_out, collected, at_risk = 0, 0, 0

    # 3. CALCULATE NET REVENUE (Collected - Bills)
    t_ops = pd.to_numeric(all_e['AMOUNT'], errors='coerce').sum() if not all_e.empty else 0
    # Petty Cash Spends
    local_p = pd.DataFrame(st.session_state.get('local_petty', []))
    all_p = pd.concat([petty_df, local_p], ignore_index=True)
    t_petty = all_p[all_p['TYPE'] == 'Spend']['AMOUNT'].sum() if not all_p.empty else 0
    # Payroll
    local_pay = pd.DataFrame(st.session_state.get('local_payroll', []))
    all_pay = pd.concat([payroll_df, local_pay], ignore_index=True)
    t_payroll = all_pay['NET_PAY'].sum() if not all_pay.empty else 0
    
    net_rev = collected - (t_ops + t_petty + t_payroll)
    
    # 4. DISPLAY TOP METRICS
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Capital Out", f"UGX {cap_out:,.0f}")
    k2.metric("📈 Collected", f"UGX {collected:,.0f}")
    k3.metric("💎 Net Revenue", f"UGX {net_rev:,.0f}", delta="After Bills")
    k4.metric("🚨 At Risk", f"UGX {at_risk:,.0f}", delta_color="inverse")

    st.write("---")
    
    # 5. CHARTS (Live Update)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Collection Ratio")
        if cap_out > 0:
            fig = px.pie(
                values=[collected, at_risk if at_risk > 0 else 0], 
                names=['Paid', 'Outstanding'], 
                hole=.5, 
                color_discrete_sequence=['#1e3a8a', '#3b82f6']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ℹ️ Add a borrower to see the ratio.")
            
    with c2:
        st.markdown("#### Monthly Expense Breakdown")
        if not all_e.empty:
            exp_chart_data = all_e.groupby('CATEGORY')['AMOUNT'].sum()
            st.bar_chart(exp_chart_data)
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
    
    # 1. Initialize Local Memory
    if 'local_collateral' not in st.session_state:
        st.session_state.local_collateral = []

    # 2. LOG NEW COLLATERAL FORM
    with st.expander("📝 Log New Collateral (Secure Asset)", expanded=True):
        with st.form("collateral_form", clear_on_submit=True):
            # Smart Borrower Picker
            local_names = [b.get('CUSTOMER_NAME') or b.get('BORROWER') for b in st.session_state.get('local_registry', [])]
            cloud_names = df['CUSTOMER_NAME'].tolist() if 'CUSTOMER_NAME' in df.columns else []
            all_borrowers = sorted(list(set([str(n) for n in cloud_names + local_names if n])))
            
            c1, c2 = st.columns(2)
            with c1:
                b_name = st.selectbox("Select Borrower", options=all_borrowers if all_borrowers else ["No Borrowers Found"])
                asset_type = st.text_input("Asset Type", placeholder="e.g. Car Logbook")
                detailed_desc = st.text_area("Detailed Description", placeholder="Plate No, Color, Condition...")
            
            with c2:
                item_val = st.number_input("Estimated Value (UGX)", min_value=0, step=50000)
                st.caption(f"💰 Value Preview: **UGX {item_val:,.0f}**")
                status = st.selectbox("Initial Status", ["Held", "Released", "Disposed"])
                date_added = st.date_input("Date Added", value=datetime.now())

            submit_btn = st.form_submit_button("🔒 Secure Item", use_container_width=True)
            
            if submit_btn:
                if b_name != "No Borrowers Found" and asset_type:
                    new_asset = {
                        "BORROWER": b_name,
                        "ASSET_TYPE": asset_type,
                        "DESCRIPTION": detailed_desc,
                        "ESTIMATED_VALUE": item_val,
                        "STORAGE_REF": str(date_added),
                        "STATUS": status,
                        "DATE_ADDED": str(date_added)
                    }
                    
                    # Save Locally
                    st.session_state.local_collateral.append(new_asset)
                    
                    try:
                        # Fresh Cloud Handshake
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("Collateral")
                        
                        ws.append_row(list(new_asset.values()), value_input_option='USER_ENTERED')
                        
                        st.balloons()
                        st.success(f"✅ {asset_type} secured for {b_name}!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.warning(f"⚠️ Saved locally, Cloud sync pending: {e}")
                else:
                    st.warning("Please select a borrower and enter an Asset Type.")

    st.write("---")

    # 3. THE INVENTORY TABLE
    st.markdown("#### 📦 Current Inventory List")
    
    # 1. Standard Global Headers
    b_col = 'BORROWER' if 'BORROWER' in collateral_df.columns else 'BORROWER_NAME'
    i_col = 'ASSET_TYPE' if 'ASSET_TYPE' in collateral_df.columns else 'ITEM_NAME'
    v_col = 'ESTIMATED_VALUE' if 'ESTIMATED_VALUE' in collateral_df.columns else 'VALUE'
    s_col = 'STATUS' if 'STATUS' in collateral_df.columns else 'STATUS'
    d_col = 'DESCRIPTION' if 'DESCRIPTION' in collateral_df.columns else 'ITEM_NAME'
    dt_col = 'DATE_ADDED' if 'DATE_ADDED' in collateral_df.columns else 'STORAGE_REF'

    local_collat_df = pd.DataFrame(st.session_state.get('local_collateral', []))
    combined_collat = pd.concat([collateral_df, local_collat_df], ignore_index=True)
    
    if not combined_collat.empty:
        # --- THE FIX: LOGICAL FILTERING ---
        
        # A. Clean up Status text (Make it all UPPERCASE so 'deleted' vs 'DELETED' doesn't matter)
        combined_collat[s_col] = combined_collat[s_col].astype(str).str.upper().str.strip()
        
        # B. DEDUPLICATE FIRST: Keep the LATEST entry for every Borrower + Asset Type
        # This ensures the 'DELETED' row (added last) replaces the 'HELD' row
        combined_collat = combined_collat.drop_duplicates(subset=[b_col, i_col], keep='last')
        
        # C. FILTER OUT DELETED: Now that the latest status is confirmed, hide them
        # This removes the item entirely from the view
        combined_collat = combined_collat[~combined_collat[s_col].isin(["DELETED", "REMOVED", "NAN", "NONE"])]
        
        # D. Sort to show the newest active items at the top
        combined_collat = combined_collat.sort_index(ascending=False)

        # 2. SEARCH & DISPLAY
        search = st.text_input("🔍 Filter Inventory", placeholder="Search name or item...", key="collat_search_main")
        display_df = combined_collat.copy()
        
        if search:
            display_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        # 3. TABLE FORMATTING
        table_show = display_df.copy()
        if v_col in table_show.columns:
            table_show[v_col] = pd.to_numeric(table_show[v_col], errors='coerce').fillna(0)
            table_show[v_col] = table_show[v_col].apply(lambda x: f"{float(x):,.0f}")
            
        st.dataframe(table_show, use_container_width=True, hide_index=True)
        
        st.caption(f"Showing {len(display_df)} active collateral items.")
    else:
        st.info("ℹ️ Your Collateral Inventory is currently empty.")

        # --- 4. MANAGE SELECTED ASSET ---
        st.write("---")
        st.markdown("#### 🛠️ Manage Selected Asset")
        
        # Build Options List safely
        dropdown_options = []
        for _, row in display_df.iterrows():
            name = str(row.get(b_col, "N/A"))
            item = str(row.get(i_col, "Item"))
            val = str(row.get(v_col, "0"))
            dropdown_options.append(f"{name} | {item} (UGX {val})")

        selected_asset_str = st.selectbox("Select item to Update/Delete", options=dropdown_options)

        if selected_asset_str:
            # We find the row by index in display_df to be 100% accurate
            idx = dropdown_options.index(selected_asset_str)
            asset_row = display_df.iloc[idx]
            
            st.info(f"📍 Managing: **{asset_row.get(i_col)}** for **{asset_row.get(b_col)}**")
            
            col_a, col_b = st.columns(2)
            
            with col_a.expander("📝 Edit Asset"):
                with st.form("edit_asset_final_v4"):
                    new_desc = st.text_input("Description", value=str(asset_row.get(d_col, "")))
                    
                    # Clean the value
                    clean_v = str(asset_row.get(v_col, "0")).replace(",", "").strip()
                    try: curr_v = int(float(clean_v))
                    except: curr_v = 0
                    
                    new_val = st.number_input("Value (UGX)", value=curr_v, step=50000)
                    new_status = st.selectbox("Status", ["Held", "Released", "Disposed"])
                    
                    if st.form_submit_button("💾 Save Changes"):
                        try:
                            creds_dict = dict(st.secrets["gcp_service_account"])
                            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                            fresh_client = gspread.service_account_from_dict(creds_dict)
                            ws = fresh_client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Collateral")
                            ws.append_row([asset_row[b_col], asset_row[i_col], new_desc, new_val, asset_row.get(dt_col, ""), new_status, str(datetime.now().date())])
                            st.success("✅ Saved!")
                            st.cache_data.clear(); st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            with col_b.expander("🗑️ Delete"):
                if st.button("🔥 Confirm Deletion", key="del_final_v5"):
                    try:
                        # 1. Fresh Handshake
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        ws = fresh_client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Collateral")
                        
                        # 2. THE FIX: Match your 7 columns EXACTLY as shown in your screenshot
                        # Columns: [BORROWER, ASSET_TYPE, DESCRIPTION, ESTIMATED_VALUE, STORAGE_REF, STATUS, DATE_ADDED]
                        delete_row = [
                            str(asset_row.get(b_col, "")),      # 1. BORROWER
                            str(asset_row.get(i_col, "")),      # 2. ASSET_TYPE
                            "DELETED RECORD",                   # 3. DESCRIPTION
                            0,                                  # 4. ESTIMATED_VALUE
                            str(asset_row.get(dt_col, "")),     # 5. STORAGE_REF
                            "DELETED",                          # 6. STATUS
                            str(datetime.now().date())          # 7. DATE_ADDED
                        ]
                        
                        ws.append_row(delete_row)
                        
                        st.success("✅ Success! Item removed from active inventory.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        # This will tell us the exact technical reason if it fails
                        st.error(f"Sync error: {str(e)}")
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

    # 2. CALCULATE LIVE BALANCE (Cloud + Local)
    local_p_df = pd.DataFrame(st.session_state.local_petty)
    combined_petty = pd.concat([petty_df, local_p_df], ignore_index=True)
    
    if not combined_petty.empty:
        # Ensure numbers are valid for math
        combined_petty['AMOUNT'] = pd.to_numeric(combined_petty['AMOUNT'], errors='coerce').fillna(0)
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
                    
                    # Save locally for instant view
                    st.session_state.local_petty.append(new_p)
                    
                    try:
                        # Fresh handshake for Google
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("PettyCash")
                        ws.append_row(list(new_p.values()), value_input_option='USER_ENTERED')
                        
                        st.success(f"✅ {p_type} recorded!")
                        st.cache_data.clear()
                        st.rerun() # <--- This makes the table show up immediately!
                    except Exception as e:
                        if "200" in str(e):
                            st.success("✅ Recorded!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.warning(f"⚠️ Saved locally, Cloud Sync pending.")
                else:
                    st.warning("Please enter an amount and reason.")

    st.write("---")

    # 4. THE TRANSACTION TABLE (The Ledger)
    st.markdown("#### 📜 Petty Cash Ledger")
    
    if not combined_petty.empty:
        # Sort so the newest transaction is at the top
        display_p = combined_petty.copy().sort_index(ascending=False)
        
        # Comma Formatting for the 'AMOUNT' column
        if 'AMOUNT' in display_p.columns:
            display_p['AMOUNT'] = display_p['AMOUNT'].apply(lambda x: f"{float(x):,.0f}")
            
        st.dataframe(
            display_p, 
            use_container_width=True, 
            hide_index=True,
            column_order=("DATE", "TYPE", "ITEM", "AMOUNT")
        )
    else:
        st.info("ℹ️ No petty cash transactions found. Top up your float to get started!")

# PAGE: PAYROLL (Salaries & Digital Pay Slips)
elif page == "Payroll":
    st.markdown('<div class="main-title">👔 Team Payroll Management</div>', unsafe_allow_html=True)
    
    # 1. Initialize Local Memory
    if 'local_payroll' not in st.session_state:
        st.session_state.local_payroll = []

    # 2. SYNC DATA (Cloud + Local)
    local_pay_df = pd.DataFrame(st.session_state.local_payroll)
    combined_payroll = pd.concat([payroll_df, local_pay_df], ignore_index=True)
    
    # 3. PAYROLL SUMMARY
    if not combined_payroll.empty:
        total_monthly_pay = pd.to_numeric(combined_payroll['NET_PAY'], errors='coerce').sum()
        st.metric("Total Monthly Payroll", f"UGX {total_monthly_pay:,.0f}", delta="Staff Costs")

    # 4. RECORD SALARY PAYMENT
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
                if p_staff and net_pay > 0:
                    new_payroll = {
                        "STAFF_NAME": p_staff,
                        "BASIC_SALARY": p_basic,
                        "BONUS": p_bonus,
                        "DEDUCTIONS": p_deduct,
                        "NET_PAY": net_pay,
                        "DATE": str(p_date)
                    }
                    st.session_state.local_payroll.append(new_payroll)
                    
                    try:
                        # Fresh handshake to avoid AttributeError
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("Payroll")
                        ws.append_row(list(new_payroll.values()), value_input_option='USER_ENTERED')
                        
                        st.success(f"✅ Salary processed for {p_staff}!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.warning(f"⚠️ Saved locally, Cloud sync pending: {e}")
                else:
                    st.warning("Please fill in Staff Name and Amount.")

    # 5. GENERATE INDIVIDUAL PAY SLIP (Restored Logic)
    st.write("---")
    st.markdown("#### 🎫 Generate Individual Pay Slip")
    
    if not combined_payroll.empty:
        staff_list = combined_payroll['STAFF_NAME'].unique()
        selected_staff = st.selectbox("Select Employee", options=staff_list)
        
        # Get the latest payment for this staff member
        staff_data = combined_payroll[combined_payroll['STAFF_NAME'] == selected_staff].iloc[-1]

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
                pdf.cell(60, 10, f"{float(basic):,.0f}", 1, 1, 'R')
                pdf.cell(130, 10, "Performance Bonus / Commission", 1)
                pdf.cell(60, 10, f"{float(bonus):,.0f}", 1, 1, 'R')
                pdf.set_text_color(153, 27, 27) # Red for deductions
                pdf.cell(130, 10, "Deductions / Salary Advance", 1)
                pdf.cell(60, 10, f"- {float(deduct):,.0f}", 1, 1, 'R')

                # Net Total
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 12)
                pdf.set_fill_color(239, 246, 255) # Baby Blue
                pdf.set_text_color(30, 58, 138)
                pdf.cell(130, 12, " NET DISBURSEMENT", 1, 0, 'L', True)
                pdf.cell(60, 12, f"UGX {float(net):,.0f}", 1, 1, 'R', True)

                # Signatures
                pdf.ln(20)
                pdf.set_font("Arial", 'I', 9)
                pdf.set_text_color(100, 116, 139)
                pdf.cell(100, 10, "__________________________", ln=0)
                pdf.cell(90, 10, "__________________________", ln=1, align='R')
                pdf.cell(100, 5, "Authorized Signatory", ln=0)
                pdf.cell(90, 5, "Employee Signature", ln=1, align='R')
                
                return pdf.output(dest='S').encode('latin-1')

            # PDF Generation & Download
            slip_bytes = generate_payslip_pdf(
                staff_data['STAFF_NAME'], staff_data['BASIC_SALARY'], 
                staff_data['BONUS'], staff_data['DEDUCTIONS'], 
                staff_data['NET_PAY'], staff_data['DATE'], "ZOE CONSULTS SMC LTD"
            )
            b64_slip = base64.b64encode(slip_bytes).decode()
            href_slip = f'<a href="data:application/octet-stream;base64,{b64_slip}" download="PaySlip_{selected_staff}.pdf" style="text-decoration:none;">' \
                        f'<div style="background-color:#3b82f6; color:white; padding:15px; border-radius:10px; text-align:center; font-weight:bold;">' \
                        f'📥 DOWNLOAD PAY SLIP FOR {selected_staff}</div></a>'
            st.markdown(href_slip, unsafe_allow_html=True)
            
        # 6. DISBURSEMENT HISTORY TABLE
        st.write("---")
        st.markdown("#### 📜 Disbursement History")
        display_pay = combined_payroll.copy().sort_values(by='DATE', ascending=False)
        for col in ['BASIC_SALARY', 'BONUS', 'DEDUCTIONS', 'NET_PAY']:
            if col in display_pay.columns:
                display_pay[col] = display_pay[col].apply(lambda x: f"{float(x):,.0f}")
        st.dataframe(display_pay, use_container_width=True, hide_index=True)
    else:
        st.info("Record a staff salary first to generate a pay slip.")
# PAGE: ADD PAYMENT (Loan Collections)
elif page == "Add Payment":
    st.markdown('<div class="main-title">📥 Post Loan Repayment</div>', unsafe_allow_html=True)
    
    # 1. Initialize Local Payment Memory
    if 'local_repayments' not in st.session_state:
        st.session_state.local_repayments = []

    # 2. SYNC DATA (Combine Cloud + Local Borrowers for the dropdown)
    local_borrowers = pd.DataFrame(st.session_state.get('local_registry', []))
    combined_borrowers = pd.concat([df, local_borrowers], ignore_index=True)
    
    if not combined_borrowers.empty:
        # --- REPAYMENT FORM ---
        with st.form("add_p", clear_on_submit=True):
            borrower_list = combined_borrowers['CUSTOMER_NAME'].unique().tolist()
            cn = st.selectbox("Select Client", options=borrower_list)
            
            c1, c2 = st.columns(2)
            ap = c1.number_input("Amount Paid (UGX)", min_value=0, step=10000)
            p_mode = c2.selectbox("Payment Mode", ["Mobile Money", "Cash", "Bank Deposit"])
            p_note = st.text_input("Note (Optional)")
            
            if st.form_submit_button("🚀 Post Repayment & Update Ledger", use_container_width=True):
                if ap > 0:
                    today = str(datetime.now().date())
                    # Dictionary for local memory
                    new_pay_dict = {
                        "CUSTOMER_NAME": cn,
                        "AMOUNT_PAID": ap,
                        "DATE": today,
                        "PAYMENT_MODE": p_mode,
                        "NOTES": p_note
                    }
                    
                    # STEP A: Save locally for the table below
                    st.session_state.local_repayments.append(new_pay_dict)
                    
                    try:
                        # STEP B: Save to Google (Fresh Handshake)
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        fresh_client = gspread.service_account_from_dict(creds_dict)
                        
                        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
                        ws = fresh_client.open_by_key(sheet_id).worksheet("Repayments")
                        ws.append_row(list(new_pay_dict.values()), value_input_option='USER_ENTERED')
                        
                        st.balloons()
                        st.success(f"✅ UGX {ap:,.0f} collected from {cn}!")
                        st.cache_data.clear()
                        # No st.rerun() here so the form stays cleared but the table below updates via session_state
                    except Exception as e:
                        if "200" in str(e):
                            st.balloons(); st.cache_data.clear()
                        else:
                            st.warning(f"⚠️ Saved locally, Cloud Sync pending: {e}")
                else:
                    st.warning("Please enter a valid amount.")

        # 3. THE COLLECTIONS TABLE (Combined Cloud + Local)
        st.write("---")
        st.markdown("#### 🕒 Recent Collections Ledger")
        
        # Merge Cloud payments with your new local payments
        local_pay_df = pd.DataFrame(st.session_state.local_repayments)
        combined_payments = pd.concat([pay_df, local_pay_df], ignore_index=True)

        if not combined_payments.empty:
            # Clean up and sort by date (newest first)
            display_pay = combined_payments.copy().sort_index(ascending=False)
            
            # Format numbers with commas
            if 'AMOUNT_PAID' in display_pay.columns:
                display_pay['AMOUNT_PAID'] = display_pay['AMOUNT_PAID'].apply(lambda x: f"{float(x):,.0f}" if x != "" else "0")
            
            st.dataframe(
                display_pay, 
                use_container_width=True, 
                hide_index=True,
                column_order=("DATE", "CUSTOMER_NAME", "AMOUNT_PAID", "PAYMENT_MODE", "NOTES")
            )
            
            total_rev = pd.to_numeric(combined_payments['AMOUNT_PAID'], errors='coerce').sum()
            st.info(f"📈 Total Revenue Collected: **UGX {total_rev:,.0f}**")
        else:
            st.info("ℹ️ No repayments recorded yet.")
    else:
        st.info("ℹ️ No borrowers found. Register a client first.")


# PAGE: SETTINGS (Backups & Reports & Branding)
elif page == "Settings":
    st.markdown('<div class="main-title">⚙️ Business Configuration</div>', unsafe_allow_html=True)
    
    # 1. BUSINESS PROFILE & LOGO
    st.markdown("<p style='color: #1e3a8a; font-weight: bold;'>🏢 Business Identity & Branding</p>", unsafe_allow_html=True)
    
    # --- LOGO UPLOADER SECTION ---
    with st.expander("🎨 Logo & Visual Branding", expanded=True):
        uploaded_logo = st.file_uploader("Upload Company Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if uploaded_logo:
            st.session_state.custom_logo = uploaded_logo.read()
            st.image(st.session_state.custom_logo, width=150, caption="Logo Preview")
            st.success("✅ Logo uploaded! It will now appear in the sidebar.")

    col1, col2 = st.columns(2)
    biz_name = col1.text_input("Company Name", value=st.session_state.get('biz_name', "ZOE CONSULTS SMC LTD"))
    biz_tagline = col2.text_input("Tagline", value=st.session_state.get('biz_tagline', "Official Loan Statement & Repayment Ledger"))
    
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
        # Store for PDF logic
        st.session_state.signature = uploaded_sig.read()

    # 4. SAVE BUTTON
    if st.button("💾 Save System Settings", use_container_width=True):
        # Commit choices to session state
        st.session_state.biz_name = biz_name
        st.session_state.biz_tagline = biz_tagline
        st.session_state.default_rate = default_rate
        st.session_state.late_penalty = late_penalty
        
        st.balloons()
        st.success("Settings updated successfully! Changes are active for this session.")
