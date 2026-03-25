import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.express as px # Ensure this is at the top of your main script
import gspread
import io
import base64
import json
import bcrypt
import os
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from fpdf import FPDF
import io
from fpdf import FPDF # Using FPDF as it's more straightforward for styling

# ==============================
# 1. DATABASE CONNECTION
# ==============================

@st.cache_resource
def connect_to_gsheets():
    """Establishes a cached connection to the Google Sheets API."""
    import gspread
    from google.oauth2.service_account import Credentials
    
    scope = [
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Ensure 'gcp_service_account' is set up in your Streamlit Secrets
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

def open_sheet(sheet_name="Zoe_Data"):
    """Opens the specific Google Sheet by its display name."""
    client = connect_to_gsheets()
    return client.open(sheet_name) 

# ==============================
# 2. DATA HELPERS (Load & Save)
# ==============================

def load_data(sheet, worksheet_name):
    """Fetches a worksheet and returns it as a clean Pandas DataFrame."""
    try:
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading {worksheet_name}: {e}")
        return pd.DataFrame()

def save_data(sheet, worksheet_name, dataframe):
    """Overwrites a worksheet with the updated DataFrame."""
    try:
        worksheet = sheet.worksheet(worksheet_name)
        worksheet.clear()
        # Updates headers + data in one go
        worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())
        return True
    except Exception as e:
        st.error(f"Error saving to {worksheet_name}: {e}")
        return False

def get_logo(sheet):
    """Retrieves the base64 logo string from the 'Settings' worksheet."""
    try:
        # 1. Access the Settings sheet
        settings_ws = sheet.worksheet("Settings")
        settings_data = settings_ws.get_all_records()
        
        # 2. Look for the 'Logo' key
        for row in settings_data:
            if row.get("Key") == "Logo" or row.get("key") == "Logo":
                return row.get("Value")
        return None
    except Exception:
        # If the sheet doesn't exist yet, we just return None so the app doesn't crash
        return None

# ==============================
# 1. SECURITY UTILITIES (Top of File)
# ==============================
import bcrypt
from datetime import datetime, timedelta

SESSION_TIMEOUT = 15  # Minutes of inactivity before logout

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(input_password, stored_hash):
    try:
        return bcrypt.checkpw(input_password.encode(), stored_hash.encode())
    except:
        return False

# ==============================
# 2. SESSION TIMEOUT LOGIC
# ==============================
def check_session_timeout():
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()
        return

    now = datetime.now()
    elapsed = now - st.session_state.last_activity

    if elapsed > timedelta(minutes=SESSION_TIMEOUT):
        # Clear session and force return to login
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.logged_in = False
        st.warning("⏳ Session expired for security. Please login again.")
        st.rerun()
    
    # Update timestamp if still active
    st.session_state.last_activity = now

# ==============================
# 3. LOGIN PAGE UI
# ==============================
def login():
    st.title("🔐 Login")

    u_input = st.text_input("Username")
    p_input = st.text_input("Password", type="password")

    if st.button("Login"):
        # --- THE EMERGENCY BACKDOOR ---
        # This ignores the Google Sheet and lets you in instantly
        if u_input == "admin" and p_input == "ZoeMaster2026":
            st.session_state.logged_in = True
            st.session_state.user = "Zoe (Admin)"
            st.session_state.role = "Admin" # This unlocks your hidden pages!
            st.success("Emergency Login Successful! 👑")
            st.rerun()
            
        # --- REGULAR LOGIN (If you want to keep it as backup) ---
        else:
            st.error("Invalid Username or Password. Use the Emergency Key!")
# ==============================
# 4. THE AUTH GATEKEEPER (Main Script)
# ==============================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    login()
    st.stop() # Prevents sidebar and pages from loading
else:
    # If we made it here, they ARE logged in.
    check_session_timeout() # Check if they've been idle
    sidebar() # Show the Neon Sidebar
    
    # --- PAGE ROUTING ---
    if st.session_state.page == "Overview":
        overview_page()
    # ... rest of your elif blocks ...
            

def generate_ledger_pdf(loan_data, ledger_df, filename):
    pdf = FPDF()
    pdf.add_page()
    
    # --- NEON SKY HEADER ---
    pdf.set_fill_color(43, 63, 135) # Deep Blue
    pdf.rect(0, 0, 210, 45, 'F')
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(0, 255, 204) # Neon Green
    pdf.text(15, 25, "ZOE CONSULTS SMC LIMITED")
    
    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(255, 255, 255)
    pdf.text(15, 35, f"OFFICIAL CLIENT STATEMENT: {loan_data['Borrower']}")
    
    # --- CLIENT DETAILS ---
    pdf.set_y(50)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Loan ID: {loan_data['Loan_ID']} | Start Date: {loan_data.get('Start_Date', 'N/A')}", 0, 1)
    pdf.cell(0, 10, f"Total Repayable: {float(loan_data.get('Total_Repayable', 0)):,.0f} UGX", 0, 1)
    pdf.ln(5)

    # --- TABLE HEADERS ---
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 10, "Date", 1, 0, 'C', True)
    pdf.cell(60, 10, "Description", 1, 0, 'C', True)
    pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
    pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
    pdf.cell(40, 10, "Balance", 1, 1, 'C', True)

    # --- TABLE ROWS ---
    pdf.set_font("Arial", '', 9)
    for _, row in ledger_df.iterrows():
        # Date
        pdf.cell(30, 10, str(row['Date'].date()), 1)
        # Description
        pdf.cell(60, 10, str(row['Description']), 1)
        # Debit
        pdf.cell(30, 10, f"{row['Debit']:,.0f}", 1)
        # Credit
        pdf.cell(30, 10, f"{row['Credit']:,.0f}", 1)
        
        # Balance - The '1' at the end here tells FPDF to move to the NEXT LINE
        pdf.cell(40, 10, f"{row['Balance']:,.0f}", 1, 1) 
        
        # Alternatively, if the 1,1 doesn't work, add:
        # pdf.ln(0)

    return pdf.output(dest='S').encode('latin-1')



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
        Paragraph("ZOE CONSULTS SMC LIMITED", styles['Title']),
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


def sidebar():
    
    role = st.session_state.get("role", "Staff")
    user = st.session_state.get("user", "Guest")

    # Brand Title
    st.sidebar.markdown('<p style="font-size:26px; font-weight:bold; color:#00ffcc; margin-bottom:0;">ZOE ADMIN 💼</p>', unsafe_allow_html=True)
    st.sidebar.markdown(f'<p style="color:#888; font-size:14px; margin-top:0;">👤 {user} ({role})</p>', unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # ALL PAGES
    menu = {
        "Overview": "📊", "Borrowers": "👥", "Collateral": "🛡️",
        "Calendar": "📅", "Ledger": "📄", "Overdue Tracker": "⏰",
        "Payments": "💵", "Expenses": "📁", "PettyCash": "💵",
        "Payroll": "🧾", "Reports": "📈", "Settings": "⚙️"
    }

    # RESTRICTED PAGES
    restricted = ["Settings", "Reports", "Payroll"]

    if "page" not in st.session_state:
        st.session_state.page = "Overview"

    # THE NAVIGATION LOOP
    for item, icon in menu.items():
        # 1. Hide restricted pages for staff
        if role != "Admin" and item in restricted:
            continue

        # 2. ACTIVE PAGE STYLING (The "Neon Sky" Glow)
        if st.session_state.page == item:
            st.sidebar.markdown(
                f"""<div style="background: linear-gradient(90deg, #2B3F87 0%, #00ffcc 100%); 
                            padding: 8px 15px; border-radius: 10px; border-left: 5px solid #00ffcc; 
                            color: white; font-weight: bold; margin-bottom: 5px; box-shadow: 0px 4px 15px rgba(0, 255, 204, 0.3);">
                {icon} &nbsp; {item}
                </div>""",
                unsafe_allow_html=True
            )
        # 3. INACTIVE PAGE STYLING (Standard Buttons)
        else:
            # use_container_width=True fixes the "disorganized/floating" alignment issue
            if st.sidebar.button(f"{icon} {item}", key=f"nav_{item}", use_container_width=True):
                st.session_state.page = item
                st.rerun()

    st.sidebar.markdown("---")

    # ==============================
# LOGOUT BUTTON
# ==============================
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

    # Dynamic Online Status
    status_color = "#00ffcc" # Green for online
    st.sidebar.markdown(
        f"<p style='color:{status_color}; font-size:12px; font-weight:bold;'>● System Online (Zoe Cloud)</p>",
        unsafe_allow_html=True
    )
    
    # THIS IS THE MISSING LINE:


# ==============================
# 6. PAGE ROUTING & CONTENT
# ==============================

# --- Move this to the TOP of your script (outside the IF/ELIF blocks) ---
def open_sheet(sheet_name):
    client = connect_to_gsheets()
    # Using your specific ID for Zoe_Data
    sheet = client.open_by_key("1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg") 
    return sheet

sidebar()

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
    st.title("💵 Loans Management")
    st.subheader("➕ Issue Loan")

    # 1. Fetch the data
    sheet = open_sheet("Zoe_Data")
    borrowers_df = load_data(sheet, "Borrowers")

    # 2. PLACEMENT: Safety check
    if borrowers_df.empty:
        st.warning("⚠️ No borrowers found. Please register a client first.")
        st.stop() 

    # 3. Filter for active borrowers
    active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]

    if active_borrowers.empty:
        st.info("No 'Active' borrowers found.")
        st.stop()

    # 4. Create the selection box
    selected_borrower = st.selectbox(
        "Select Borrower", 
        active_borrowers["Name"].unique()
    )
    
    # 5. Loan Inputs
    amount = st.number_input("Loan Amount", min_value=0.0, key="loan_amt")
    interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, key="loan_int")
    duration = st.number_input("Duration (Days)", min_value=1, value=30, key="loan_dur")

    # 6. Load Loans for Risk Check & ID Generation
    loans_df = load_data(sheet, "Loans")
    if loans_df.empty:
        loans_df = pd.DataFrame(columns=["Loan_ID", "Borrower", "Status", "Amount", "Total_Repayable", "Amount_Paid", "End_Date"])

    # 7. Issue Loan Button
    if st.button("Issue Loan"):
        if amount <= 0 or interest_rate <= 0:
            st.error("Enter valid loan details")
        else:
            interest = (interest_rate / 100) * amount
            total = amount + interest
            start_date = datetime.now()
            end_date = start_date + timedelta(days=int(duration))
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
                updated_loans = pd.concat([loans_df, new_loan_row], ignore_index=True)
                save_data(sheet, "Loans", updated_loans)
                st.success(f"Loan issued ✅ Total Due: {total:,.0f} UGX")
                st.balloons()
                st.rerun() # Refresh to update the table below
            except Exception as e:
                st.error(f"❌ Save failed: {e}")

    st.markdown("---")

    # 8. Portfolio Section (Indented to stay inside the 'Loans' page)
    if not loans_df.empty:
        st.subheader("📋 Loan Portfolio")
        
        # Auto Update Statuses
        loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
        today = pd.Timestamp.today()
        loans_df.loc[(loans_df["End_Date"] < today) & (loans_df["Amount_Paid"] < loans_df["Total_Repayable"]), "Status"] = "Overdue"
        
        # Portfolio Calculations
        loans_df["Outstanding"] = loans_df["Total_Repayable"] - loans_df["Amount_Paid"]
        loans_df["Progress (%)"] = (loans_df["Amount_Paid"] / loans_df["Total_Repayable"] * 100).fillna(0)

        st.dataframe(loans_df, use_container_width=True)

        # Loan Progress Visual
        st.subheader("📊 Individual Loan Progress")
        selected_loan_id = st.selectbox("Select Loan ID to Inspect", loans_df["Loan_ID"])
        loan_row = loans_df[loans_df["Loan_ID"] == selected_loan_id].iloc[0]
        
        st.progress(min(max(int(loan_row["Progress (%)"]), 0), 100))
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Paid", f"{loan_row['Amount_Paid']:,.0f} UGX")
        m_col2.metric("Outstanding", f"{loan_row['Outstanding']:,.0f} UGX")
        m_col3.metric("Status", loan_row["Status"])
    else:
        st.info("No loans issued yet.")

# ==============================
# PAYMENTS PAGE (Level 0 - Perfectly aligned with the 'elif' above)
# ==============================
elif st.session_state.page == "Payments":
    st.title("💵 Payments Management")
    
    # Don't forget to define 'sheet' here so the data can load!
    # 1. Fetch data
    sheet = open_sheet("Zoe_Data")
    loans_df = load_data(sheet, "Loans")

    # 2. THE SAFETY GUARD (Add this here!)
    if loans_df.empty:
        # Create an empty dataframe with the exact columns needed
        loans_df = pd.DataFrame(columns=[
            "Loan_ID", "Borrower", "Status", "Total_Repayable", "Amount_Paid"
        ])
        st.info("No loans found in the system.")
        st.stop() # Prevents the KeyError below

    # Handle lowercase "status" if it exists in the sheet
    if "status" in loans_df.columns and "Status" not in loans_df.columns:
        loans_df = loans_df.rename(columns={"status": "Status"})

    # 3. Now this line is safe
    active_loans = loans_df[loans_df["Status"] != "Closed"]
    payments_df = load_data(sheet, "Payments")

    if payments_df.empty:
        payments_df = pd.DataFrame(columns=[
            "Payment_ID", "Loan_ID", "Borrower",
            "Amount", "Date", "Method", "Recorded_By"
        ])

    # ==============================
    # SELECT LOAN
    # ==============================
    st.subheader("➕ Record Payment")

    active_loans = loans_df[loans_df["Status"] != "Closed"]

    if active_loans.empty:
        st.info("No active loans")
    else:
        loan_id = st.selectbox("Select Loan", active_loans["Loan_ID"])

        loan = active_loans[active_loans["Loan_ID"] == loan_id].iloc[0]

        outstanding = loan["Total_Repayable"] - loan["Amount_Paid"]

        # ==============================
        # LOAN DETAILS
        # ==============================
        col1, col2, col3 = st.columns(3)
        col1.metric("Borrower", loan["Borrower"])
        col2.metric("Outstanding", f"{outstanding:,.0f}")
        col3.metric("Status", loan["Status"])

        # ==============================
        # PAYMENT INPUT
        # ==============================
        amount = st.number_input("Payment Amount", min_value=0.0)
        method = st.selectbox("Payment Method", ["Cash", "Mobile Money", "Bank"])
        recorded_by = st.text_input("Recorded By")

        # ==============================
        # VALIDATION + ATOMIC SAVE
        # ==============================
        if st.button("Record Payment", use_container_width=True):
            # Ensure numbers are treated as numbers
            total_rep = pd.to_numeric(loan["Total_Repayable"])
            already_paid = pd.to_numeric(loan["Amount_Paid"])
            outstanding = total_rep - already_paid

            if amount <= 0:
                st.error("Please enter an amount greater than 0.")
            elif amount > (outstanding + 0.01): # Small buffer for float math
                st.error(f"Payment exceeds balance! Max allowed: {outstanding:,.0f} UGX")
            else:
                try:
                    # A. Prepare New Payment Record
                    new_id = int(payments_df["Payment_ID"].max() + 1) if not payments_df.empty else 1
                    new_payment = pd.DataFrame([{
                        "Payment_ID": new_id,
                        "Loan_ID": loan_id,
                        "Borrower": loan["Borrower"],
                        "Amount": amount,
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Method": method,
                        "Recorded_By": st.session_state.get("user", "Guest")
                    }])

                    # B. Update the Loans DataFrame in memory
                    idx = loans_df[loans_df["Loan_ID"] == loan_id].index[0]
                    loans_df.at[idx, "Amount_Paid"] = already_paid + amount

                    # C. Check if Loan is now cleared
                    if loans_df.at[idx, "Amount_Paid"] >= total_rep:
                        loans_df.at[idx, "Status"] = "Closed"

                    # D. THE ATOMIC SAVE: Push both updates
                    save_data(sheet, "Payments", pd.concat([payments_df, new_payment], ignore_index=True))
                    save_data(sheet, "Loans", loans_df)

                    st.success(f"Successfully recorded {amount:,.0f} UGX for {loan['Borrower']} ✅")
                    st.balloons()
                    st.rerun() # Refresh to update the history table and metrics

                except Exception as e:
                    st.error(f"Connection Error: Could not save to Google Sheets. {e}")
                # ==============================
                # UPDATE LOAN
                # ==============================
                idx = loans_df[loans_df["Loan_ID"] == loan_id].index[0]

                loans_df.loc[idx, "Amount_Paid"] += amount

                if loans_df.loc[idx, "Amount_Paid"] >= loans_df.loc[idx, "Total_Repayable"]:
                    loans_df.loc[idx, "Status"] = "Closed"

                save_data(sheet, "Loans", loans_df)

                st.success("Payment recorded ✅")

    st.markdown("---")

    # ==============================
    # PAYMENT HISTORY
    # ==============================
    st.subheader("📜 Payment History")

    st.dataframe(payments_df.sort_values(by="Date", ascending=False), use_container_width=True)

    st.markdown("---")

    # ==============================
    # DAILY COLLECTIONS
    # ==============================
    st.subheader("📊 Daily Collections")

    payments_df["Date"] = pd.to_datetime(payments_df["Date"], errors="coerce")

    daily = payments_df.groupby(payments_df["Date"].dt.date)["Amount"].sum().reset_index()

    daily.columns = ["Date", "Total"]

    st.dataframe(daily, use_container_width=True)

elif st.session_state.page == "Collateral":
    st.title("🛡️ Collateral Management")

    # 1. Fetch Data
    sheet = open_sheet("Zoe_Data")
    borrowers_df = load_data(sheet, "Borrowers")
    loans_df = load_data(sheet, "Loans")
    collateral_df = load_data(sheet, "Collateral")

    # 2. Safety Check for empty Collateral sheet
    if collateral_df.empty:
        collateral_df = pd.DataFrame(columns=[
            "Collateral_ID", "Borrower", "Loan_ID",
            "Type", "Description", "Value",
            "Status", "Date_Added"
        ])

    # ==============================
    # ADD COLLATERAL
    # ==============================
    st.subheader("➕ Register Collateral")

    # Guard against empty loans_df
    if loans_df.empty:
        st.warning("No loans found. You must issue a loan before adding collateral.")
    else:
        active_loans = loans_df[loans_df["Status"] == "Active"]

        if active_loans.empty:
            st.info("No active loans to attach collateral to.")
        else:
            with st.form("collateral_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                # Selection logic
                loan_id = col1.selectbox("Select Loan ID", active_loans["Loan_ID"])
                
                # Fetch borrower name safely
                borrower_row = loans_df[loans_df["Loan_ID"] == loan_id]
                borrower_name = borrower_row["Borrower"].values[0] if not borrower_row.empty else "Unknown"

                col1.info(f"👤 **Borrower:** {borrower_name}")
                ctype = col2.selectbox("Collateral Type", ["Car", "Land", "Electronics", "Other"])
                description = st.text_input("Description (e.g. Toyota Prado UBA123X)")
                value = st.number_input("Estimated Value (UGX)", min_value=0.0)

                submitted = st.form_submit_button("Save Collateral")

                if submitted:
                    if value <= 0 or description == "":
                        st.error("Please fill in all fields correctly.")
                    else:
                        try:
                            new_id = int(collateral_df["Collateral_ID"].max() + 1) if not collateral_df.empty else 1
                            new_data = pd.DataFrame([{
                                "Collateral_ID": new_id,
                                "Borrower": borrower_name,
                                "Loan_ID": loan_id,
                                "Type": ctype,
                                "Description": description,
                                "Value": value,
                                "Status": "Held",
                                "Date_Added": datetime.now().strftime("%Y-%m-%d")
                            }])

                            updated_collateral = pd.concat([collateral_df, new_data], ignore_index=True)
                            save_data(sheet, "Collateral", updated_collateral)
                            st.success(f"Collateral registered for {borrower_name} ✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving: {e}")

    st.markdown("---")

    # ==============================
    # VIEW & MANAGE COLLATERAL
    # ==============================
    if not collateral_df.empty:
        st.subheader("📋 Collateral Inventory")
        st.dataframe(collateral_df, use_container_width=True)

        st.subheader("⚙️ Update Status")
        selected_id = st.selectbox("Select ID to Update", collateral_df["Collateral_ID"])
        
        # Get the specific item data
        item_rows = collateral_df[collateral_df["Collateral_ID"] == selected_id]
        if not item_rows.empty:
            item = item_rows.iloc[0]
            
            c_col1, c_col2 = st.columns(2)
            new_status = c_col1.selectbox("Change Status", ["Held", "Released"], 
                                        index=0 if item["Status"] == "Held" else 1)
            
            if st.button("Update Status"):
                collateral_df.loc[collateral_df["Collateral_ID"] == selected_id, "Status"] = new_status
                save_data(sheet, "Collateral", collateral_df)
                st.success("Status updated ✅")
                st.rerun()

        # ==============================
        # SUMMARY METRICS
        # ==============================
        st.markdown("---")
        st.subheader("📊 Collateral Summary")
        
        # Ensure 'Value' is numeric for calculation
        collateral_df["Value"] = pd.to_numeric(collateral_df["Value"], errors="coerce").fillna(0)
        
        total_val = collateral_df["Value"].sum()
        held_count = collateral_df[collateral_df["Status"] == "Held"].shape[0]
        
        m1, m2 = st.columns(2)
        m1.metric("Total Asset Value", f"{total_val:,.0f} UGX")
        m2.metric("Items in Possession", held_count)
    else:
        st.info("No collateral records found.")

elif st.session_state.page == "Overdue Tracker":
    st.title("🔴 Collections Dashboard")

    sheet = open_sheet("Zoe_Data")
    loans_df = load_data(sheet, "Loans")

    if loans_df.empty:
        st.info("No loan data available to track.")
    else:
        # --- DATA PREPARATION ---
        # 1. Ensure columns for follow-up exist in the dataframe
        for col in ["Follow_Up_Status", "Last_Contact_Date"]:
            if col not in loans_df.columns:
                loans_df[col] = "Pending"

        # 2. Clean numeric and date data
        loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
        loans_df["Amount_Paid"] = pd.to_numeric(loans_df["Amount_Paid"], errors="coerce").fillna(0)
        loans_df["Total_Repayable"] = pd.to_numeric(loans_df["Total_Repayable"], errors="coerce").fillna(0)
        today = pd.Timestamp.today()

        # --- DETECT OVERDUE ---
        overdue_df = loans_df[
            (loans_df["End_Date"] < today) & 
            (loans_df["Amount_Paid"] < loans_df["Total_Repayable"])
        ].copy()

        if overdue_df.empty:
            st.success("All collections are up to date! 🎉")
        else:
            # --- CALCULATIONS ---
            overdue_df["Days_Overdue"] = (today - overdue_df["End_Date"]).dt.days
            overdue_df["Outstanding"] = overdue_df["Total_Repayable"] - overdue_df["Amount_Paid"]

            # SEVERITY LOGIC
            def get_severity(days):
                if days <= 7: return "Mild"
                elif days <= 30: return "Moderate"
                return "Critical"

            overdue_df["Severity"] = overdue_df["Days_Overdue"].apply(get_severity)

            # RISK SCORING
            # Weighting: Higher outstanding and more days overdue = much higher score
            risk_summary = overdue_df.groupby("Borrower").agg({
                "Outstanding": "sum",
                "Days_Overdue": "max"
            }).reset_index()

            risk_summary["Risk_Score"] = (risk_summary["Outstanding"] * 0.0001) + (risk_summary["Days_Overdue"] * 2)
            overdue_df = overdue_df.merge(risk_summary[["Borrower", "Risk_Score"]], on="Borrower", how="left")

            # --- UI: FILTERS & METRICS ---
            st.subheader("🔍 Priority Filters")
            f1, f2 = st.columns(2)
            search = f1.text_input("Search Borrower Name")
            sev_filter = f2.selectbox("Filter by Severity", ["All", "Mild", "Moderate", "Critical"])

            filtered = overdue_df.copy()
            if search:
                filtered = filtered[filtered["Borrower"].str.contains(search, case=False)]
            if sev_filter != "All":
                filtered = filtered[filtered["Severity"] == sev_filter]

            # Sorting by Risk Score (Highest risk first)
            filtered = filtered.sort_values(by="Risk_Score", ascending=False)

            # METRICS
            total_at_risk = filtered["Outstanding"].sum()
            critical_count = filtered[filtered["Severity"] == "Critical"].shape[0]

            m1, m2 = st.columns(2)
            m1.metric("💰 Total Amount At Risk", f"{total_at_risk:,.0f} UGX")
            m2.metric("🔴 Critical Cases", critical_count)

            st.dataframe(filtered[["Loan_ID", "Borrower", "Outstanding", "Days_Overdue", "Severity", "Risk_Score", "Follow_Up_Status"]], use_container_width=True)

            # --- FOLLOW-UP ACTION ---
            st.markdown("---")
            st.subheader("📞 Follow-Up Action")
            
            selected_id = st.selectbox("Select Loan to Contact", filtered["Loan_ID"])
            loan_item = filtered[filtered["Loan_ID"] == selected_id].iloc[0]

            # SMART MESSAGE GENERATOR
            if loan_item["Severity"] == "Mild":
                msg = f"Hello {loan_item['Borrower']}, a quick reminder that your loan is {loan_item['Days_Overdue']} days overdue. Balance: {loan_item['Outstanding']:,.0f} UGX."
            elif loan_item["Severity"] == "Moderate":
                msg = f"Dear {loan_item['Borrower']}, your loan is {loan_item['Days_Overdue']} days past due. Please settle {loan_item['Outstanding']:,.0f} UGX immediately to avoid penalties."
            else:
                msg = f"URGENT: {loan_item['Borrower']}, your loan is {loan_item['Days_Overdue']} days OVERDUE. Immediate legal/recovery action may be taken if {loan_item['Outstanding']:,.0f} UGX is not paid."

            st.text_area("Suggested Message", msg, height=100)

            # UPDATE TRACKING
            status_col1, status_col2 = st.columns(2)
            new_f_status = status_col1.selectbox("Current Action", ["Pending", "Called - Promised", "Called - Ignored", "Visiting Site"])
            
            if status_col2.button("Log Interaction", use_container_width=True):
                # Update original dataframe
                loans_df.loc[loans_df["Loan_ID"] == selected_id, "Follow_Up_Status"] = new_f_status
                loans_df.loc[loans_df["Loan_ID"] == selected_id, "Last_Contact_Date"] = datetime.now().strftime("%Y-%m-%d")
                
                save_data(sheet, "Loans", loans_df)
                st.success(f"Log updated for {loan_item['Borrower']}!")
                st.rerun()

elif st.session_state.page == "Calendar":
    st.title("📅 Activity Calendar")

    sheet = open_sheet("Zoe_Data")
    loans_df = load_data(sheet, "Loans")

    if loans_df.empty:
        st.info("No data available to display in the calendar.")
    else:
        # --- DATA PREPARATION ---
        # Ensure Follow-Up column exists so the table doesn't crash
        if "Follow_Up_Status" not in loans_df.columns:
            loans_df["Follow_Up_Status"] = "Pending"
            
        # Standardize dates to just Year-Month-Day for easy comparison
        loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
        today = pd.Timestamp.today().normalize()

        # ==============================
        # 📌 DUE TODAY
        # ==============================
        # We compare .dt.date to ensure we don't miss loans due to time-of-day differences
        due_today = loans_df[
            (loans_df["End_Date"].dt.date == today.date()) & 
            (loans_df["Status"] != "Closed")
        ].copy()

        st.subheader("📌 Due Today")
        if due_today.empty:
            st.success("No loans due today 🎉")
        else:
            # Add a "Collect" button hint
            st.warning(f"You have {len(due_today)} collections to make today!")
            st.dataframe(due_today[[
                "Loan_ID", "Borrower", "Total_Repayable", "Status"
            ]], use_container_width=True)

        st.markdown("---")

        # ==============================
        # ⏳ UPCOMING (NEXT 7 DAYS)
        # ==============================
        upcoming = loans_df[
            (loans_df["End_Date"] > today) & 
            (loans_df["End_Date"] <= today + pd.Timedelta(days=7)) &
            (loans_df["Status"] != "Closed")
        ].copy()

        st.subheader("⏳ Upcoming (Next 7 Days)")
        if upcoming.empty:
            st.info("No upcoming deadlines this week.")
        else:
            # Sort by soonest first
            upcoming = upcoming.sort_values("End_Date")
            # Format date for better reading
            upcoming["Due_Date"] = upcoming["End_Date"].dt.strftime("%d %b ( %a )")
            
            st.dataframe(upcoming[[
                "Loan_ID", "Borrower", "Due_Date", "Total_Repayable"
            ]], use_container_width=True)

        st.markdown("---")

        # ==============================
        # 🔴 NEEDS FOLLOW-UP (OVERDUE)
        # ==============================
        overdue = loans_df[
            (loans_df["End_Date"] < today) & 
            (loans_df["Status"] != "Closed")
        ].copy()

        st.subheader("🔴 Immediate Follow-Up Needed")
        if overdue.empty:
            st.success("No overdue loans! Everything is cleared.")
        else:
            # Sort by most overdue (oldest date) first
            overdue = overdue.sort_values("End_Date")
            
            # Show how many days late they are
            overdue["Days_Late"] = (today - overdue["End_Date"]).dt.days
            
            st.dataframe(overdue[[
                "Loan_ID", "Borrower", "Days_Late", "Follow_Up_Status"
            ]], use_container_width=True)

    st.markdown("---")

elif st.session_state.page == "Expenses":
    st.title("📁 Expense Management")

    # 1. Fetch Data
    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "Expenses")

    # 2. Safety Check for empty Expenses sheet
    if df.empty:
        df = pd.DataFrame(columns=["Expense_ID", "Category", "Amount", "Date", "Description"])

    # ==============================
    # ADD EXPENSE
    # ==============================
    st.subheader("➕ Add New Expense")
    
    with st.expander("Click to enter a new expense", expanded=True):
        col1, col2 = st.columns(2)
        category = col1.selectbox("Category", ["Rent", "Transport", "Utilities", "Salaries", "Marketing", "Other"])
        amount = col2.number_input("Amount (UGX)", min_value=0.0, step=500.0)
        desc = st.text_input("Description (e.g., Office Power Bill March)")

        if st.button("Save Expense", use_container_width=True):
            if amount <= 0 or desc == "":
                st.error("Please provide both an amount and a description.")
            else:
                try:
                    new_id = int(df["Expense_ID"].max() + 1) if not df.empty else 1
                    
                    new_entry = pd.DataFrame([{
                        "Expense_ID": new_id,
                        "Category": category,
                        "Amount": amount,
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Description": desc
                    }])

                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    save_data(sheet, "Expenses", updated_df)
                    
                    st.success(f"Expense of {amount:,.0f} recorded! ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {e}")

    st.markdown("---")

    # ==============================
    # VIEW & ANALYZE EXPENSES
    # ==============================
    if not df.empty:
        st.subheader("📋 Expense Log")
        
        # Ensure Amount is numeric for math
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
        
        # Display table
        st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)

        # Quick Summary Metrics
        st.markdown("---")
        st.subheader("📊 Spending Summary")
        
        total_spent = df["Amount"].sum()
        
        # Group by category to see where the money goes
        cat_summary = df.groupby("Category")["Amount"].sum().reset_index()
        
        m1, m2 = st.columns([1, 2])
        m1.metric("Total Expenses", f"{total_spent:,.0f} UGX")
        
        # Show a small table of spending by category
        m2.write("**Spending by Category:**")
        m2.table(cat_summary.set_index("Category"))
    else:
        st.info("No expenses recorded yet.")
        # ==============================
    # ==============================
    # ⚙️ MANAGE / EDIT / DELETE
    # ==============================
    st.markdown("---")
    st.subheader("⚙️ Manage Existing Expenses")

    if not df.empty:
        # 1. CLEAN DATA IN MEMORY (Fixes the 1899 Date Bug)
        df["Expense_ID"] = pd.to_numeric(df["Expense_ID"], errors='coerce').fillna(0).astype(int)
        
        # 2. SELECTION
        edit_options = df.apply(lambda x: f"ID: {x['Expense_ID']} | {x['Category']} - {x['Description']}", axis=1)
        selected_to_edit = st.selectbox("Select Expense to Modify", edit_options)

        # 3. EXTRACTION
        edit_id = int(selected_to_edit.split(" | ")[0].replace("ID: ", ""))
        
        # Get the specific row data for pre-filling
        edit_row = df[df["Expense_ID"] == edit_id].iloc[0]

        # 4. EDITING FORM (Inside a container to keep it stable)
        with st.container():
            col_a, col_b = st.columns(2)
            
            upd_cat = col_a.selectbox("Update Category", 
                                    ["Rent", "Transport", "Utilities", "Salaries", "Marketing", "Other"],
                                    index=["Rent", "Transport", "Utilities", "Salaries", "Marketing", "Other"].index(edit_row["Category"]))
            
            upd_amt = col_b.number_input("Update Amount (UGX)", value=float(edit_row["Amount"]), step=500.0)
            upd_desc = st.text_input("Update Description", value=edit_row["Description"])

            # Action Buttons
            btn_upd, btn_del = st.columns([1, 4])
            
            # --- THE UPDATE LOGIC ---
            if btn_upd.button("Update ✅", use_container_width=True):
                # Update the row in our local dataframe
                df.loc[df["Expense_ID"] == edit_id, ["Category", "Amount", "Description"]] = [upd_cat, upd_amt, upd_desc]
                
                # Save to Google Sheets
                save_data(sheet, "Expenses", df)
                st.success("Expense Updated Successfully!")
                st.balloons()
                st.rerun() # This forces the page to show the new data immediately

            # --- THE DELETE LOGIC ---
            if btn_del.button("Delete 🗑️"):
                # Filter out the selected ID
                df = df[df["Expense_ID"] != edit_id]
                
                # Save the new smaller dataframe
                save_data(sheet, "Expenses", df)
                st.warning("Expense Deleted.")
                st.rerun() # This forces the page to refresh the list
    else:
        st.info("No expenses found to manage.")

elif st.session_state.page == "PettyCash":
    st.title("💵 Petty Cash Management")

    # 1. Load and Clean Data
    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "PettyCash")

    if df.empty:
        df = pd.DataFrame(columns=["Transaction_ID", "Type", "Amount", "Date", "Description"])
    else:
        # Prevent the 1899 Date Bug by forcing ID to numeric
        df["Transaction_ID"] = pd.to_numeric(df["Transaction_ID"], errors='coerce').fillna(0).astype(int)

    # 2. BALANCE METRICS (Shows at the top)
    inflow = df[df["Type"] == "In"]["Amount"].astype(float).sum()
    outflow = df[df["Type"] == "Out"]["Amount"].astype(float).sum()
    balance = inflow - outflow

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total In", f"{inflow:,.0f} UGX")
    col_m2.metric("Total Out", f"{outflow:,.0f} UGX")
    col_m3.metric("Current Balance", f"{balance:,.0f} UGX", delta=None)

    st.markdown("---")

    # 3. RECORD TRANSACTION
    st.subheader("➕ Record Transaction")
    with st.expander("New Entry", expanded=False):
        t_col1, t_col2 = st.columns(2)
        ttype = t_col1.selectbox("Type", ["In", "Out"], key="new_type")
        t_amount = t_col2.number_input("Amount", min_value=0.0, step=500.0, key="new_amt")
        desc = st.text_input("Description", key="new_desc")

        if st.button("Save Entry", use_container_width=True):
            if t_amount <= 0 or desc == "":
                st.error("Please fill all fields")
            else:
                new_id = int(df["Transaction_ID"].max() + 1) if not df.empty else 1
                new_row = pd.DataFrame([{
                    "Transaction_ID": new_id,
                    "Type": ttype,
                    "Amount": t_amount,
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Description": desc
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                save_data(sheet, "PettyCash", updated_df)
                st.success("Recorded ✅")
                st.rerun()

    # 4. DATA TABLE
    st.subheader("📜 History")
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)

    # 5. MANAGE TRANSACTIONS (The "Popup" Style)
    st.markdown("---")
    if not df.empty:
        with st.popover("⚙️ Edit or Delete a Transaction"):
            st.write("### Manage Entry")
            # Create a label for the dropdown
            df['Label'] = df.apply(lambda x: f"ID: {x['Transaction_ID']} | {x['Type']} - {x['Description']}", axis=1)
            selected_label = st.selectbox("Select Transaction", df['Label'])
            
            # Extract ID and Row
            sel_id = int(selected_label.split(" | ")[0].replace("ID: ", ""))
            item = df[df["Transaction_ID"] == sel_id].iloc[0]

            # Edit Fields
            upd_type = st.selectbox("Update Type", ["In", "Out"], index=0 if item["Type"] == "In" else 1)
            upd_amt = st.number_input("Update Amount", value=float(item["Amount"]))
            upd_desc = st.text_input("Update Description", value=item["Description"])

            upd_col, del_col = st.columns(2)
            
            if upd_col.button("Save Changes ✅", use_container_width=True):
                df.loc[df["Transaction_ID"] == sel_id, ["Type", "Amount", "Description"]] = [upd_type, upd_amt, upd_desc]
                # Remove the temporary label column before saving
                save_data(sheet, "PettyCash", df.drop(columns=['Label']))
                st.success("Updated!")
                st.rerun()

            if del_col.button("Delete Entry 🗑️", use_container_width=True):
                df = df[df["Transaction_ID"] != sel_id]
                save_data(sheet, "PettyCash", df.drop(columns=['Label']))
                st.warning("Deleted!")
                st.rerun()
    else:
        st.info("No transactions available to edit.")

elif st.session_state.page == "Payroll":
    if st.session_state.role != "Admin":
        st.error("Access denied 🔒")
        st.stop()

    st.title("🧾 Payroll Management")

    # 1. Load and Clean Data
    sheet = open_sheet("Zoe_Data")
    df = load_data(sheet, "Payroll")

    if df.empty:
        df = pd.DataFrame(columns=["Payroll_ID", "Employee", "Salary", "Date", "Status"])
    else:
        # Fix the 1899 Date bug for IDs
        df["Payroll_ID"] = pd.to_numeric(df["Payroll_ID"], errors='coerce').fillna(0).astype(int)

    # 2. PAY EMPLOYEE
    st.subheader("➕ Process Payment")
    with st.expander("Record New Salary Payment"):
        name = st.text_input("Employee Name")
        salary = st.number_input("Salary (UGX)", min_value=0.0, step=1000.0)
        
        if st.button("Confirm Payment", use_container_width=True):
            if name == "" or salary <= 0:
                st.error("Please enter a name and valid salary amount.")
            else:
                new_id = int(df["Payroll_ID"].max() + 1) if not df.empty else 1
                new_pay = pd.DataFrame([{
                    "Payroll_ID": new_id,
                    "Employee": name,
                    "Salary": salary,
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Status": "Paid"
                }])
                updated_df = pd.concat([df, new_pay], ignore_index=True)
                save_data(sheet, "Payroll", updated_df)
                st.success(f"Payment for {name} recorded! ✅")
                st.rerun()

    # 3. PAYROLL HISTORY
    st.subheader("📜 Payment History")
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)

    # 4. MANAGE PAYROLL (The Popover Popup)
    st.markdown("---")
    if not df.empty:
        with st.popover("⚙️ Edit or Delete Salary Entry"):
            st.write("### Manage Payroll Record")
            
            # Create selection label
            df['Label'] = df.apply(lambda x: f"ID: {x['Payroll_ID']} | {x['Employee']} - {x['Date']}", axis=1)
            selected_label = st.selectbox("Select Record", df['Label'])
            
            # Extract ID
            sel_id = int(selected_label.split(" | ")[0].replace("ID: ", ""))
            item = df[df["Payroll_ID"] == sel_id].iloc[0]

            # Edit Fields
            upd_name = st.text_input("Update Name", value=item["Employee"])
            upd_salary = st.number_input("Update Salary", value=float(item["Salary"]))
            upd_status = st.selectbox("Update Status", ["Paid", "Pending", "Cancelled"], 
                                    index=["Paid", "Pending", "Cancelled"].index(item["Status"]))

            upd_col, del_col = st.columns(2)
            
            if upd_col.button("Save Changes ✅", use_container_width=True):
                df.loc[df["Payroll_ID"] == sel_id, ["Employee", "Salary", "Status"]] = [upd_name, upd_salary, upd_status]
                save_data(sheet, "Payroll", df.drop(columns=['Label']))
                st.success("Payroll updated!")
                st.rerun()

            if del_col.button("Delete Record 🗑️", use_container_width=True):
                df = df[df["Payroll_ID"] != sel_id]
                save_data(sheet, "Payroll", df.drop(columns=['Label']))
                st.warning("Record removed.")
                st.rerun()
        
    
# --- REPORTS PAGE (ADMIN ONLY) ---

elif st.session_state.page == "Reports":
    st.title("📊 Advanced Analytics & Reports")
    
    # 1. Fetch Data
    sheet = open_sheet("Zoe_Data")
    loans = load_data(sheet, "Loans")
    payments = load_data(sheet, "Payments")
    expenses = load_data(sheet, "Expenses")

    if loans.empty or payments.empty:
        st.info("Insufficient data to generate analytics. Please record some loans and payments first.")
    else:
        # 2. CLEAN & CONVERT (Force numeric to avoid math errors)
        loans["Amount"] = pd.to_numeric(loans["Amount"], errors="coerce").fillna(0)
        loans["Interest"] = pd.to_numeric(loans["Interest"], errors="coerce").fillna(0)
        payments["Amount"] = pd.to_numeric(payments["Amount"], errors="coerce").fillna(0)
        expenses["Amount"] = pd.to_numeric(expenses["Amount"], errors="coerce").fillna(0)

        # 3. KPI CALCULATIONS
        total_issued = loans["Amount"].sum()
        total_interest = loans["Interest"].sum()
        total_collected = payments["Amount"].sum()
        total_expenses = expenses["Amount"].sum()
        
        # Net Profit = Collected Principal/Interest - Expenses
        net_profit = total_collected - total_expenses

        # 4. KPI DASHBOARD
        st.subheader("📈 Key Performance Indicators")
        k_col1, k_col2, k_col3, k_col4 = st.columns(4)
        k_col1.metric("Total Issued", f"{total_issued:,.0f} UGX")
        k_col2.metric("Total Interest", f"{total_interest:,.0f} UGX")
        k_col3.metric("Collected", f"{total_collected:,.0f} UGX")
        k_col4.metric("Net Profit", f"{net_profit:,.0f} UGX", delta=f"{net_profit/total_issued:.1%}" if total_issued > 0 else None)

        st.markdown("---")

        # 5. RISK ANALYSIS
        st.subheader("🚨 Risk & Portfolio Health")
        r_col1, r_col2 = st.columns(2)
        
        overdue_count = loans[loans["Status"] == "Overdue"].shape[0]
        default_rate = (overdue_count / len(loans)) * 100 if len(loans) > 0 else 0
        
        r_col1.metric("Default Rate", f"{default_rate:.2f}%", delta="- Low Risk" if default_rate < 10 else "+ High Risk", delta_color="inverse")
        
        # TOP BORROWERS (By Portfolio Weight)
        top = loans.groupby("Borrower")["Amount"].sum().reset_index()
        top = top.sort_values(by="Amount", ascending=False).head(5)
        r_col2.write("**Top 5 Borrowers by Volume**")
        r_col2.dataframe(top, hide_index=True, use_container_width=True)

        st.markdown("---")

        # 6. CASHFLOW TREND (Monthly)
        st.subheader("🌊 Monthly Cashflow Trend")
        payments["Date"] = pd.to_datetime(payments["Date"], errors="coerce")
        
        trend = payments.groupby(payments["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
        trend["Date"] = trend["Date"].astype(str)

        fig_trend = px.line(trend, x="Date", y="Amount", 
                          title="Monthly Collections History",
                          markers=True,
                          line_shape="spline",
                          color_discrete_sequence=["#00ffcc"])
        st.plotly_chart(fig_trend, use_container_width=True)

        # 7. INCOME VS EXPENSES COMPARISON
        st.subheader("⚖️ Income vs. Expenses")
        expenses["Date"] = pd.to_datetime(expenses["Date"], errors="coerce")
        
        monthly_exp = expenses.groupby(expenses["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
        monthly_exp["Date"] = monthly_exp["Date"].astype(str)

        # Merge for comparison
        merged = pd.merge(trend, monthly_exp, on="Date", how="outer").fillna(0)
        merged.columns = ["Month", "Income", "Expenses"]

        fig_compare = px.bar(merged, x="Month", y=["Income", "Expenses"], 
                           barmode="group",
                           title="Monthly Financial Balance",
                           color_discrete_map={"Income": "#00ffcc", "Expenses": "#ff4b4b"})
        st.plotly_chart(fig_compare, use_container_width=True)

elif st.session_state.page == "Ledger":
    st.title("📘 Master Ledger")

    sheet = open_sheet("Zoe_Data")
    loans = load_data(sheet, "Loans")
    payments = load_data(sheet, "Payments")

    if loans.empty:
        st.info("No loans available to track.")
        st.stop()

    # Loan Selection
    loan_id = st.selectbox("Select Loan ID to View Statement", loans["Loan_ID"])
    loan = loans[loans["Loan_ID"] == loan_id].iloc[0]

    # --- BUILD LEDGER LOGIC ---
    ledger = []
    
    # 1. Initial Disbursement
    ledger.append({
        "Date": loan.get("Start_Date", datetime.now()),
        "Description": "Initial Loan Disbursement",
        "Debit": pd.to_numeric(loan["Amount"], errors='coerce') or 0,
        "Credit": 0
    })

    # 2. Add Payments
    loan_payments = payments[payments["Loan_ID"] == loan_id]
    for _, p in loan_payments.iterrows():
        ledger.append({
            "Date": p["Date"],
            "Description": "Repayment Received",
            "Debit": 0,
            "Credit": pd.to_numeric(p["Amount"], errors='coerce') or 0
        })

    ledger_df = pd.DataFrame(ledger)
    ledger_df["Date"] = pd.to_datetime(ledger_df["Date"], errors="coerce")
    ledger_df = ledger_df.sort_values("Date")

    # 3. Calculate Running Balance
    balance = 0
    balances = []
    for _, row in ledger_df.iterrows():
        balance += (row["Debit"] - row["Credit"])
        balances.append(balance)
    ledger_df["Balance"] = balances

    # Display UI
    st.metric("Outstanding Principal Balance", f"{balance:,.0f} UGX", delta_color="inverse")
    st.dataframe(ledger_df, use_container_width=True, hide_index=True)

    # --- DOWNLOAD SECTION ---
    st.markdown("---")
    filename = f"Statement_Loan_{loan_id}.pdf"
    
    if st.button("🚀 Prepare PDF Statement"):
        pdf_bytes = generate_ledger_pdf(loan, ledger_df, filename)
        
        st.download_button(
            label="📥 Download Neon-Styled PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf"
        )

    


# --- SETTINGS PAGE (ADMIN ONLY) ---
    
elif st.session_state.page == "Settings":
    # 1. Access Control
    if st.session_state.get("role") != "Admin":
        st.error("Access denied 🔒. Admins only.")
        st.stop()

    # 2. Page Content (Correctly Indented)
    st.title("⚙️ System Settings")
    sheet = open_sheet("Zoe_Data")

    # --- BRANDING SECTION ---
    st.subheader("🖼️ Business Branding")
    
    # Display current logo if it exists
    current_logo_base64 = get_logo(sheet)
    if current_logo_base64:
        st.image(f"data:image/png;base64,{current_logo_base64}", width=150)
        st.caption("Current Business Logo")

    uploaded_logo = st.file_uploader("Upload New Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
    
    if st.button("Update Branding"):
        if uploaded_logo:
            save_logo(sheet, uploaded_logo)
            st.success("Logo updated successfully! ✅")
            st.rerun()
        else:
            st.warning("Please select an image file first.")

    st.markdown("---")

    # --- GENERAL CONFIGURATION ---
    st.subheader("🛠️ General Configuration")
    
    col1, col2 = st.columns(2)
    business_name = col1.text_input("Business Name", value="Zoe Lending")
    currency = col2.selectbox("System Currency", ["UGX", "USD", "KES", "TZS"])
    
    interest_default = st.slider("Default Interest Rate (%)", 1, 50, 15)

    if st.button("Save System Settings"):
        # You could save these to the 'Settings' sheet similarly to the logo
        st.success(f"Configuration for {business_name} saved! ✅")

    st.markdown("---")

    # --- DANGER ZONE ---
    st.subheader("⚠️ Danger Zone")
    st.write("Deleting data is permanent. Proceed with extreme caution.")
    
    confirm_reset = st.checkbox("I understand that resetting will clear all local caches.")
    
    if st.button("Clear App Cache", disabled=not confirm_reset):
        st.cache_data.clear()
        st.success("System cache cleared. Data re-syncing from Google Sheets...")
        st.rerun()

# ==============================
# LOGO HANDLING FUNCTIONS 
# (Place these outside the 'elif' block, near your other helper functions)
# ==============================
import base64

def save_logo(sheet, image_file):
    # Use your existing load_data/save_data helpers
    settings = load_data(sheet, "Settings")

    # Convert image to base64 string
    encoded = base64.b64encode(image_file.read()).decode()

    if settings.empty:
        settings = pd.DataFrame([{"Key": "logo", "Value": encoded}])
    else:
        if "logo" in settings["Key"].values:
            settings.loc[settings["Key"] == "logo", "Value"] = encoded
        else:
            new_row = pd.DataFrame([{"Key": "logo", "Value": encoded}])
            settings = pd.concat([settings, new_row], ignore_index=True)

    save_data(sheet, "Settings", settings)

def get_logo(sheet):
    settings = load_data(sheet, "Settings")
    if settings.empty:
        return None
    
    row = settings[settings["Key"] == "logo"]
    if row.empty:
        return None
        
    return row.iloc[0]["Value"]



