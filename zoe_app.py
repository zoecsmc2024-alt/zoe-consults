import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import gspread
import io
import base64
import json
import os
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Place this right after your imports
@st.cache_resource
def connect_to_gsheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

def open_sheet(sheet_name):
    client = connect_to_gsheets()
    # Ensure this name matches your Google Sheet exactly
    sheet = client.open(sheet_name) 
    return sheet

# Now define your load/save helpers
def load_data(sheet, worksheet_name):
    worksheet = sheet.worksheet(worksheet_name)
    return pd.DataFrame(worksheet.get_all_records())

def save_data(sheet, worksheet_name, dataframe):
    worksheet = sheet.worksheet(worksheet_name)
    worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

# ==============================
# 1. SYSTEM CONFIGURATION
# ==============================
st.set_page_config(page_title="Zoe Fintech", layout="wide")

st.markdown("""
<style>
    /* 1. MAIN WORKSPACE - Soft Sky Blue */
    .stApp {
        background-color: #F0F7FF !important;
    }

    /* 2. SIDEBAR - Deep Midnight (Fixed Indentation & Colors) */
    section[data-testid="stSidebar"] {
        background-color: #020617 !important;
        border-right: 1px solid #1E293B;
    }

    /* Reset Sidebar Buttons to be Transparent/Dark */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        color: #94A3B8 !important;
        border: none !important;
        box-shadow: none !important; /* Removes the white box */
        transform: none !important;
        text-align: left !important;
        width: 100% !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        color: #38BDF8 !important;
        background-color: rgba(56, 189, 248, 0.05) !important;
    }

    /* 3. FLOATING CONTENT - Only for Main Page Metrics & Data */
    /* We target specific Streamlit components in the main area */
    div[data-testid="stMetric"], .stTable, [data-testid="stDataFrame"], .stAlert {
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.5) !important;
        border-radius: 16px !important;
        
        /* The Float Shadow */
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 
                    0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
        padding: 15px !important;
    }

    /* 4. ACTIVE MENU ITEM - Blue Glow on Dark Sidebar */
    .active-menu-item {
        background: linear-gradient(90deg, rgba(56, 189, 248, 0.15) 0%, rgba(56, 189, 248, 0) 100%) !important;
        border-left: 4px solid #38BDF8 !important;
        color: #38BDF8 !important;
        padding: 12px 24px !important;
        font-weight: 700 !important;
    }
    /* 5. SIDEBAR PROFILE - Premium Branding */
    .sidebar-brand {
        color: #FFFFFF !important;
        font-size: 22px !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
        margin-bottom: -5px !important;
        text-shadow: 0px 0px 15px rgba(255, 255, 255, 0.2);
    }

    .sidebar-user {
        color: #38BDF8 !important; /* Electric Baby Blue */
        font-size: 14px !important;
        font-weight: 600 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* A small glowing "Online" indicator */
    .online-dot {
        height: 8px;
        width: 8px;
        background-color: #10B981; /* Emerald Green */
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #10B981;
    }
</style>
""", unsafe_allow_html=True)
# ==============================
# 2. GOOGLE SHEETS & DATA HELPERS
# ==============================
@st.cache_resource
def connect_to_gsheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def load_data(sheet, worksheet_name):
    try:
        worksheet = sheet.worksheet(worksheet_name)
        return pd.DataFrame(worksheet.get_all_records())
    except:
        return pd.DataFrame()

def save_data(sheet, worksheet_name, dataframe):
    worksheet = sheet.worksheet(worksheet_name)
    worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

# Initialize Connection
client = connect_to_gsheets()
sheet = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg")

# ==============================
# 3. UTILITY FUNCTIONS (WhatsApp, PDF, Logo)
# ==============================
def send_whatsapp(phone, msg):
    client_tw = Client(st.secrets["TWILIO_SID"], st.secrets["TWILIO_TOKEN"])
    client_tw.messages.create(
        from_='whatsapp:+14155238886',
        body=msg,
        to=f'whatsapp:{phone}'
    )

def make_receipt(data, file):
    doc = SimpleDocTemplate(file)
    styles = getSampleStyleSheet()
    content = [
        Paragraph("ZOE LENDING SERVICES", styles['Title']),
        Spacer(1, 10),
        Paragraph(f"Borrower: {data['b']}", styles['Normal']),
        Paragraph(f"Amount: {data['a']}", styles['Normal']),
        Paragraph(f"Date: {data['d']}", styles['Normal'])
    ]
    doc.build(content)

def save_logo(sheet, image_file):
    settings = load_data(sheet, "Settings")
    encoded = base64.b64encode(image_file.read()).decode()
    if settings.empty:
        settings = pd.DataFrame([{"Key": "logo", "Value": encoded}])
    else:
        if "logo" in settings["Key"].values:
            settings.loc[settings["Key"] == "logo", "Value"] = encoded
        else:
            settings = pd.concat([settings, pd.DataFrame([{"Key": "logo", "Value": encoded}])])
    save_data(sheet, "Settings", settings)

def login():
    st.title("🔐 Login")
    
    # Load the Users sheet
    users = load_data(sheet, "Users")

    if users.empty:
        st.error("⚠️ The 'Users' sheet is empty or not found.")
        return

    # Create the input boxes
    u_input = st.text_input("Username")
    p_input = st.text_input("Password", type="password")

    if st.button("Login"):
        # We find the column names regardless of whether they are 'U' or 'Username'
        # This looks for any column starting with 'U' and 'P'
        u_col = next((c for c in users.columns if c.lower().startswith('u')), None)
        p_col = next((c for c in users.columns if c.lower().startswith('p')), None)
        r_col = next((c for c in users.columns if c.lower().startswith('r')), None) # Role

        if u_col and p_col:
            # Match the input to the sheet data
            user_match = users[(users[u_col].astype(str) == u_input) & 
                               (users[p_col].astype(str) == p_input)]
            
            if not user_match.empty:
                st.session_state.logged_in = True
                st.session_state.user = u_input
                # Set role to Admin if 'Role' column is missing
                st.session_state.role = user_match.iloc[0][r_col] if r_col else "Admin"
                st.success(f"Welcome back, {u_input}!")
                st.rerun()
            else:
                st.error("❌ Invalid Username or Password")
        else:
            st.error(f"Could not find Login columns. Your sheet has: {list(users.columns)}")
# ==============================
# 5. SIDEBAR & NAVIGATION
# ==============================
def sidebar():
    role = st.session_state.get("role", "Staff")
    current_user = st.session_state.get("user", "Guest")

    # Brand Title
    st.sidebar.markdown('<p class="sidebar-brand">ZOE ADMIN 💼</p>', unsafe_allow_html=True)
    
    # User Profile with Online Status
    st.sidebar.markdown(
        f'''<p class="sidebar-user">
            <span class="online-dot"></span> 👤 {current_user} ({role})
        </p>''', 
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown("---")
    
    # ... (the rest of your menu loop)

    menu = {
        "Overview": "📊", "Borrowers": "👥", "Loans": "💵", "Collateral": "🛡️",
        "Calendar": "📅", "Ledger": "📄", "Overdue Tracker": "⏰",
        "Payments": "💵", "Expenses": "📁", "PettyCash": "💵",
        "Payroll": "🧾", "Reports": "📊", "Settings": "⚙️"
    }
    
    restricted = ["Settings", "Reports", "Payroll"]
    if "page" not in st.session_state:
        st.session_state.page = "Overview"

    for item, icon in menu.items():
        if role != "Admin" and item in restricted:
            continue
            
        if st.session_state.page == item:
            # Active Page: Neon Sky Glow
            st.sidebar.markdown(f'<div class="active-menu-item">{icon} &nbsp;&nbsp; {item}</div>', unsafe_allow_html=True)
        else:
            # Inactive Page: Muted Gray-Blue
            if st.sidebar.button(f"{icon} &nbsp;&nbsp; {item}", key=f"btn_{item}"):
                st.session_state.page = item
                st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

sidebar()
# Check if user exists in memory before trying to print the name
if st.session_state.get("logged_in") and "user" in st.session_state:
    st.markdown(f"### Welcome {st.session_state.user} 👋")
else:
    st.markdown("### Welcome to Zoe Fintech 👋")

# ==============================
# 6. PAGE ROUTING & CONTENT
# ==============================

# --- Move this to the TOP of your script (outside the IF/ELIF blocks) ---
def open_sheet(sheet_name):
    client = connect_to_gsheets()
    # Using your specific ID for Zoe_Data
    sheet = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg") 
    return sheet

# ==============================
# UPGRADED OVERVIEW PAGE
# ==============================
if st.session_state.page == "Overview":
    st.title("📊 Financial Dashboard")
    
    # 1. Open the sheet and load data
    try:
        sheet = open_sheet("Zoe_Data")
        df = load_data(sheet, "Loans")
    except Exception as e:
        st.error(f"Could not connect to Google Sheets: {e}")
        df = pd.DataFrame()

    # 2. Check if data is available
    if df.empty:
        st.warning("No data available in the 'Loans' worksheet.")
    else:
        # ==============================
        # CLEAN DATA
        # ==============================
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
        df["Interest"] = pd.to_numeric(df["Interest"], errors="coerce").fillna(0)
        df["Amount_Paid"] = pd.to_numeric(df.get("Amount_Paid", 0), errors="coerce").fillna(0)

        df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
        df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")

        today = pd.Timestamp.today()
        
        # (Rest of your metrics and chart logic follows here, indented by 8 spaces...)
        # ==============================
        # CLEAN DATA
        # ==============================
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        df["Interest"] = pd.to_numeric(df["Interest"], errors="coerce")
        df["Amount_Paid"] = pd.to_numeric(df.get("Amount_Paid", 0), errors="coerce")

        df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
        df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")

        today = pd.Timestamp.today()

        # ==============================
        # AUTO OVERDUE DETECTION
        # ==============================
        df["Auto_Status"] = df["Status"]
        df.loc[
            (df["End_Date"] < today) & (df["Amount_Paid"] < df["Amount"] + df["Interest"]),
            "Auto_Status"
        ] = "Overdue"

        # ==============================
        # METRICS
        # ==============================
        total_loans = df["Amount"].sum()
        total_interest = df["Interest"].sum()
        total_expected = total_loans + total_interest

        total_paid = df["Amount_Paid"].sum()

        active_loans = df[df["Auto_Status"] == "Active"].shape[0]
        overdue_loans = df[df["Auto_Status"] == "Overdue"].shape[0]

        default_rate = (overdue_loans / len(df)) * 100 if len(df) > 0 else 0

        # ==============================
        # TODAY COLLECTIONS
        # ==============================
        today_collections = df[
            df["Start_Date"].dt.date == today.date()
        ]["Amount_Paid"].sum()

        # ==============================
        # METRIC CARDS
        # ==============================
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("💰 Total Issued", f"{total_loans:,.0f}")
        col2.metric("📈 Expected Profit", f"{total_interest:,.0f}")
        col3.metric("💵 Collected", f"{total_paid:,.0f}")
        col4.metric("⚠️ Overdue Loans", overdue_loans)

        col5, col6 = st.columns(2)
        col5.metric("📊 Default Rate", f"{default_rate:.1f}%")
        col6.metric("📅 Today’s Collections", f"{today_collections:,.0f}")

        st.markdown("---")

        # ==============================
        # STATUS PIE CHART
        # ==============================
        status_counts = df["Auto_Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]

        fig = px.pie(
            status_counts,
            names="Status",
            values="Count",
            title="Loan Status Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

        # ==============================
        # MONTHLY INCOME TREND
        # ==============================
        df["Month"] = df["Start_Date"].dt.to_period("M").astype(str)

        monthly_income = df.groupby("Month")["Amount_Paid"].sum().reset_index()

        fig2 = px.line(
            monthly_income,
            x="Month",
            y="Amount_Paid",
            title="Monthly Collections Trend"
        )

        st.plotly_chart(fig2, use_container_width=True)

        # ==============================
        # OVERDUE TABLE (IMPORTANT)
        # ==============================
        st.subheader("⚠️ Overdue Loans")

        overdue_df = df[df["Auto_Status"] == "Overdue"]

        if overdue_df.empty:
            st.success("No overdue loans 🎉")
        else:
            st.dataframe(
                overdue_df[[
                    "Borrower",
                    "Amount",
                    "Interest",
                    "End_Date",
                    "Amount_Paid"
                ]],
                use_container_width=True
            )

        # ==============================
        # RECENT ACTIVITY
        # ==============================
        st.subheader("📅 Recent Loans")

        recent = df.sort_values(by="Start_Date", ascending=False).head(5)
        st.dataframe(recent, use_container_width=True)


# --- BORROWERS PAGE ---
elif st.session_state.page == "Borrowers":

    st.title("👥 Borrowers Management")

    sheet = open_sheet("ZOE_DATA")
    df = load_data(sheet, "Borrowers")

    if df.empty:
        df = pd.DataFrame(columns=[
            "Borrower_ID", "Name", "Phone",
            "National_ID", "Address", "Status", "Date_Added"
        ])

    # ==============================
    # SEARCH & FILTER
    # ==============================
    st.subheader("🔍 Search & Filter")

    col1, col2 = st.columns(2)

    search = col1.text_input("Search (Name or Phone)")
    status_filter = col2.selectbox("Filter by Status", ["All", "Active", "Inactive"])

    filtered_df = df.copy()

    if search:
        filtered_df = filtered_df[
            filtered_df["Name"].str.contains(search, case=False, na=False) |
            filtered_df["Phone"].str.contains(search, case=False, na=False)
        ]

    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]

    # ==============================
    # DISPLAY BORROWERS
    # ==============================
    st.subheader("📋 Borrowers List")
    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("---")

    # ==============================
    # ADD BORROWER
    # ==============================
    st.subheader("➕ Add Borrower")

    with st.form("add_borrower", clear_on_submit=True):
        col1, col2 = st.columns(2)

        name = col1.text_input("Full Name")
        phone = col2.text_input("Phone Number")

        national_id = col1.text_input("National ID")
        address = col2.text_input("Address")

        submitted = st.form_submit_button("Add Borrower")

        if submitted:
            new_id = int(df["Borrower_ID"].max() + 1) if not df.empty else 1

            new_data = pd.DataFrame([{
                "Borrower_ID": new_id,
                "Name": name,
                "Phone": phone,
                "National_ID": national_id,
                "Address": address,
                "Status": "Active",
                "Date_Added": datetime.now().strftime("%Y-%m-%d")
            }])

            df = pd.concat([df, new_data], ignore_index=True)
            save_data(sheet, "Borrowers", df)

            st.success("Borrower added ✅")

    st.markdown("---")

    # ==============================
    # SELECT BORROWER (FOR ACTIONS)
    # ==============================
    st.subheader("⚙️ Manage Borrower")

    if not df.empty:
        selected_id = st.selectbox(
            "Select Borrower",
            filtered_df["Borrower_ID"]
        )

        borrower = df[df["Borrower_ID"] == selected_id].iloc[0]

        # ==============================
        # BORROWER SUMMARY
        # ==============================
        loans_df = load_data(sheet, "Loans")

        if not loans_df.empty:
            loans_df["Amount"] = pd.to_numeric(loans_df["Amount"], errors="coerce")
            loans_df["Amount_Paid"] = pd.to_numeric(loans_df.get("Amount_Paid", 0), errors="coerce")

            user_loans = loans_df[loans_df["Borrower"] == borrower["Name"]]

            total_loans = user_loans.shape[0]
            total_borrowed = user_loans["Amount"].sum()
            total_paid = user_loans["Amount_Paid"].sum()
        else:
            total_loans, total_borrowed, total_paid = 0, 0, 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Loans", total_loans)
        col2.metric("Borrowed", f"{total_borrowed:,.0f}")
        col3.metric("Paid", f"{total_paid:,.0f}")

        st.markdown("---")

        # ==============================
        # EDIT BORROWER
        # ==============================
        st.subheader("✏️ Edit Borrower")

        col1, col2 = st.columns(2)

        new_name = col1.text_input("Name", borrower["Name"])
        new_phone = col2.text_input("Phone", borrower["Phone"])

        new_nid = col1.text_input("National ID", borrower["National_ID"])
        new_address = col2.text_input("Address", borrower["Address"])

        new_status = st.selectbox(
            "Status",
            ["Active", "Inactive"],
            index=0 if borrower["Status"] == "Active" else 1
        )

        if st.button("Update"):
            df.loc[df["Borrower_ID"] == selected_id, [
                "Name", "Phone", "National_ID", "Address", "Status"
            ]] = [
                new_name, new_phone, new_nid, new_address, new_status
            ]

            save_data(sheet, "Borrowers", df)
            st.success("Updated successfully ✅")

        # ==============================
        # SAFE DELETE (DEACTIVATE)
        # ==============================
        st.subheader("⚠️ Deactivate Borrower")

        if borrower["Status"] == "Active":
            if st.button("Deactivate"):
                df.loc[df["Borrower_ID"] == selected_id, "Status"] = "Inactive"
                save_data(sheet, "Borrowers", df)
                st.warning("Borrower deactivated ⚠️")
        else:
            st.info("Borrower already inactive")

elif st.session_state.page == "Loans":
    # EVERYTHING BELOW IS PUSHED IN BY 4 SPACES
    st.subheader("➕ Issue Loan")

    # 1. First, fetch the data
    sheet = open_sheet("Zoe_Data")
    borrowers_df = load_data(sheet, "Borrowers")

    # 2. PLACEMENT: Safety check
    if borrowers_df.empty:
        st.warning("⚠️ No borrowers found in the database. Please register a client first.")
        st.stop() 

    # 3. Filter for active borrowers
    # Make sure 'Status' in your Google Sheet matches this capitalization
    active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]

    if active_borrowers.empty:
        st.info("No 'Active' borrowers found. Check your 'Status' column in the sheet.")
        st.stop()

    # 4. Create the selection box
    selected_borrower = st.selectbox(
        "Select Borrower", 
        active_borrowers["Name"].unique()
    )
    
    # --- You can continue adding loan amount/interest inputs here ---

    amount = st.number_input("Loan Amount", min_value=0.0)
    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0)
    duration = st.number_input("Duration (Days)", min_value=1)

    # ==============================
    # LIVE LOAN PREVIEW
    # ==============================
    if amount > 0 and interest_rate > 0:
        interest = (interest_rate / 100) * amount
        total = amount + interest
        end_date = datetime.now() + timedelta(days=int(duration))

        col1, col2, col3 = st.columns(3)
        col1.metric("Interest", f"{interest:,.0f}")
        col2.metric("Total Repayable", f"{total:,.0f}")
        col3.metric("End Date", end_date.strftime("%Y-%m-%d"))

    # ==============================
    # RISK CHECK
    # ==============================
    # 1. Load the Loans data (add this above line 652)
loans_df = load_data(sheet, "Loans")

# 2. Safety check: if Loans sheet is empty, create an empty dataframe with columns
if loans_df.empty:
    loans_df = pd.DataFrame(columns=["Loan_ID", "Borrower", "Status", "Amount"])

# 3. Now line 652 will work perfectly!
risky_loans = loans_df[
    (loans_df["Borrower"] == selected_borrower) & 
    (loans_df["Status"] == "Active")
]
# --- ISSUE BUTTON SECTION ---
    # These should be indented inside your 'elif page == "Borrowers":' block
    amount = st.number_input("Loan Amount", min_value=0.0)
    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0)
    duration = st.number_input("Duration (Days)", min_value=1, value=30) # Ensure duration exists

    if st.button("Issue Loan"):
        # LEVEL 1: Inside the button click
        if amount <= 0 or interest_rate <= 0:
            st.error("Enter valid loan details")

        elif selected_borrower not in active_borrowers["Name"].values:
            st.error("Borrower is inactive")

        else:
            # LEVEL 2: Inside the 'else' (The actual processing)
            interest = (interest_rate / 100) * amount
            total = amount + interest

            start_date = datetime.now()
            end_date = start_date + timedelta(days=int(duration))

            # Generate ID Safely
            new_id = int(loans_df["Loan_ID"].max() + 1) if not loans_df.empty else 1

            new_loan_row = pd.DataFrame([{
                "Loan_ID": new_id,
                "Borrower": selected_borrower,
                "Amount": amount,
                "Interest": interest,
                "Total_Repayable": total,
                "Amount_Paid": 0,
                "Start_Date": start_date.strftime("%Y-%m-%d"),
                "End_Date": end_date.strftime("%Y-%m-%d"),
                "Status": "Active"
            }])

            try:
                # Concatenate and push to Google Sheets
                updated_loans = pd.concat([loans_df, new_loan_row], ignore_index=True)
                save_data(sheet, "Loans", updated_loans)
                
                st.success(f"Loan issued ✅ Total Due: {total:,.0f} UGX")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Failed to save to Google Sheets: {e}")

    st.markdown("---")
    # ==============================
    # AUTO STATUS UPDATE
    # ==============================
    loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
    today = pd.Timestamp.today()

    loans_df.loc[
        (loans_df["End_Date"] < today) &
        (loans_df["Amount_Paid"] < loans_df["Total_Repayable"]),
        "Status"
    ] = "Overdue"

    # ==============================
    # LOAN TABLE WITH INSIGHTS
    # ==============================
    st.subheader("📋 Loan Portfolio")

    loans_df["Outstanding"] = loans_df["Total_Repayable"] - loans_df["Amount_Paid"]
    loans_df["Progress (%)"] = (
        loans_df["Amount_Paid"] / loans_df["Total_Repayable"] * 100
    ).fillna(0)

    st.dataframe(loans_df, use_container_width=True)

    # ==============================
    # LOAN PROGRESS VISUAL
    # ==============================
    st.subheader("📊 Loan Progress")

    selected_loan = st.selectbox("Select Loan ID", loans_df["Loan_ID"])

    loan = loans_df[loans_df["Loan_ID"] == selected_loan].iloc[0]

    progress = loan["Progress (%)"]

    st.progress(min(int(progress), 100))

    col1, col2, col3 = st.columns(3)
    col1.metric("Paid", f"{loan['Amount_Paid']:,.0f}")
    col2.metric("Outstanding", f"{loan['Outstanding']:,.0f}")
    col3.metric("Status", loan["Status"])


# --- PAYMENTS PAGE ---
elif st.session_state.page == "Payments":
    st.title("💵 Payments Management")
    loans_df = load_data(sheet, "Loans")
    payments_df = load_data(sheet, "Payments")

    loan_id = st.selectbox("Select Loan", loans_df[loans_df["Status"] != "Closed"]["Loan_ID"])
    amount = st.number_input("Payment Amount", min_value=0.0)
    if st.button("Record Payment"):
        # Process payment logic...
        st.success("Payment Recorded!")

# --- REPORTS PAGE (ADMIN ONLY) ---
elif st.session_state.page == "Reports":
    st.title("📊 Advanced Analytics")
    loans = load_data(sheet, "Loans")
    payments = load_data(sheet, "Payments")
    expenses = load_data(sheet, "Expenses")
    
    total_issued = pd.to_numeric(loans["Amount"]).sum()
    total_collected = pd.to_numeric(payments["Amount"]).sum()
    st.metric("Total Profitability", f"{(total_collected - pd.to_numeric(expenses['Amount']).sum()):,.0f}")

# --- SETTINGS PAGE (ADMIN ONLY) ---
elif st.session_state.page == "Settings":
    if st.session_state.role != "Admin":
        st.error("Access denied 🔒")
    else:
        st.title("⚙️ Settings")
        logo_file = st.file_uploader("Upload Company Logo")
        if logo_file and st.button("Save Logo"):
            save_logo(sheet, logo_file)
            st.success("Logo Saved!")

# Placeholder for remaining routes
else:
    st.title(f"{st.session_state.page} Page")
    st.info("Module logic under construction.")
