import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta
import os
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
from st_aggrid import AgGrid
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from streamlit_option_menu import option_menu

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import pandas as pd
from datetime import datetime, timedelta

# ... (rest of your sidebar/navigation code)

# --- ADD THIS TO THE TOP OF YOUR FILE (AFTER IMPORTS) ---
@st.cache_data(ttl=300) # This refreshes data from Google Sheets every 5 mins
def get_data():
    try:
        # ... your existing connection code ...
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        # DEBUG: This will show in your terminal/logs
        print(f"Fetched {len(df)} rows from Google Sheets") 
        
        return df
    except Exception as e:
        st.error(f"Failed to fetch cloud data: {e}")
        return pd.DataFrame()

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Zoe Consults Admin",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main-title { font-size: 32px; font-weight: 700; color: #1e3a8a; margin-bottom: 20px; }
    .stMetric {
        background-color: #f0f9ff;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid #1e3a8a;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div.stButton > button:first-child {
        background-color: #1e3a8a;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #3b82f6;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE INITIALIZATION ---
for key in ["authenticated", "ready", "b64_str", "last_client"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "authenticated" else ""

# --- 4. LOGIN ---
if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>🏛️ Admin Portal</h2>", unsafe_allow_html=True)
        user = st.text_input("Username")
        pw = st.text_input("Access Key", type="password")
        if st.button("Login to Zoe Consults", use_container_width=True):
            if user == st.secrets["admin_user"] and pw == st.secrets["admin_pass"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid Credentials")
    st.stop()

# --- 5. DATA ENGINE (Google Sheets) ---
@st.cache_data(ttl=120, show_spinner="Syncing cloud data...")
def load_full_database():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        client = gspread.service_account_from_dict(creds_dict)
        sheet_id = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
        database = client.open_by_key(sheet_id)

        def fetch_ws(name):
            try:
                sheet = database.worksheet(name)
                data = sheet.get_all_records()
                return pd.DataFrame(data) if data else pd.DataFrame()
            except:
                return pd.DataFrame()

        df = fetch_ws("Clients")
        pay_df = fetch_ws("Repayments")
        collat_df = fetch_ws("Collateral")
        exp_df = fetch_ws("Expenses")
        petty_df = fetch_ws("PettyCash")
        payroll_df = fetch_ws("Payroll")
        return df, pay_df, collat_df, exp_df, petty_df, payroll_df, client
    except Exception as e:
        st.error(f"FATAL CONNECTION ERROR: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

df, pay_df, collateral_df, expense_df, petty_df, payroll_df, g_client = load_full_database()

# --- 6. SIDEBAR NAVIGATION ---
with st.sidebar:
    # Logo
    if 'custom_logo' in st.session_state:
        st.image(st.session_state.custom_logo, use_container_width=10)
    elif os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=10)
    else:
        st.markdown(f"<h2 style='text-align: center; color: #1e3a8a;'>{st.session_state.get('biz_name', 'ZOE ADMIN')}</h2>", unsafe_allow_html=True)

    st.markdown("---")

    page = option_menu(
        menu_title=None,
        options=["Overview", "Borrowers", "Collateral", "Calendar", "Ledger",
                 "Overdue Tracker", "Expenses", "PettyCash", "Payroll", "Add Payment", "Settings"],
        icons=["grid-1x2", "people", "shield-lock", "calendar3", "file-earmark-medical",
               "alarm", "wallet2", "cash-register", "person-check", "cash-stack", "gear"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "nav-link": {"font-size": "13px", "text-align": "left"},
            "nav-link-selected": {"background-color": "#1e3a8a"},
        }
    )

    st.markdown("---")

    c1, c2 = st.columns(2)
    if c1.button("🔄 Sync", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if c2.button("🚪 Exit", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown(
        "<p style='font-size:10px; text-align:center; color:{}'>{}</p>".format(
            "#16a34a" if not df.empty else "#dc2626",
            "● System Online (Cloud Synced)" if not df.empty else "○ System Offline (Check Connection)"
        ),
        unsafe_allow_html=True
    )

# --- 7. MODULE PLACEHOLDER ---
st.markdown(f"<div class='main-title'>🖥️ {page} Module</div>", unsafe_allow_html=True)
st.info("Module content will load here based on your navigation selection.")

if page == "Overview":
    st.markdown('<div class="main-title">🏛️ Executive Overview</div>', unsafe_allow_html=True)

    # --- 1. MERGE ALL DATA (CLOUD + LOCAL) ---
    local_b = pd.DataFrame(st.session_state.get('local_registry', []))
    local_r = pd.DataFrame(st.session_state.get('local_repayments', []))
    local_e = pd.DataFrame(st.session_state.get('local_expenses', []))
    local_p = pd.DataFrame(st.session_state.get('local_petty', []))
    local_pay = pd.DataFrame(st.session_state.get('local_payroll', []))

    all_b = pd.concat([df, local_b], ignore_index=True)
    all_r = pd.concat([pay_df, local_r], ignore_index=True)
    all_e = pd.concat([expense_df, local_e], ignore_index=True)
    all_p = pd.concat([petty_df, local_p], ignore_index=True)
    all_pay = pd.concat([payroll_df, local_pay], ignore_index=True)

    # --- 2. CLEAN DATA (VERY IMPORTANT) ---
    def clean(df, col):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df

    all_b = clean(all_b, 'LOAN_AMOUNT')
    all_b = clean(all_b, 'AMOUNT_PAID')
    all_b = clean(all_b, 'OUTSTANDING_AMOUNT')

    all_r = clean(all_r, 'AMOUNT_PAID')
    all_e = clean(all_e, 'AMOUNT')
    all_p = clean(all_p, 'AMOUNT')
    all_pay = clean(all_pay, 'NET_PAY')

    # --- 3. CORE METRICS ---
    cap_out = all_b['LOAN_AMOUNT'].sum() if not all_b.empty else 0
    collected = all_r['AMOUNT_PAID'].sum() if not all_r.empty else 0
    outstanding = all_b['OUTSTANDING_AMOUNT'].sum() if not all_b.empty else 0

    # EXPENSES BREAKDOWN
    t_ops = all_e['AMOUNT'].sum() if not all_e.empty else 0
    t_petty = all_p[all_p['TYPE'] == 'Spend']['AMOUNT'].sum() if not all_p.empty else 0
    t_payroll = all_pay['NET_PAY'].sum() if not all_pay.empty else 0

    total_expenses = t_ops + t_petty + t_payroll
    net_profit = collected - total_expenses

    # COLLECTION RATE
    collection_rate = (collected / cap_out * 100) if cap_out > 0 else 0

    # --- 4. KPI DISPLAY (KEEP YOUR COLORS) ---
    k1, k2, k3, k4 = st.columns(4)

    k1.metric("💰 Capital Out", f"UGX {cap_out:,.0f}")
    k2.metric("📈 Collected", f"UGX {collected:,.0f}")
    k3.metric("💎 Net Profit", f"UGX {net_profit:,.0f}", delta="After Expenses")
    k4.metric("🚨 Outstanding", f"UGX {outstanding:,.0f}", delta_color="inverse")

    st.write("---")

    # --- 5. SECONDARY METRICS ---
    s1, s2, s3 = st.columns(3)
    s1.metric("📊 Collection Rate", f"{collection_rate:.1f}%")
    s2.metric("💸 Total Expenses", f"UGX {total_expenses:,.0f}")
    s3.metric("👥 Total Clients", f"{len(all_b)}")

    st.write("---")

    # --- 6. VISUALS ---
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 💰 Portfolio Distribution")

        if cap_out > 0:
            fig = px.pie(
                values=[collected, outstanding],
                names=['Collected', 'Outstanding'],
                hole=0.5,
                color_discrete_sequence=['#1e3a8a', '#3b82f6']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No loan data available yet.")

    with c2:
        st.markdown("#### 📉 Expense Breakdown")

        if not all_e.empty:
            exp_chart = all_e.groupby('CATEGORY')['AMOUNT'].sum().sort_values(ascending=False)

            fig2 = px.bar(
                exp_chart,
                x=exp_chart.index,
                y=exp_chart.values,
                color_discrete_sequence=['#3b82f6']
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No expenses recorded yet.")

    st.write("---")

    # --- 7. MONTHLY PERFORMANCE (🔥 UPGRADE) ---
    st.markdown("#### 📆 Monthly Performance")

    if not all_r.empty:
        all_r['DATE'] = pd.to_datetime(all_r['DATE'], errors='coerce')
        monthly_rev = all_r.groupby(all_r['DATE'].dt.to_period("M"))['AMOUNT_PAID'].sum()

        monthly_rev.index = monthly_rev.index.astype(str)

        fig3 = px.line(
            monthly_rev,
            x=monthly_rev.index,
            y=monthly_rev.values,
            markers=True
        )
        fig3.update_traces(line_color='#1e3a8a')

        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No revenue data yet.")

    st.write("---")

    # --- 8. TOP BORROWERS (SMART INSIGHT) ---
    st.markdown("#### 🏆 Top Borrowers (Highest Loans)")

    if not all_b.empty:
        top_clients = all_b.sort_values(by='LOAN_AMOUNT', ascending=False).head(5)

        st.dataframe(
            top_clients[['CUSTOMER_NAME', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No borrower data available.")
    

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# --- 1. Page Title ---
st.markdown('<div class="main-title">👥 Borrower Management Hub</div>', unsafe_allow_html=True)

# --- 2. Initialize Local Storage ---
if 'local_registry' not in st.session_state:
    st.session_state.local_registry = []

# --- 3. Fetch Cloud Data ---
def get_cloud_data():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        client = gspread.service_account_from_dict(creds_dict)
        ws = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Clients")
        data = ws.get_all_records()
        return pd.DataFrame(data), ws
    except Exception as e:
        st.warning(f"Cloud connection failed: {e}")
        return pd.DataFrame(), None

df_cloud, ws_clients = get_cloud_data()
local_df = pd.DataFrame(st.session_state.local_registry)
combined = pd.concat([df_cloud, local_df], ignore_index=True) if not df_cloud.empty else local_df

# --- 4. Register New Client ---
with st.expander("➕ Register New Client (KYC Enrollment)", expanded=False):
    with st.form("kyc_registration_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            f_name = st.text_input("First Name")
            l_name = st.text_input("Last Name")
            phone = st.text_input("Contact (256...)")
            gender = st.selectbox("Gender", ["Male", "Female"])
            nin = st.text_input("NIN")
            issue_date = st.date_input("Loan Issue Date", value=datetime.now())

        with c2:
            loan_amt = st.number_input("Loan Amount (UGX)", min_value=0, step=50000)
            interest = st.number_input("Interest Rate (%)", min_value=0.0)
            loan_type = st.selectbox("Loan Type", ["Personal", "Business", "Emergency"])
            address = st.text_area("Address")
            due_date = st.date_input("Due Date", value=datetime.now() + timedelta(days=30))

        total_due = loan_amt + (loan_amt * interest / 100)
        st.info(f"💰 Total Payable: UGX {total_due:,.0f}")

        if st.form_submit_button("🚀 Register & Disburse"):
            if f_name and l_name and nin:
                full_name = f"{f_name} {l_name}".upper()
                new_entry = {
                    "CUSTOMER_NAME": full_name,
                    "CONTACT": phone,
                    "NIN": nin,
                    "GENDER": gender,
                    "ADDRESS": address,
                    "LOAN_TYPE": loan_type,
                    "LOAN_AMOUNT": loan_amt,
                    "INTEREST_RATE": interest,
                    "TOTAL_DUE": total_due,
                    "AMOUNT_PAID": 0,
                    "OUTSTANDING_AMOUNT": total_due,
                    "ISSUE_DATE": str(issue_date),
                    "DUE_DATE": str(due_date)
                }
                st.session_state.local_registry.append(new_entry)

                # Try to save to Google Sheets
                try:
                    if ws_clients:
                        ws_clients.append_row(list(new_entry.values()), value_input_option='USER_ENTERED')
                        st.success(f"✅ {full_name} registered successfully!")
                        st.balloons()
                except:
                    st.warning("Saved locally. Cloud sync pending.")

            else:
                st.warning("Please fill all required fields.")

st.markdown("---")

# --- 5. Borrower Directory Table ---
st.markdown("#### 🔍 Borrower Directory")

if not combined.empty:
    # Format money
    for col in ['LOAN_AMOUNT','TOTAL_DUE','AMOUNT_PAID','OUTSTANDING_AMOUNT']:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors='coerce').fillna(0)
            combined[col] = combined[col].apply(lambda x: f"{x:,.0f}")

    # Add actions column placeholder
    combined["ACTIONS"] = "👁️ ✏️ 🗑️"

    # Build AgGrid table
    gb = GridOptionsBuilder.from_dataframe(combined)
    gb.configure_selection('single', use_checkbox=True)
    gb.configure_column("ACTIONS", editable=False)
    grid_options = gb.build()

    grid_response = AgGrid(
        combined,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme='streamlit',
        height=400,
        enable_enterprise_modules=False
    )

    # Handle selected row actions
    selected_rows = grid_response.get('selected_rows')
    if selected_rows:
        row = selected_rows[0]
        st.markdown(f"### Actions for {row['CUSTOMER_NAME']}")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("👁️ View Details"):
                st.info(f"""
                **Name:** {row['CUSTOMER_NAME']}
                **NIN:** {row['NIN']}
                **Contact:** {row['CONTACT']}
                **Address:** {row['ADDRESS']}
                **Gender:** {row['GENDER']}
                **Loan Type:** {row['LOAN_TYPE']}
                **Loan Amount:** UGX {row['LOAN_AMOUNT']}
                **Total Due:** UGX {row['TOTAL_DUE']}
                **Outstanding:** UGX {row['OUTSTANDING_AMOUNT']}
                **Issue Date:** {row['ISSUE_DATE']}
                **Due Date:** {row['DUE_DATE']}
                """)

        with col2:
            if st.button("✏️ Edit KYC"):
                with st.form("edit_form", clear_on_submit=False):
                    new_name = st.text_input("Full Name", value=row["CUSTOMER_NAME"])
                    new_nin = st.text_input("NIN", value=row["NIN"])
                    new_phone = st.text_input("Contact", value=row["CONTACT"])
                    new_gender = st.selectbox("Gender", ["Male","Female"], index=0 if row["GENDER"]=="Male" else 1)
                    new_address = st.text_area("Address", value=row["ADDRESS"])
                    new_loan = st.number_input("Loan Amount (UGX)", value=int(row["LOAN_AMOUNT"].replace(",","")))
                    new_out = st.number_input("Outstanding (UGX)", value=int(row["OUTSTANDING_AMOUNT"].replace(",","")))
                    if st.form_submit_button("💾 Save Changes"):
                        # Update local registry
                        for r in st.session_state.local_registry:
                            if r["NIN"] == row["NIN"]:
                                r.update({
                                    "CUSTOMER_NAME": new_name,
                                    "NIN": new_nin,
                                    "CONTACT": new_phone,
                                    "GENDER": new_gender,
                                    "ADDRESS": new_address,
                                    "LOAN_AMOUNT": new_loan,
                                    "OUTSTANDING_AMOUNT": new_out
                                })
                        st.success("✅ Borrower updated locally!")
                        st.experimental_rerun()

        with col3:
            if st.button("🗑️ Delete"):
                st.session_state.local_registry = [r for r in st.session_state.local_registry if r["NIN"] != row["NIN"]]
                st.success("✅ Borrower deleted locally!")
                st.experimental_rerun()
            else:
                st.info("No borrowers found. Register a client above to start.")
    
elif page == "Collateral":
    st.markdown('<div class="main-title">🛡️ Collateral Inventory</div>', unsafe_allow_html=True)
    # --- 1. INIT LOCAL STORAGE ---
    if 'local_collateral' not in st.session_state:
        st.session_state.local_collateral = []

    # --- 2. LOAD BORROWERS ---
    local_b = pd.DataFrame(st.session_state.get('local_registry', []))
    combined_borrowers = pd.concat([df, local_b], ignore_index=True)

    borrower_names = []
    if not combined_borrowers.empty and 'CUSTOMER_NAME' in combined_borrowers.columns:
        borrower_names = combined_borrowers['CUSTOMER_NAME'].dropna().unique().tolist()

    # --- 3. ADD COLLATERAL ---
    with st.expander("📝 Log New Collateral", expanded=True):
        with st.form("collateral_form", clear_on_submit=True):

            c1, c2 = st.columns(2)

            with c1:
                borrower = st.selectbox("Borrower", borrower_names if borrower_names else ["No borrowers found"])
                asset_type = st.text_input("Asset Type (e.g. Car, Land, Phone)")
                description = st.text_area("Description (Plate No, Serial, etc)")

            with c2:
                value = st.number_input("Estimated Value (UGX)", min_value=0, step=50000)
                status = st.selectbox("Status", ["HELD", "RELEASED", "DISPOSED"])
                date_added = st.date_input("Date Added", value=datetime.now())

            if st.form_submit_button("🔒 Save Collateral"):
                if borrower != "No borrowers found" and asset_type:

                    new_asset = {
                        "BORROWER": borrower,
                        "ASSET_TYPE": asset_type,
                        "DESCRIPTION": description,
                        "ESTIMATED_VALUE": value,
                        "STATUS": status,
                        "DATE_ADDED": str(date_added)
                    }

                    # LOCAL SAVE
                    st.session_state.local_collateral.append(new_asset)

                    # CLOUD SAVE
                    try:
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

                        client = gspread.service_account_from_dict(creds_dict)
                        ws = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Collateral")

                        ws.append_row(list(new_asset.values()), value_input_option='USER_ENTERED')

                        st.success("✅ Collateral saved!")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()

                    except:
                        st.warning("Saved locally. Cloud sync pending.")

                else:
                    st.warning("Fill all required fields.")

    st.write("---")

    # --- 4. DISPLAY COLLATERAL ---
    st.markdown("#### 📦 Collateral Inventory")

    local_c = pd.DataFrame(st.session_state.local_collateral)
    combined_c = pd.concat([collateral_df, local_c], ignore_index=True)

    if not combined_c.empty:

        # CLEAN DATA
        combined_c['BORROWER'] = combined_c['BORROWER'].astype(str).str.strip()
        combined_c['ASSET_TYPE'] = combined_c['ASSET_TYPE'].astype(str).str.strip()
        combined_c['STATUS'] = combined_c['STATUS'].astype(str).str.upper().str.strip()

        # REMOVE DUPLICATES (LATEST ENTRY WINS)
        combined_c = combined_c.drop_duplicates(subset=['BORROWER', 'ASSET_TYPE'], keep='last')

        # REMOVE DELETED
        combined_c = combined_c[~combined_c['STATUS'].isin(['DELETED', 'REMOVED'])]

        # SEARCH
        search = st.text_input("🔍 Search collateral...")
        if search:
            combined_c = combined_c[
                combined_c.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            ]

        # FORMAT VALUE
        combined_c['ESTIMATED_VALUE'] = pd.to_numeric(combined_c['ESTIMATED_VALUE'], errors='coerce').fillna(0)
        combined_c['ESTIMATED_VALUE'] = combined_c['ESTIMATED_VALUE'].apply(lambda x: f"{x:,.0f}")

        st.dataframe(
            combined_c,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No collateral recorded.")

    st.write("---")

    # --- 5. MANAGE COLLATERAL ---
    st.markdown("#### 🛠️ Manage Asset")

    if not combined_c.empty:

        options = combined_c.apply(lambda row: f"{row['BORROWER']} | {row['ASSET_TYPE']}", axis=1).tolist()
        selected = st.selectbox("Select Asset", options)

        selected_row = combined_c.iloc[options.index(selected)]

        c1, c2 = st.columns(2)

        # --- EDIT ---
        with c1:
            with st.expander("📝 Edit Asset"):
                with st.form("edit_asset"):

                    new_desc = st.text_input("Description", value=str(selected_row['DESCRIPTION']))
                    new_val = st.number_input("Value", value=int(str(selected_row['ESTIMATED_VALUE']).replace(",", "")))
                    new_status = st.selectbox("Status", ["HELD", "RELEASED", "DISPOSED"])

                    if st.form_submit_button("💾 Save Changes"):

                        try:
                            creds_dict = dict(st.secrets["gcp_service_account"])
                            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

                            client = gspread.service_account_from_dict(creds_dict)
                            ws = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Collateral")

                            ws.append_row([
                                selected_row['BORROWER'],
                                selected_row['ASSET_TYPE'],
                                new_desc,
                                new_val,
                                new_status,
                                str(datetime.now().date())
                            ])

                            st.success("Updated successfully!")
                            st.cache_data.clear()
                            st.rerun()

                        except:
                            st.error("Update failed.")

        # --- DELETE ---
        with c2:
            with st.expander("🗑️ Delete Asset"):
                st.warning("This will hide the asset from the system.")

                if st.button("🔥 Confirm Delete"):

                    try:
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

                        client = gspread.service_account_from_dict(creds_dict)
                        ws = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Collateral")

                        ws.append_row([
                            selected_row['BORROWER'],
                            selected_row['ASSET_TYPE'],
                            "DELETED",
                            0,
                            "DELETED",
                            str(datetime.now().date())
                        ])

                        st.success("Asset removed.")
                        st.cache_data.clear()
                        st.rerun()

                    except:
                        st.error("Delete failed.")
# PAGE: ACTIVITY CALENDAR
elif page == "Calendar":
    st.markdown('<div class="main-title">📅 Zoe Consults Smart Calendar</div>', unsafe_allow_html=True)

    import calendar

    # --- 1. LOAD DATA ---
    local_b = pd.DataFrame(st.session_state.get('local_registry', []))
    combined_borrowers = pd.concat([df, local_b], ignore_index=True)

    local_c = pd.DataFrame(st.session_state.get('local_collateral', []))
    combined_collateral = pd.concat([collateral_df, local_c], ignore_index=True)

    events_list = []

    # --- 2. BUILD EVENTS ---
    if not combined_borrowers.empty:
        for _, row in combined_borrowers.iterrows():
            name = row.get('CUSTOMER_NAME', 'Unknown')

            if row.get('ISSUE_DATE'):
                try:
                    events_list.append({
                        "date": pd.to_datetime(row['ISSUE_DATE']),
                        "event": f"Loan → {name}",
                        "type": "Loan"
                    })
                except:
                    pass

            if row.get('DUE_DATE'):
                try:
                    events_list.append({
                        "date": pd.to_datetime(row['DUE_DATE']),
                        "event": f"Due → {name}",
                        "type": "Due"
                    })
                except:
                    pass

    if not combined_collateral.empty:
        for _, row in combined_collateral.iterrows():
            borrower = row.get('BORROWER', 'Unknown')
            asset = row.get('ASSET_TYPE', 'Asset')

            if row.get('DATE_ADDED'):
                try:
                    events_list.append({
                        "date": pd.to_datetime(row['DATE_ADDED']),
                        "event": f"Asset → {asset} ({borrower})",
                        "type": "Collateral"
                    })
                except:
                    pass

    events = pd.DataFrame(events_list)

    # --- 3. DATE CONTROLS ---
    c1, c2 = st.columns(2)

    current_year = datetime.now().year
    selected_year = c1.selectbox("Year", list(range(current_year - 2, current_year + 3)), index=2)

    month_names = list(calendar.month_name)[1:]
    selected_month_name = c2.selectbox("Month", month_names, index=datetime.now().month - 1)

    selected_month = month_names.index(selected_month_name) + 1

    # --- 4. PREP EVENTS ---
    if not events.empty:
        events['date'] = pd.to_datetime(events['date'], errors='coerce')
        events = events.dropna(subset=['date'])
        events['day'] = events['date'].dt.day

        month_events = events[
            (events['date'].dt.year == selected_year) &
            (events['date'].dt.month == selected_month)
        ]
    else:
        month_events = pd.DataFrame()

    # --- 5. CALENDAR GRID ---
    st.markdown(f"### {selected_month_name} {selected_year}")

    cal = calendar.monthcalendar(selected_year, selected_month)

    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):

            with cols[i]:
                if day == 0:
                    st.write(" ")
                else:
                    day_events = month_events[month_events['day'] == day] if not month_events.empty else pd.DataFrame()

                    # Day box
                    st.markdown(f"**{day}**")

                    if not day_events.empty:
                        for _, ev in day_events.iterrows():

                            if ev['type'] == "Loan":
                                color = "#3b82f6"
                            elif ev['type'] == "Due":
                                color = "#dc2626"
                            else:
                                color = "#16a34a"

                            st.markdown(
                                f"<div style='background:{color}; color:white; padding:4px; margin:2px; border-radius:6px; font-size:11px;'>"
                                f"{ev['event']}</div>",
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown("<span style='color: #94a3b8;'>No events</span>", unsafe_allow_html=True)

    st.write("---")

    # --- 6. CLICK DAY DETAILS ---
    st.markdown("### 🔍 View Day Details")

    selected_day = st.number_input("Select Day", min_value=1, max_value=31, step=1)

    if not month_events.empty:
        selected_events = month_events[month_events['day'] == selected_day]

        if not selected_events.empty:
            for _, ev in selected_events.iterrows():
                st.info(f"{ev['date'].strftime('%d %b')} — {ev['event']}")
        else:
            st.info("No events for this day.")
    else:
        st.info("No data available.")

    st.write("---")

    # --- 7. UPCOMING ALERTS ---
    st.markdown("### ⏳ Upcoming (Next 7 Days)")

    if not events.empty:
        today = datetime.now()
        next_week = today + timedelta(days=7)

        upcoming = events[
            (events['date'] >= today) &
            (events['date'] <= next_week)
        ].sort_values(by='date')

        if not upcoming.empty:
            for _, ev in upcoming.iterrows():
                st.warning(f"⚠️ {ev['date'].strftime('%d %b')} → {ev['event']}")
        else:
            st.success("No upcoming deadlines 🎉")
    else:
        st.info("No upcoming events.")

# PAGE: LEDGER (Individual Client Statements & PDF Export)
elif page == "Ledger":
    st.markdown('<div class="main-title">📑 Client Statement Center</div>', unsafe_allow_html=True)

    # --- 1. COMBINE DATA ---
    local_df = pd.DataFrame(st.session_state.get('local_registry', []))
    combined = pd.concat([df, local_df], ignore_index=True)

    if not combined.empty and 'CUSTOMER_NAME' in combined.columns:

        combined = combined.drop_duplicates(subset=['NIN'], keep='last')

        # --- 2. SEARCH ---
        search = st.text_input("🔍 Search Client")

        filtered = combined[
            combined['CUSTOMER_NAME'].str.contains(search, case=False, na=False)
        ] if search else combined

        selected = st.selectbox("Select Client", filtered['CUSTOMER_NAME'].tolist())

        if selected:

            client = combined[combined['CUSTOMER_NAME'] == selected].iloc[0]

            # --- 3. PAYMENTS ---
            local_pay = pd.DataFrame(st.session_state.get('local_repayments', []))
            all_payments = pd.concat([pay_df, local_pay], ignore_index=True)

            client_pays = all_payments[
                all_payments['CUSTOMER_NAME'] == selected
            ].copy()

            if not client_pays.empty:
                client_pays['DATE'] = pd.to_datetime(client_pays['DATE'], errors='coerce')
                client_pays = client_pays.sort_values(by='DATE')

            # --- 4. METRICS ---
            loan = float(client.get('LOAN_AMOUNT', 0))
            paid = client_pays['AMOUNT_PAID'].sum() if not client_pays.empty else 0
            balance = loan - paid

            today = datetime.now().date()
            due_date = pd.to_datetime(client.get('DUE_DATE'), errors='coerce')

            # STATUS ENGINE
            if balance <= 0:
                status = "CLEARED"
            elif due_date and due_date.date() < today:
                status = "OVERDUE"
            else:
                status = "ACTIVE"

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Loan", f"UGX {loan:,.0f}")
            c2.metric("Paid", f"UGX {paid:,.0f}")
            c3.metric("Balance", f"UGX {balance:,.0f}", delta_color="inverse")
            c4.metric("Status", status)

            st.write("---")

            # --- 5. RUNNING BALANCE (🔥 IMPORTANT) ---
            st.markdown("### 📊 Running Balance")

            if not client_pays.empty:
                running = loan
                history = []

                for _, row in client_pays.iterrows():
                    running -= float(row['AMOUNT_PAID'])
                    history.append({
                        "DATE": row['DATE'].strftime('%Y-%m-%d'),
                        "PAID": row['AMOUNT_PAID'],
                        "BALANCE": running,
                        "MODE": row.get('PAYMENT_MODE', '')
                    })

                hist_df = pd.DataFrame(history)

                st.dataframe(hist_df, use_container_width=True, hide_index=True)

                # Chart
                fig = px.line(hist_df, x='DATE', y='BALANCE', markers=True)
                fig.update_traces(line_color='#1e3a8a')
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("No payments yet.")

            st.write("---")

            # --- 6. PAYMENT SUMMARY ---
            st.markdown("### 📈 Payment Insights")

            if not client_pays.empty:
                total_tx = len(client_pays)
                avg_pay = paid / total_tx if total_tx > 0 else 0

                s1, s2 = st.columns(2)
                s1.metric("Transactions", total_tx)
                s2.metric("Avg Payment", f"UGX {avg_pay:,.0f}")

            st.write("---")

            # --- 7. PDF GENERATOR (UPGRADED) ---
            def generate_pdf():
                pdf = FPDF()
                pdf.add_page()

                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, "ZOE CONSULTS SMC LTD", ln=True, align='C')

                pdf.set_font("Arial", '', 10)
                pdf.cell(200, 8, f"Client: {selected}", ln=True)
                pdf.cell(200, 8, f"Status: {status}", ln=True)
                pdf.cell(200, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d')}", ln=True)

                pdf.ln(5)

                pdf.cell(200, 8, f"Loan: UGX {loan:,.0f}", ln=True)
                pdf.cell(200, 8, f"Paid: UGX {paid:,.0f}", ln=True)
                pdf.cell(200, 8, f"Balance: UGX {balance:,.0f}", ln=True)

                pdf.ln(5)

                pdf.set_font("Arial", 'B', 10)
                pdf.cell(60, 8, "Date", 1)
                pdf.cell(60, 8, "Paid", 1)
                pdf.cell(60, 8, "Balance", 1, 1)

                pdf.set_font("Arial", '', 10)

                if not client_pays.empty:
                    run = loan
                    for _, r in client_pays.iterrows():
                        run -= float(r['AMOUNT_PAID'])
                        pdf.cell(60, 8, str(r['DATE'].date()), 1)
                        pdf.cell(60, 8, f"{r['AMOUNT_PAID']:,.0f}", 1)
                        pdf.cell(60, 8, f"{run:,.0f}", 1, 1)
                else:
                    pdf.cell(180, 8, "No payments", 1, 1)

                return pdf.output(dest='S').encode('latin-1')

            if st.button("📄 Generate Statement"):
                pdf_bytes = generate_pdf()
                b64 = base64.b64encode(pdf_bytes).decode()

                href = f'<a href="data:application/octet-stream;base64,{b64}" download="Statement_{selected}.pdf">Download PDF</a>'
                st.markdown(href, unsafe_allow_html=True)

            st.write("---")

            # --- 8. RAW PAYMENT TABLE ---
            st.markdown("### 🕒 Payment History")

            if not client_pays.empty:
                display = client_pays.copy()
                display['AMOUNT_PAID'] = display['AMOUNT_PAID'].apply(lambda x: f"{float(x):,.0f}")
                st.dataframe(display, use_container_width=True, hide_index=True)
            else:
                st.info("No payment records found.")

    else:
        st.info("No clients available.")

# PAGE: OVERDUE TRACKER (The Debt Collector)
elif page == "Overdue Tracker":
    st.markdown('<div class="main-title">🚨 Overdue Intelligence Dashboard</div>', unsafe_allow_html=True)

    # --- 1. LOAD DATA ---
    local_df = pd.DataFrame(st.session_state.get('local_registry', []))
    combined = pd.concat([df, local_df], ignore_index=True)

    local_pay = pd.DataFrame(st.session_state.get('local_repayments', []))
    all_payments = pd.concat([pay_df, local_pay], ignore_index=True)

    if not combined.empty:

        combined = combined.drop_duplicates(subset=['NIN'], keep='last')

        today = datetime.now().date()

        # --- 2. LAST PAYMENT TRACKING ---
        if not all_payments.empty:
            all_payments['DATE'] = pd.to_datetime(all_payments['DATE'], errors='coerce')

            last_pay = all_payments.groupby('CUSTOMER_NAME')['DATE'].max().reset_index()
            last_pay['DATE'] = last_pay['DATE'].dt.date

            combined = combined.merge(last_pay, on='CUSTOMER_NAME', how='left')
            combined.rename(columns={'DATE': 'LAST_PAYMENT'}, inplace=True)
        else:
            combined['LAST_PAYMENT'] = None

        # --- 3. CALCULATE OVERDUE ---
        combined['DUE_DATE'] = pd.to_datetime(combined['DUE_DATE'], errors='coerce').dt.date
        combined['OUTSTANDING_AMOUNT'] = pd.to_numeric(combined['OUTSTANDING_AMOUNT'], errors='coerce').fillna(0)

        overdue = combined[
            (combined['OUTSTANDING_AMOUNT'] > 0) &
            (combined['DUE_DATE'] < today)
        ].copy()

        if not overdue.empty:

            # --- 4. DAYS OVERDUE ---
            overdue['DAYS_OVERDUE'] = (today - overdue['DUE_DATE']).dt.days

            # --- 5. RISK LEVEL ENGINE ---
            def risk_level(days):
                if days <= 7:
                    return "LOW"
                elif days <= 30:
                    return "MEDIUM"
                elif days <= 60:
                    return "HIGH"
                else:
                    return "CRITICAL"

            overdue['RISK'] = overdue['DAYS_OVERDUE'].apply(risk_level)

            # --- 6. SORT WORST FIRST ---
            overdue = overdue.sort_values(by='DAYS_OVERDUE', ascending=False)

            # --- 7. SUMMARY KPIs ---
            total_overdue = overdue['OUTSTANDING_AMOUNT'].sum()
            avg_days = overdue['DAYS_OVERDUE'].mean()

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Overdue", f"UGX {total_overdue:,.0f}")
            k2.metric("Clients Overdue", len(overdue))
            k3.metric("Avg Days Late", f"{avg_days:.0f} days")

            st.write("---")

            # --- 8. FILTER BY RISK ---
            risk_filter = st.selectbox("Filter by Risk Level", ["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"])

            if risk_filter != "ALL":
                overdue = overdue[overdue['RISK'] == risk_filter]

            # --- 9. DISPLAY CARDS ---
            for _, row in overdue.iterrows():

                name = row['CUSTOMER_NAME']
                balance = float(row['OUTSTANDING_AMOUNT'])
                days = row['DAYS_OVERDUE']
                risk = row['RISK']
                phone = str(row.get('CONTACT', ''))

                # Color by risk
                if risk == "LOW":
                    color = "#3b82f6"
                elif risk == "MEDIUM":
                    color = "#f59e0b"
                elif risk == "HIGH":
                    color = "#ef4444"
                else:
                    color = "#7f1d1d"

                with st.container():
                    c1, c2, c3 = st.columns([2, 1, 1])

                    c1.markdown(f"""
                        <div style="border-left: 5px solid {color}; padding-left:10px;">
                        <b>{name}</b><br>
                        <span style='color:#64748b;'>Overdue by {days} days</span>
                        </div>
                    """, unsafe_allow_html=True)

                    c2.markdown(f"**UGX {balance:,.0f}**")
                    c2.caption("Outstanding")

                    # --- 10. WHATSAPP ---
                    clean_phone = "".join(filter(str.isdigit, phone))

                    if clean_phone:
                        msg = f"Reminder: Your loan balance of UGX {balance:,.0f} is overdue by {days} days. Kindly clear it immediately to avoid further action."

                        wa_link = f"https://wa.me/{clean_phone}?text={msg.replace(' ', '%20')}"

                        c3.markdown(f"""
                            <a href="{wa_link}" target="_blank">
                                <div style="background:{color}; color:white; padding:10px;
                                border-radius:8px; text-align:center; font-weight:bold;">
                                Send Reminder
                                </div>
                            </a>
                        """, unsafe_allow_html=True)
                    else:
                        c3.button("No Contact", disabled=True, key=f"btn_{name}")

                    st.divider()

        else:
            st.balloons()
            st.success("🎉 All clients are up to date!")

    else:
        st.info("No borrowers available.")
# PAGE: OPERATING EXPENSES
elif page == "Expenses":
    st.markdown('<div class="main-title">📉 Expense Intelligence Center</div>', unsafe_allow_html=True)

    # --- 1. INIT LOCAL STORAGE ---
    if 'local_expenses' not in st.session_state:
        st.session_state.local_expenses = []

    # --- 2. COMBINE DATA ---
    local_exp_df = pd.DataFrame(st.session_state.local_expenses)
    combined = pd.concat([expense_df, local_exp_df], ignore_index=True)

    # --- 3. RECORD EXPENSE ---
    with st.expander("➕ Log Expense", expanded=True):
        with st.form("exp_form", clear_on_submit=True):
            c1, c2 = st.columns(2)

            category = c1.selectbox("Category", ["Rent", "Salaries", "Utilities", "Marketing", "Transport", "Other"])
            amount = c2.number_input("Amount (UGX)", min_value=0, step=5000)

            date = st.date_input("Date", value=datetime.now())
            receipt = st.text_input("Receipt No")
            desc = st.text_input("Description")

            if st.form_submit_button("💾 Save Expense", use_container_width=True):

                if amount > 0 and desc:
                    new_exp = {
                        "DATE": str(date),
                        "CATEGORY": category,
                        "DESCRIPTION": desc,
                        "AMOUNT": amount,
                        "RECEIPT_NO": receipt
                    }

                    st.session_state.local_expenses.append(new_exp)

                    try:
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        client = gspread.service_account_from_dict(creds_dict)

                        ws = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Expenses")
                        ws.append_row(list(new_exp.values()), value_input_option='USER_ENTERED')

                        st.success("✅ Expense saved!")
                        st.cache_data.clear()

                    except:
                        st.warning("Saved locally. Cloud sync pending.")

                else:
                    st.warning("Enter amount and description.")

    st.write("---")

    # --- 4. CLEAN DATA ---
    if not combined.empty:
        combined['AMOUNT'] = pd.to_numeric(combined['AMOUNT'], errors='coerce').fillna(0)
        combined['DATE'] = pd.to_datetime(combined['DATE'], errors='coerce')

    # --- 5. KPI DASHBOARD ---
    if not combined.empty:

        total = combined['AMOUNT'].sum()

        this_month = combined[
            combined['DATE'].dt.month == datetime.now().month
        ]['AMOUNT'].sum()

        avg_exp = combined['AMOUNT'].mean()

        k1, k2, k3 = st.columns(3)
        k1.metric("Total Expenses", f"UGX {total:,.0f}")
        k2.metric("This Month", f"UGX {this_month:,.0f}")
        k3.metric("Avg Expense", f"UGX {avg_exp:,.0f}")

    st.write("---")

    # --- 6. CATEGORY ANALYSIS ---
    st.markdown("### 📊 Category Breakdown")

    if not combined.empty:
        cat = combined.groupby('CATEGORY')['AMOUNT'].sum().sort_values(ascending=False)

        fig = px.pie(
            values=cat.values,
            names=cat.index,
            hole=0.5,
            color_discrete_sequence=px.colors.sequential.Blues
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No expense data.")

    st.write("---")

    # --- 7. MONTHLY TREND ---
    st.markdown("### 📈 Monthly Trend")

    if not combined.empty:
        combined['MONTH'] = combined['DATE'].dt.to_period("M").astype(str)

        monthly = combined.groupby('MONTH')['AMOUNT'].sum()

        fig2 = px.line(monthly, x=monthly.index, y=monthly.values, markers=True)
        fig2.update_traces(line_color='#1e3a8a')

        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.info("No trend data.")

    st.write("---")

    # --- 8. FILTER + TABLE ---
    st.markdown("### 📜 Expense Ledger")

    if not combined.empty:

        # Filters
        f1, f2 = st.columns(2)
        selected_cat = f1.selectbox("Filter Category", ["All"] + combined['CATEGORY'].dropna().unique().tolist())
        selected_month = f2.selectbox("Filter Month", ["All"] + combined['DATE'].dt.strftime("%Y-%m").dropna().unique().tolist())

        filtered = combined.copy()

        if selected_cat != "All":
            filtered = filtered[filtered['CATEGORY'] == selected_cat]

        if selected_month != "All":
            filtered = filtered[filtered['DATE'].dt.strftime("%Y-%m") == selected_month]

        # Format
        display = filtered.copy()
        display['AMOUNT'] = display['AMOUNT'].apply(lambda x: f"{x:,.0f}")

        st.dataframe(display.sort_values(by='DATE', ascending=False), use_container_width=True, hide_index=True)

        st.info(f"Filtered Total: UGX {filtered['AMOUNT'].sum():,.0f}")

    else:
        st.info("No expenses recorded.")
# PAGE: PETTY CASH (UPGRADED)
elif page == "PettyCash":
    st.markdown('<div class="main-title">💵 Petty Cash Intelligence Center</div>', unsafe_allow_html=True)

    # --- 1. INIT STORAGE ---
    if 'local_petty_cash' not in st.session_state:
        st.session_state.local_petty_cash = []

    # --- 2. LOAD DATA ---
    local_df = pd.DataFrame(st.session_state.local_petty_cash)
    combined = pd.concat([petty_df, local_df], ignore_index=True) if 'petty_df' in locals() else local_df

    # --- 3. ENTRY FORM ---
    with st.expander("➕ Record Cash Movement", expanded=True):
        with st.form("petty_form", clear_on_submit=True):

            c1, c2 = st.columns(2)

            date = c1.date_input("Date", datetime.now())
            entry_type = c2.selectbox("Type", ["INFLOW", "OUTFLOW"])

            category = c1.selectbox("Category", [
                "Office Supplies", "Transport", "Fuel",
                "Maintenance", "Airtime", "Miscellaneous"
            ])

            amount = c2.number_input("Amount (UGX)", min_value=0, step=1000)

            desc = st.text_input("Description")

            if st.form_submit_button("💾 Save Entry", use_container_width=True):

                if amount > 0 and desc:

                    new_entry = {
                        "DATE": str(date),
                        "TYPE": entry_type,
                        "CATEGORY": category,
                        "DESCRIPTION": desc,
                        "AMOUNT": amount
                    }

                    st.session_state.local_petty_cash.append(new_entry)

                    # --- CLOUD SYNC (OPTIONAL LIKE EXPENSES) ---
                    try:
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        client = gspread.service_account_from_dict(creds_dict)

                        ws = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("PettyCash")
                        ws.append_row(list(new_entry.values()), value_input_option='USER_ENTERED')

                        st.success("✅ Saved & Synced")

                    except:
                        st.warning("Saved locally (offline mode)")

                else:
                    st.warning("Enter amount and description")

    st.write("---")

    # --- 4. CLEAN DATA ---
    if not combined.empty:
        combined['DATE'] = pd.to_datetime(combined['DATE'], errors='coerce')
        combined['AMOUNT'] = pd.to_numeric(combined['AMOUNT'], errors='coerce').fillna(0)

        combined = combined.sort_values("DATE")

        # --- RUNNING BALANCE ENGINE ---
        combined['SIGNED'] = combined.apply(
            lambda x: x['AMOUNT'] if x['TYPE'] == "INFLOW" else -x['AMOUNT'],
            axis=1
        )
        combined['BALANCE'] = combined['SIGNED'].cumsum()

    # --- 5. KPI DASHBOARD ---
    if not combined.empty:

        total_in = combined[combined['TYPE'] == "INFLOW"]['AMOUNT'].sum()
        total_out = combined[combined['TYPE'] == "OUTFLOW"]['AMOUNT'].sum()
        balance = total_in - total_out

        today = datetime.now().month
        month_exp = combined[
            (combined['TYPE'] == "OUTFLOW") &
            (combined['DATE'].dt.month == today)
        ]['AMOUNT'].sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Cash In", f"UGX {total_in:,.0f}")
        k2.metric("Cash Out", f"UGX {total_out:,.0f}")
        k3.metric("Balance", f"UGX {balance:,.0f}")
        k4.metric("This Month Out", f"UGX {month_exp:,.0f}")

    st.write("---")

    # --- 6. CASH FLOW CHART ---
    st.markdown("### 📈 Cash Balance Trend")

    if not combined.empty:
        fig = px.line(combined, x='DATE', y='BALANCE', markers=True)
        fig.update_traces(line_color='#16a34a')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet")

    st.write("---")

    # --- 7. CATEGORY ANALYSIS ---
    st.markdown("### 📊 Spending by Category")

    if not combined.empty:
        outflow = combined[combined['TYPE'] == "OUTFLOW"]

        if not outflow.empty:
            cat = outflow.groupby('CATEGORY')['AMOUNT'].sum()

            fig2 = px.pie(
                values=cat.values,
                names=cat.index,
                hole=0.5,
                color_discrete_sequence=px.colors.sequential.Reds
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No expenses recorded")

    st.write("---")

    # --- 8. FILTERS ---
    st.markdown("### 🔍 Filter Cashbook")

    if not combined.empty:
        f1, f2 = st.columns(2)

        type_filter = f1.selectbox("Type", ["ALL", "INFLOW", "OUTFLOW"])
        month_filter = f2.selectbox(
            "Month",
            ["ALL"] + combined['DATE'].dt.strftime("%Y-%m").dropna().unique().tolist()
        )

        filtered = combined.copy()

        if type_filter != "ALL":
            filtered = filtered[filtered['TYPE'] == type_filter]

        if month_filter != "ALL":
            filtered = filtered[filtered['DATE'].dt.strftime("%Y-%m") == month_filter]

        # Format display
        display = filtered.copy()
        display['AMOUNT'] = display['AMOUNT'].apply(lambda x: f"{x:,.0f}")
        display['BALANCE'] = display['BALANCE'].apply(lambda x: f"{x:,.0f}")

        st.dataframe(
            display.sort_values(by='DATE', ascending=False),
            use_container_width=True,
            hide_index=True
        )

        st.info(f"Filtered Balance: UGX {filtered['SIGNED'].sum():,.0f}")

        # --- EXPORT ---
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", csv, "petty_cash.csv", "text/csv")

    else:
        st.info("No petty cash records yet")
# PAGE: PAYROLL (UPGRADED PRO VERSION)
elif page == "Payroll":
    st.markdown('<div class="main-title">👔 Team Payroll Management</div>', unsafe_allow_html=True)

    # --- 1. INIT STATE ---
    if 'local_payroll' not in st.session_state:
        st.session_state.local_payroll = []

    local_pay_df = pd.DataFrame(st.session_state.local_payroll)
    combined = pd.concat([payroll_df, local_pay_df], ignore_index=True)

    if not combined.empty:
        combined['NET_PAY'] = pd.to_numeric(combined['NET_PAY'], errors='coerce').fillna(0)
        combined['DATE'] = pd.to_datetime(combined['DATE'], errors='coerce')

    # --- 2. KPI DASHBOARD ---
    if not combined.empty:
        total = combined['NET_PAY'].sum()
        this_month = combined[
            combined['DATE'].dt.month == datetime.now().month
        ]['NET_PAY'].sum()

        avg_salary = combined['NET_PAY'].mean()

        k1, k2, k3 = st.columns(3)
        k1.metric("Total Payroll", f"UGX {total:,.0f}")
        k2.metric("This Month", f"UGX {this_month:,.0f}")
        k3.metric("Avg Salary", f"UGX {avg_salary:,.0f}")

    st.write("---")

    # --- 3. PROCESS SALARY ---
    with st.expander("➕ Process Salary", expanded=True):
        with st.form("payroll_form", clear_on_submit=True):

            staff = st.text_input("Staff Name")

            c1, c2, c3 = st.columns(3)
            basic = c1.number_input("Basic", min_value=0, step=10000)
            bonus = c2.number_input("Bonus", min_value=0, step=5000)
            deduct = c3.number_input("Deductions", min_value=0, step=5000)

            net = basic + bonus - deduct
            st.markdown(f"### 💰 Net Pay: UGX {net:,.0f}")

            date = st.date_input("Payment Date", value=datetime.now())

            if st.form_submit_button("💳 Process Payment", use_container_width=True):

                if staff and net > 0:

                    new = {
                        "STAFF_NAME": staff,
                        "BASIC_SALARY": basic,
                        "BONUS": bonus,
                        "DEDUCTIONS": deduct,
                        "NET_PAY": net,
                        "DATE": str(date)
                    }

                    st.session_state.local_payroll.append(new)

                    try:
                        creds_dict = dict(st.secrets["gcp_service_account"])
                        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                        client = gspread.service_account_from_dict(creds_dict)

                        ws = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Payroll")
                        ws.append_row(list(new.values()), value_input_option='USER_ENTERED')

                        st.success(f"✅ Salary processed for {staff}")
                        st.cache_data.clear()
                        st.rerun()

                    except:
                        st.warning("Saved locally. Sync pending.")

                else:
                    st.warning("Enter valid staff + amount")

    st.write("---")

    # --- 4. ANALYTICS ---
    st.markdown("### 📊 Payroll Insights")

    if not combined.empty:
        combined['MONTH'] = combined['DATE'].dt.to_period("M").astype(str)

        monthly = combined.groupby('MONTH')['NET_PAY'].sum()

        fig = px.line(monthly, x=monthly.index, y=monthly.values, markers=True)
        fig.update_traces(line_color='#1e3a8a')

        st.plotly_chart(fig, use_container_width=True)

        # Staff distribution
        staff_dist = combined.groupby('STAFF_NAME')['NET_PAY'].sum()

        fig2 = px.bar(
            staff_dist,
            x=staff_dist.index,
            y=staff_dist.values,
            color=staff_dist.values,
            color_continuous_scale="Blues"
        )

        st.plotly_chart(fig2, use_container_width=True)

    st.write("---")

    # --- 5. PAYSLIP GENERATOR ---
    st.markdown("### 🎫 Generate Pay Slip")

    if not combined.empty:

        staff_list = combined['STAFF_NAME'].unique()
        selected_staff = st.selectbox("Select Staff", staff_list)

        staff_records = combined[combined['STAFF_NAME'] == selected_staff]
        latest = staff_records.sort_values(by='DATE').iloc[-1]

        if st.button("📄 Generate Pay Slip"):

            def generate_pdf():
                pdf = FPDF()
                pdf.add_page()

                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, "ZOE CONSULTS SMC LTD", ln=True, align='C')

                pdf.ln(5)

                pdf.set_font("Arial", '', 11)
                pdf.cell(200, 8, f"Employee: {selected_staff}", ln=True)
                pdf.cell(200, 8, f"Date: {latest['DATE'].date()}", ln=True)

                pdf.ln(5)

                pdf.cell(200, 8, f"Basic: {latest['BASIC_SALARY']:,.0f}", ln=True)
                pdf.cell(200, 8, f"Bonus: {latest['BONUS']:,.0f}", ln=True)
                pdf.cell(200, 8, f"Deductions: {latest['DEDUCTIONS']:,.0f}", ln=True)

                pdf.ln(5)

                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 10, f"NET PAY: UGX {latest['NET_PAY']:,.0f}", ln=True)

                return pdf.output(dest='S').encode('latin-1')

            pdf_bytes = generate_pdf()
            b64 = base64.b64encode(pdf_bytes).decode()

            href = f'<a href="data:application/octet-stream;base64,{b64}" download="PaySlip_{selected_staff}.pdf">Download Pay Slip</a>'
            st.markdown(href, unsafe_allow_html=True)

    st.write("---")

    # --- 6. FILTERABLE TABLE ---
    st.markdown("### 📜 Payroll Records")

    if not combined.empty:

        f1, f2 = st.columns(2)

        staff_filter = f1.selectbox("Filter Staff", ["All"] + combined['STAFF_NAME'].unique().tolist())
        month_filter = f2.selectbox("Filter Month", ["All"] + combined['DATE'].dt.strftime("%Y-%m").unique().tolist())

        filtered = combined.copy()

        if staff_filter != "All":
            filtered = filtered[filtered['STAFF_NAME'] == staff_filter]

        if month_filter != "All":
            filtered = filtered[filtered['DATE'].dt.strftime("%Y-%m") == month_filter]

        display = filtered.copy()
        display['NET_PAY'] = display['NET_PAY'].apply(lambda x: f"{x:,.0f}")

        st.dataframe(display.sort_values(by='DATE', ascending=False), use_container_width=True, hide_index=True)

        st.info(f"Filtered Total: UGX {filtered['NET_PAY'].sum():,.0f}")

    else:
        st.info("No payroll records yet.")
elif page == "Add Payment":
    st.markdown('<div class="main-title">📥 Post Loan Repayment</div>', unsafe_allow_html=True)

    # 1️⃣ Initialize local memory
    if 'local_repayments' not in st.session_state:
        st.session_state.local_repayments = []

    # 2️⃣ Merge borrowers (Cloud + Local)
    local_borrowers = pd.DataFrame(st.session_state.get('local_registry', []))
    combined_borrowers = pd.concat([df, local_borrowers], ignore_index=True).drop_duplicates(subset=['NIN'], keep='last')

    if not combined_borrowers.empty:

        # --- CLIENT SEARCH & SELECTION ---
        search = st.text_input("🔍 Search Client by Name or NIN")
        filtered_clients = combined_borrowers[
            combined_borrowers['CUSTOMER_NAME'].str.contains(search, case=False, na=False) |
            combined_borrowers['NIN'].str.contains(search, na=False)
        ] if search else combined_borrowers

        selected_client = st.selectbox("Select Client", options=filtered_clients['CUSTOMER_NAME'].tolist())

        if selected_client:

            client_data = combined_borrowers[combined_borrowers['CUSTOMER_NAME'] == selected_client].iloc[0]
            loan_amount = float(client_data.get('LOAN_AMOUNT', 0))
            
            # Compute already paid amount
            all_payments = pd.concat([pay_df, pd.DataFrame(st.session_state.local_repayments)], ignore_index=True)
            paid_amount = all_payments.loc[all_payments['CUSTOMER_NAME'] == selected_client, 'AMOUNT_PAID'].sum()
            balance = loan_amount - paid_amount

            # Status Engine
            today = datetime.now().date()
            due_date = pd.to_datetime(client_data.get('DUE_DATE'), errors='coerce').date() if client_data.get('DUE_DATE') else None
            status = "CLEARED" if balance <= 0 else "OVERDUE" if due_date and due_date < today else "ACTIVE"

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Loan", f"UGX {loan_amount:,.0f}")
            c2.metric("Paid", f"UGX {paid_amount:,.0f}")
            c3.metric("Balance", f"UGX {balance:,.0f}", delta_color="inverse")
            c4.metric("Status", status)

            st.write("---")

            # --- PAYMENT FORM ---
            with st.form("add_payment", clear_on_submit=True):
                col1, col2 = st.columns(2)
                ap = col1.number_input("Amount Paid (UGX)", min_value=0, max_value=balance, step=10000)
                p_mode = col2.selectbox("Payment Mode", ["Mobile Money", "Cash", "Bank Deposit"])
                p_note = st.text_input("Note / Receipt No (Optional)")

                if st.form_submit_button("🚀 Post Repayment"):
                    if ap > 0:
                        today_str = str(datetime.now().date())
                        new_payment = {
                            "CUSTOMER_NAME": selected_client,
                            "AMOUNT_PAID": ap,
                            "DATE": today_str,
                            "PAYMENT_MODE": p_mode,
                            "NOTES": p_note
                        }

                        # Save locally
                        st.session_state.local_repayments.append(new_payment)

                        # Try syncing to Google Sheets
                        try:
                            creds_dict = dict(st.secrets["gcp_service_account"])
                            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                            client_gs = gspread.service_account_from_dict(creds_dict)
                            ws = client_gs.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg").worksheet("Repayments")
                            ws.append_row(list(new_payment.values()), value_input_option='USER_ENTERED')
                            st.balloons()
                            st.success(f"✅ UGX {ap:,.0f} collected from {selected_client}!")
                            st.cache_data.clear()
                        except Exception as e:
                            st.warning(f"⚠️ Saved locally, Cloud sync pending: {e}")
                    else:
                        st.warning("Enter a valid amount.")

            st.write("---")

            # --- DISPLAY COLLECTIONS LEDGER ---
            st.markdown("### 🕒 Recent Collections Ledger")
            local_pay_df = pd.DataFrame(st.session_state.local_repayments)
            combined_payments = pd.concat([pay_df, local_pay_df], ignore_index=True)

            if not combined_payments.empty:
                combined_payments['AMOUNT_PAID'] = combined_payments['AMOUNT_PAID'].apply(lambda x: f"{float(x):,.0f}")
                st.dataframe(
                    combined_payments.sort_values(by='DATE', ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_order=("DATE", "CUSTOMER_NAME", "AMOUNT_PAID", "PAYMENT_MODE", "NOTES")
                )
                total_rev = pd.to_numeric(combined_payments['AMOUNT_PAID'].str.replace(",", ""), errors='coerce').sum()
                st.info(f"📈 Total Revenue Collected: UGX {total_rev:,.0f}")
                
                # Optional: Export PDF receipt
                if st.button("📄 Download Client Receipt"):
                    from fpdf import FPDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(200, 10, "Repayment Receipt", ln=True, align='C')
                    pdf.set_font("Arial", '', 12)
                    pdf.ln(10)
                    pdf.cell(200, 8, f"Client: {selected_client}", ln=True)
                    pdf.cell(200, 8, f"Date: {today}", ln=True)
                    pdf.cell(200, 8, f"Amount Paid: UGX {ap:,.0f}", ln=True)
                    pdf.cell(200, 8, f"Payment Mode: {p_mode}", ln=True)
                    pdf.cell(200, 8, f"Balance Remaining: UGX {balance - ap:,.0f}", ln=True)
                    pdf.ln(10)
                    pdf.cell(200, 8, "Thank you for your payment!", ln=True)
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    b64 = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/octet-stream;base64,{b64}" download="Receipt_{selected_client}.pdf">Download Receipt PDF</a>'
                    st.markdown(href, unsafe_allow_html=True)
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
