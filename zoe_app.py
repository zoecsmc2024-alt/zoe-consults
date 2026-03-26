import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import gspread
import io
import base64
import json
import bcrypt
import os
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from fpdf import FPDF

# ==============================
# 1. GLOBAL SETTINGS & AUTH
# ==============================
SHEET_ID = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"


# ==============================
# 2. HIGH-SPEED DATA LOADING
# ==============================
@st.cache_data(ttl=600)  # Remembers data for 10 minutes to stay fast
def get_cached_data(worksheet_name):
    """
    Fetches a specific sheet and converts it to a DataFrame.
    Uses the cached client for speed.
    """
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID)
        data = sheet.worksheet(worksheet_name).get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error loading {worksheet_name}: {e}")
        return pd.DataFrame()

# ==============================
# 2. DATABASE CONNECTION (Refined)
# ==============================

@st.cache_resource
def connect_to_gsheets():
    """
    Establishes a cached connection to the Google Sheets API.
    Using @st.cache_resource ensures we only 'log in' once per session.
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Pulled from your Streamlit Cloud Secrets
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def open_main_sheet():
    """
    Opens your specific Zoe Admin sheet using the Global SHEET_ID.
    Opening by ID is faster than opening by Name.
    """
    client = connect_to_gsheets()
    return client.open_by_key(SHEET_ID)

# ==============================
# 3. DATA HELPERS (The Engine)
# ==============================

# 1. THE DATA LOADER (Cached for 10 minutes)
@st.cache_data(ttl=600)
def get_cached_data(worksheet_name):
    """
    Fetches and caches a specific worksheet. 
    Uses the global SHEET_ID and cached connection.
    """
    try:
        # Use our optimized opener from Piece 2
        sheet = open_main_sheet()
        data = sheet.worksheet(worksheet_name).get_all_records()
        df = pd.DataFrame(data)
        # Clean up any empty rows/columns that Google Sheets often includes
        return df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"⚠️ Error loading {worksheet_name}: {e}")
        return pd.DataFrame()

# 2. THE LOGO LOADER (Cached for 1 hour)
@st.cache_data(ttl=3600)
def get_logo():
    """
    Fetches the logo once per hour. This stops the 'Quota Exceeded' 
    error because it only hits Google once every 3,600 seconds.
    """
    try:
        df_settings = get_cached_data("Settings")
        if not df_settings.empty:
            # Look for the 'logo' key in your Settings tab
            logo_row = df_settings[df_settings['Key'].str.lower() == 'logo']
            if not logo_row.empty:
                return logo_row.iloc[0]['Value']
    except Exception:
        pass
    return None

# 3. THE DATA SAVER (With Cache Clearing)
def save_data(worksheet_name, dataframe):
    """
    Overwrites a worksheet and FORCES the app to refresh.
    """
    try:
        sheet = open_main_sheet()
        worksheet = sheet.worksheet(worksheet_name)
        worksheet.clear()
        
        data_to_upload = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
        worksheet.update(data_to_upload)
        
        # 🔥 THE FIX: Use clear() without any arguments inside
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"❌ Error saving to {worksheet_name}: {e}")
        return False
# ==============================
# 4. SECURITY & SESSION MANAGEMENT
# ==============================

SESSION_TIMEOUT = 15  # Minutes

def verify_password(input_password, stored_hash):
    """Fast password verification with error handling."""
    try:
        # If using bcrypt, ensure we are comparing bytes to bytes
        return bcrypt.checkpw(input_password.encode(), stored_hash.encode())
    except Exception:
        return False

def check_session_timeout():
    """
    Quietly monitors inactivity. 
    If the user is gone too long, it wipes the memory for safety.
    """
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        return

    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()
        return

    now = datetime.now()
    elapsed = now - st.session_state.last_activity

    if elapsed > timedelta(minutes=SESSION_TIMEOUT):
        # Clear only relevant session data to avoid 'stutter'
        for key in ["logged_in", "user", "role", "last_activity"]:
            if key in st.session_state:
                del st.session_state[key]
        st.warning("⏳ Session expired for security. Please login again.")
        st.rerun()
    
    # Update timestamp quietly
    st.session_state.last_activity = now

# ==============================
# 5. THE LOGIN INTERFACE
# ==============================
def login_page():
    """
    A clean, centered login page.
    Note: I removed the sidebar() call from here to stop the 'flicker' error.
    """
    st.markdown("<h2 style='text-align: center; color: #00ffcc;'>🔐 ZOE ADMIN LOGIN</h2>", unsafe_allow_html=True)
    
    # Create a nice centered container
    with st.container():
        u_input = st.text_input("Username", placeholder="Enter username")
        p_input = st.text_input("Password", type="password", placeholder="Enter password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Access System", use_container_width=True):
                # --- THE EMERGENCY BACKDOOR ---
                if u_input == "admin" and p_input == "ZoeMaster2026":
                    st.session_state.logged_in = True
                    st.session_state.user = "Zoe (Admin)"
                    st.session_state.role = "Admin"
                    st.session_state.last_activity = datetime.now()
                    st.success("Welcome back, Master! 👑")
                    st.rerun()
                else:
                    st.error("❌ Access Denied. Check credentials.")

# ==============================
# 6. THE AUTH GATEKEEPER (Main Script)
# ==============================
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    login_page() # Using the optimized function from Piece 4
    st.stop() 
else:
    # If we made it here, they ARE logged in.
    check_session_timeout() 
    
    # Initialize session state for navigation if not set
    if "page" not in st.session_state:
        st.session_state.page = "Overview"

 

# ==============================
# 7. DOCUMENT GENERATION (PDF)
# ==============================
def generate_ledger_pdf(loan_data, ledger_df):
    """
    Generates a professional 'Neon Sky' styled PDF statement.
    Optimized for speed by generating in-memory only.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # --- NEON SKY HEADER ---
    # Header Background (Deep Blue #2B3F87)
    pdf.set_fill_color(43, 63, 135) 
    pdf.rect(0, 0, 210, 45, 'F')
    
    # Company Title (Neon Green #00FFCC)
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(0, 255, 204) 
    pdf.text(15, 20, "ZOE CONSULTS SMC LIMITED")
    
    # Subheader
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(255, 255, 255)
    borrower_name = str(loan_data.get('Borrower', 'Client')).upper()
    pdf.text(15, 30, f"OFFICIAL CLIENT STATEMENT: {borrower_name}")
    pdf.text(15, 38, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # --- CLIENT DETAILS ---
    pdf.set_y(50)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 10)
    
    loan_id = loan_data.get('Loan_ID', 'N/A')
    start_date = loan_data.get('Start_Date', 'N/A')
    total_due = float(loan_data.get('Total_Repayable', 0))
    
    pdf.cell(0, 8, f"Loan ID: {loan_id}  |  Start Date: {start_date}", 0, 1)
    pdf.cell(0, 8, f"Total Repayable: {total_due:,.0f} UGX", 0, 1)
    pdf.ln(5)

    # --- TABLE HEADERS ---
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 9)
    # Widths: Date(25), Description(65), Debit(30), Credit(30), Balance(35) = 185 total
    pdf.cell(25, 10, "Date", 1, 0, 'C', True)
    pdf.cell(65, 10, "Description", 1, 0, 'C', True)
    pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
    pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
    pdf.cell(35, 10, "Balance", 1, 1, 'C', True)

    # --- TABLE ROWS ---
    pdf.set_font("Arial", '', 8)
    for _, row in ledger_df.iterrows():
        # Ensure date is string
        date_str = str(row['Date'])[:10]
        
        pdf.cell(25, 8, date_str, 1)
        pdf.cell(65, 8, str(row['Description'])[:40], 1) # Cap description length
        pdf.cell(30, 8, f"{float(row['Debit']):,.0f}", 1, 0, 'R')
        pdf.cell(30, 8, f"{float(row['Credit']):,.0f}", 1, 0, 'R')
        pdf.cell(35, 8, f"{float(row['Balance']):,.0f}", 1, 1, 'R')

    # Return the bytes for the download button
    return pdf.output(dest='S').encode('latin-1')

# ==============================
# 8. SYSTEM & UI CONFIGURATION
# ==============================
# This MUST be the first Streamlit command in the whole script
st.set_page_config(page_title="Zoe Admin", layout="wide", initial_sidebar_state="expanded")

# Injection of the 'Neon Sky' Design System
st.markdown("""
<style>
    /* 1. MAIN APP WORKSPACE */
    .stApp {
        background-color: #F0F7FF !important;
    }

    /* 2. SIDEBAR - Deep Midnight & Neon Border */
    section[data-testid="stSidebar"] {
        background-color: #020617 !important;
        border-right: 2px solid #2B3F87 !important;
    }

    /* 3. CLEAN SIDEBAR BUTTONS */
    /* Removes the default Streamlit button styling that looks 'clunky' */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        color: #94A3B8 !important;
        border: none !important;
        width: 100% !important;
        text-align: left !important;
        padding: 10px 15px !important;
        transition: all 0.3s ease;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        color: #00FFCC !important; /* Neon Green Glow */
        background-color: rgba(0, 255, 204, 0.05) !important;
        transform: translateX(5px);
    }

    /* 4. METRIC CARDS - Glassmorphism Effect */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(43, 63, 135, 0.1) !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05) !important;
        padding: 20px !important;
    }

    /* 5. BRANDING ELEMENTS */
    .sidebar-brand {
        color: #FFFFFF !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
        text-shadow: 0px 0px 10px rgba(0, 255, 204, 0.3);
    }

    .online-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #00FFCC;
        font-size: 12px;
        font-weight: 600;
        margin-top: 5px;
    }

    .online-dot {
        height: 8px;
        width: 8px;
        background-color: #00FFCC;
        border-radius: 50%;
        box-shadow: 0 0 10px #00FFCC;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)
# ==============================
# 9. UTILITY FUNCTIONS (WhatsApp, Receipts, Logo)
# ==============================

def send_whatsapp(phone, msg):
    """
    Sends a WhatsApp message via Twilio.
    Wrapped in a try-block so the app doesn't crash if the internet blips.
    """
    try:
        client_tw = Client(st.secrets["TWILIO_SID"], st.secrets["TWILIO_TOKEN"])
        client_tw.messages.create(
            from_='whatsapp:+14155238886',
            body=msg,
            to=f'whatsapp:{phone}'
        )
        return True
    except Exception as e:
        st.error(f"⚠️ WhatsApp failed to send: {e}")
        return False

def save_logo_to_sheet(image_file):
    """
    Encodes and saves the logo to the 'Settings' worksheet.
    Optimized to prevent duplicate keys and handle empty sheets.
    """
    try:
        # Load current settings using our cached helper
        settings = get_cached_data("Settings") 
        
        # Convert image to Base64
        encoded = base64.b64encode(image_file.read()).decode()
        
        # If 'logo' exists, update it; otherwise, add a new row
        if not settings.empty and "Key" in settings.columns:
            if "logo" in settings["Key"].values:
                settings.loc[settings["Key"] == "logo", "Value"] = encoded
            else:
                new_row = pd.DataFrame([{"Key": "logo", "Value": encoded}])
                settings = pd.concat([settings, new_row], ignore_index=True)
        else:
            # Create fresh settings if sheet is empty
            settings = pd.DataFrame([{"Key": "logo", "Value": encoded}])
        
        # Save back to Google and Clear Cache so the new logo shows up
        success = save_data("Settings", settings)
        if success:
            st.cache_data.clear() # Force app to see the new logo
            return True
    except Exception as e:
        st.error(f"❌ Logo Save Error: {e}")
    return False

# NOTE: Your 'make_receipt' using SimpleDocTemplate is kept as is, 
# but I recommend moving toward the FPDF version we built in Piece 5 
# for consistent styling!

# ==============================
# 10. THE SIDEBAR NAVIGATION
# ==============================

def sidebar():
    role = st.session_state.get("role", "Staff")
    user = st.session_state.get("user", "Guest")
    current_page = st.session_state.get("page", "Overview")

    # 1. THE LOGO LOADER (Now 100x Faster via Cache)
    logo_base64 = get_logo() # Uses our cached function from Piece 3
    
    if logo_base64:
        img_src = f"data:image/png;base64,{logo_base64}"
        st.sidebar.markdown(f"""
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <div style="width: 85px; height: 85px; border-radius: 50%; overflow: hidden; 
                            border: 3px solid #00ffcc; box-shadow: 0px 0px 15px rgba(0, 255, 204, 0.5);">
                    <img src="{img_src}" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # 2. BRANDING & USER INFO
    st.sidebar.markdown(f"""
        <div style="text-align: center;">
            <h2 class="sidebar-brand">ZOE CONSULTS</h2>
            <div class="online-indicator">
                <span class="online-dot"></span> System Online
            </div>
            <p style='color:#94A3B8; font-size:14px; margin-top:10px;'>
                👤 <span style='color:#00ffcc;'>{user} ({role})</span>
            </p>
        </div>
        <hr style='border-top: 1px solid #2B3F87; margin: 20px 0;'>
    """, unsafe_allow_html=True)

    # 3. NAVIGATION MENU
    menu = {
        "Overview": "📊", "Loans": "💵", "Borrowers": "👥", "Collateral": "🛡️",
        "Calendar": "📅", "Ledger": "📄", "Overdue Tracker": "⏰",
        "Payments": "💵", "Expenses": "📁", "PettyCash": "💵",
        "Payroll": "🧾", "Reports": "📈", "Settings": "⚙️"
    }
    restricted = ["Settings", "Reports", "Payroll"]

    for item, icon in menu.items():
        # Permission Check
        if role != "Admin" and item in restricted:
            continue

        # Visual Active State
        if current_page == item:
            st.sidebar.markdown(f"""
                <div class="active-menu-item">
                    {icon} &nbsp; {item}
                </div>
            """, unsafe_allow_html=True)
        else:
            # Clean Button Navigation
            if st.sidebar.button(f"{icon} {item}", key=f"nav_{item}", use_container_width=True):
                st.session_state.page = item
                st.rerun()

    # 4. LOGOUT (Clean & Simple)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
        st.session_state.clear()
        st.rerun()

# ==============================
# 11. DASHBOARD LOGIC (OVERVIEW)
# ==============================

def show_overview():
    st.markdown("<h2 style='color: #2B3F87;'>📊 Financial Dashboard</h2>", unsafe_allow_html=True)
    
    # 1. LOAD PRIMARY DATA
    df = get_cached_data("Loans")
    pay_df = get_cached_data("Payments")
    exp_df = get_cached_data("Expenses")

    if df.empty:
        st.warning("⚠️ No data found in 'Loans'. Add some borrowers to get started!")
        return

    # 2. DATA CRUNCHING (Monthly Trends for Bar Chart)
    if not pay_df.empty and not exp_df.empty:
        pay_df["Date"] = pd.to_datetime(pay_df["Date"])
        exp_df["Date"] = pd.to_datetime(exp_df["Date"])
        
        # Group by Month
        inc_m = pay_df.groupby(pay_df["Date"].dt.strftime('%b %Y'))["Amount"].sum().reset_index()
        exp_m = exp_df.groupby(exp_df["Date"].dt.strftime('%b %Y'))["Amount"].sum().reset_index()
        
        # Merge into one master table for the chart
        merged_df = pd.merge(inc_m, exp_m, on="Date", how="outer", suffixes=('_Inc', '_Exp')).fillna(0)
        merged_df.columns = ["Month", "Income", "Expenses"]
    else:
        merged_df = pd.DataFrame(columns=["Month", "Income", "Expenses"])

    # 3. LOAN STATUS CLEANING
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Interest"] = pd.to_numeric(df["Interest"], errors="coerce").fillna(0)
    df["Amount_Paid"] = pd.to_numeric(df.get("Amount_Paid", 0), errors="coerce").fillna(0)
    df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
    df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
    
    today = pd.Timestamp.today()
    df["Auto_Status"] = df["Status"]
    total_due = df["Amount"] + df["Interest"]
    df.loc[(df["End_Date"] < today) & (df["Amount_Paid"] < total_due), "Auto_Status"] = "Overdue"

    # 4. METRICS ROW
    total_issued = df["Amount"].sum()
    total_profit = df["Interest"].sum()
    total_collected = df["Amount_Paid"].sum()
    overdue_count = df[df["Auto_Status"] == "Overdue"].shape[0]
    
    m1, m2, m3, m4 = st.columns(4)

    # 1. Total Issued (Capital - Corporate Blue)
    m1.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold; letter-spacing:1px;">💰 TOTAL ISSUED</p>
            <h3 style="margin:0; color:#2B3F87; font-size: 20px;">{total_issued:,.0f} <span style="font-size:12px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # 2. Expected Profit (Growth - Neon Green)
    m2.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #00ffcc; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold; letter-spacing:1px;">📈 EXPECTED PROFIT</p>
            <h3 style="margin:0; color:#00ffcc; font-size: 20px;">{total_profit:,.0f} <span style="font-size:12px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # 3. Collected (Cash Flow - Cyan/Teal)
    m3.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #00D1FF; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold; letter-spacing:1px;">💵 COLLECTED</p>
            <h3 style="margin:0; color:#00D1FF; font-size: 20px;">{total_collected:,.0f} <span style="font-size:12px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # 4. Overdue (Risk - Alert Red)
    m4.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold; letter-spacing:1px;">⚠️ OVERDUE LOANS</p>
            <h3 style="margin:0; color:#FF4B4B; font-size: 24px;">{overdue_count}</h3>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 5. VISUALS SECTION (This is where your Chart Columns go)
    # [Insert your c1, c2 columns code here...]

    # ==============================
    # VISUALS (Neon Styled)
    # ==============================
    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        status_df = df["Auto_Status"].value_counts().reset_index()
        status_df.columns = ["Status", "Count"]
        fig_pie = px.pie(
            status_df, names="Status", values="Count", 
            hole=0.4, title="Loan Portfolio Health",
            color_discrete_sequence=["#00ffcc", "#2B3F87", "#FF4B4B"]
        )
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True, key="overview_pie_chart")

    with c2:
        if 'merged_df' in locals() and not merged_df.empty:
            fig_bar = px.bar(
                merged_df, x="Month", y=["Income", "Expenses"], 
                barmode="group", title="Monthly Cashflow",
                color_discrete_map={"Income": "#00ffcc", "Expenses": "#FF4B4B"}
            )
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True, key="overview_bar_chart")
        else:
            st.info("📊 Monthly cashflow data is being prepared...")

    # ==============================
    # DATA TABLES (With Comma Formatting)
    # ==============================
    st.markdown("### 📋 Detailed Records")
    tab1, tab2 = st.tabs(["🚨 Critical Overdue", "📅 Recent Activity"])
    
    with tab1:
        overdue_display = df[df["Auto_Status"] == "Overdue"][[
            "Borrower", "Amount", "End_Date", "Amount_Paid"
        ]].sort_values("End_Date")
        
        if not overdue_display.empty:
            # Apply formatting for commas
            st.dataframe(
                overdue_display.style.format({
                    "Amount": "{:,.0f} UGX",
                    "Amount_Paid": "{:,.0f} UGX"
                }), 
                use_container_width=True, hide_index=True
            )
        else:
            st.success("No overdue loans! 🌟")
    
    with tab2:
        recent_activity = df.sort_values("Start_Date", ascending=False).head(10)
        # Apply formatting for commas
        st.dataframe(
            recent_activity.style.format({
                "Amount": "{:,.0f} UGX",
                "Interest": "{:,.0f} UGX",
                "Total_Repayable": "{:,.0f} UGX",
                "Amount_Paid": "{:,.0f} UGX"
            }), 
            use_container_width=True, hide_index=True
        )


# ==============================
# 12. BORROWERS MANAGEMENT PAGE
# ==============================

def show_borrowers():
    st.markdown("<h2 style='color: #2B3F87;'>👥 Borrowers Management</h2>", unsafe_allow_html=True)

    # 1. LOAD DATA
    df = get_cached_data("Borrowers")
    loans_df = get_cached_data("Loans") 

    if df.empty:
        # Added Email and Next_of_Kin to the fallback structure
        df = pd.DataFrame(columns=["Borrower_ID", "Name", "Phone", "Email", "National_ID", "Address", "Next_of_Kin", "Status", "Date_Added"])

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_list, tab_add, tab_manage = st.tabs(["📋 View All", "➕ Add New", "⚙️ Manage & Edit"])

    # --- TAB 1: SEARCH & LIST ---
    with tab_list:
        col1, col2 = st.columns([2, 1])
        search = col1.text_input("🔍 Search Name, Phone or Email")
        status_filter = col2.selectbox("Filter", ["All", "Active", "Inactive"])

        filtered_df = df.copy()
        if search:
            # Added Email to search functionality
            filtered_df = filtered_df[
                filtered_df["Name"].str.contains(search, case=False, na=False) |
                filtered_df["Phone"].str.contains(search, case=False, na=False) |
                filtered_df["Email"].str.contains(search, case=False, na=False)
            ]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df["Status"] == status_filter]

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # --- TAB 2: ADD BORROWER ---
    with tab_add:
        with st.form("add_borrower_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name*")
            phone = c2.text_input("Phone Number*")
            
            # --- NEW FIELDS ---
            email = c1.text_input("Email Address")
            kin = c2.text_input("Next of Kin (Name & Phone)")
            
            nid = c1.text_input("National ID / NIN")
            addr = c2.text_input("Physical Address")
            
            if st.form_submit_button("🚀 Save Borrower"):
                if name and phone:
                    new_id = int(df["Borrower_ID"].max() + 1) if not df.empty else 1
                    new_entry = pd.DataFrame([{
                        "Borrower_ID": new_id, 
                        "Name": name, 
                        "Phone": phone,
                        "Email": email,        # Save Email
                        "National_ID": nid, 
                        "Address": addr, 
                        "Next_of_Kin": kin,    # Save Next of Kin
                        "Status": "Active",
                        "Date_Added": datetime.now().strftime("%Y-%m-%d")
                    }])
                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    if save_data("Borrowers", updated_df):
                        st.success(f"✅ {name} added to system!")
                        st.rerun()
                else:
                    st.error("⚠️ Please fill in Name and Phone.")

    # --- TAB 3: MANAGE & SUMMARY ---
    with tab_manage:
        if not df.empty:
            target_name = st.selectbox("Select Borrower to Manage", df["Name"].tolist())
            # Fetch borrower details
            b_data = df[df["Name"] == target_name].iloc[0]
            
            # Show the new contact details in the summary
            col_info1, col_info2 = st.columns(2)
            col_info1.write(f"**Email:** {b_data.get('Email', 'N/A')}")
            col_info2.write(f"**Next of Kin:** {b_data.get('Next_of_Kin', 'N/A')}")
            
            st.markdown("---")
            
            user_loans = loans_df[loans_df["Borrower"] == target_name] if not loans_df.empty else pd.DataFrame()
            
            if not user_loans.empty:
                total_paid = pd.to_numeric(user_loans['Amount_Paid']).sum()
                total_remaining = pd.to_numeric(user_loans['Total_Repayable']).sum() - total_paid
                active_count = user_loans[user_loans["Status"] != "Closed"].shape[0]

                st.markdown(f"### 📋 Portfolio Summary for {target_name}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Loans Taken", len(user_loans))
                m2.metric("Active Loans", active_count)
                m3.metric("Total Outstanding", f"{total_remaining:,.0f} UGX")

                st.write("**Loan History:**")
                st.dataframe(user_loans[["Loan_ID", "Amount", "Status", "End_Date"]], use_container_width=True, hide_index=True)
            else:
                st.info("This borrower has not taken any loans yet.")





# ==============================
# 13. LOANS MANAGEMENT PAGE
# ==============================

def show_loans():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Loans Management</h2>", unsafe_allow_html=True)
    
    # 1. LOAD DATA
    borrowers_df = get_cached_data("Borrowers")
    loans_df = get_cached_data("Loans")

    if borrowers_df.empty:
        st.warning("⚠️ No borrowers found. Register a client first!")
        return
        
    active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]

    # --- TABBED INTERFACE ---
    tab_issue, tab_view, tab_manage = st.tabs(["➕ Issue Loan", "📊 Portfolio", "⚙️ Manage Loans"])

    # ==============================
# 13. LOANS MANAGEMENT PAGE
# ==============================

def show_loans():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Loans Management</h2>", unsafe_allow_html=True)
    
    # 1. LOAD DATA
    borrowers_df = get_cached_data("Borrowers")
    loans_df = get_cached_data("Loans")

    if borrowers_df.empty:
        st.warning("⚠️ No borrowers found. Register a client first!")
        return
        
    active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]

    # --- TABBED INTERFACE ---
    tab_issue, tab_view, tab_manage = st.tabs(["➕ Issue Loan", "📊 Portfolio", "⚙️ Manage Loans"])

    # Now continue with the rest of your TAB 1, TAB 2, etc. logic here...
    # ==============================
    # TAB 1: ISSUE LOAN
    # ==============================
    with tab_issue:
        if active_borrowers.empty:
            st.info("💡 Tip: Activate a borrower to issue a loan.")
        else:
            with st.form("loan_issue_form"):
                col1, col2 = st.columns(2)
                selected_borrower = col1.selectbox("Select Borrower", active_borrowers["Name"].unique())
                amount = col1.number_input("Principal Amount (UGX)", min_value=0, step=50000)
                date_issued = col1.date_input("Date Issued", value=datetime.now())
                
                # NEW: Added Loan Type to the issue form
                l_type = col2.selectbox("Loan Type", ["Business", "Personal", "Emergency", "Other"])
                interest_rate = col2.number_input("Interest Rate (%)", min_value=0.0, step=0.5)
                date_due = col2.date_input("Due Date", value=date_issued + timedelta(days=30))

                interest = (interest_rate / 100) * amount
                total_due = amount + interest
                
                st.write(f"**Preview:** Total Repayable: {total_due:,.0f} UGX")

                if st.form_submit_button("🚀 Confirm & Issue Loan"):
                    if amount > 0:
                        # 1. FIX: Ensure new_id is a clean integer
                        last_id = loans_df["Loan_ID"].max()
                        new_id = int(last_id + 1) if pd.notna(last_id) else 1
                        
                        # 2. FIX: Ensure math doesn't produce 'nan'
                        safe_interest = float(interest) if pd.notna(interest) else 0.0
                        safe_total = float(total_due) if pd.notna(total_due) else float(amount)

                        new_loan = pd.DataFrame([{
                            "Loan_ID": new_id, 
                            "Borrower": selected_borrower, 
                            "Type": l_type,
                            "Amount": float(amount), 
                            "Interest": safe_interest,
                            "Total_Repayable": safe_total, 
                            "Amount_Paid": 0.0, # Use 0.0 instead of 0 to keep it as float
                            "Start_Date": date_issued.strftime("%Y-%m-%d"),
                            "End_Date": date_due.strftime("%Y-%m-%d"),
                            "Status": "Active"
                        }])
                        
                        # 3. FIX: Fill any accidental NaNs in the final combined dataframe
                        updated_df = pd.concat([loans_df, new_loan], ignore_index=True).fillna(0)
                        
                        if save_data("Loans", updated_df):
                            st.success(f"Loan #{new_id} Issued!")
                            st.rerun()

    # ==============================
    # TAB 2: PORTFOLIO INSPECTOR
    # ==============================
    with tab_view:
        if not loans_df.empty:
            # Added "Type" to the expected columns
            expected_cols = ["Loan_ID", "Borrower", "Type", "Amount", "Interest", "Total_Repayable", "Amount_Paid", "Start_Date", "End_Date", "Status"]
            existing_cols = [c for c in expected_cols if c in loans_df.columns]
            display_df = loans_df[existing_cols].copy()
            
            # Data Cleaning
            display_df["Interest"] = pd.to_numeric(display_df["Interest"], errors='coerce').fillna(0)
            display_df["Amount"] = pd.to_numeric(display_df["Amount"], errors='coerce').fillna(0)
            display_df["Amount_Paid"] = pd.to_numeric(display_df["Amount_Paid"], errors='coerce').fillna(0)
            display_df["Total_Repayable"] = display_df["Amount"] + display_df["Interest"]
            display_df["Outstanding"] = display_df["Total_Repayable"] - display_df["Amount_Paid"]
            
            sel_id = st.selectbox("🔍 Select Loan to Inspect", display_df["Loan_ID"].unique())
            loan_info = display_df[display_df["Loan_ID"] == sel_id].iloc[0]
            
            # --- STYLED METRICS ROW ---
            # Make sure this line exists and defines p1, p2, AND p3
            p1, p2, p3 = st.columns(3)
            
            # Dynamic Status Color Logic
            status_color = "#00ffcc" if loan_info['Status'] == "Active" else "#FF4B4B" if loan_info['Status'] == "Overdue" else "#2B3F87"
            
            # 1. Paid Card
            p1.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #00ffcc; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">PAID</p>
                    <h3 style="margin:0; color:#2B3F87;">{loan_info['Amount_Paid']:,.0f} UGX</h3>
                </div>
            """, unsafe_allow_html=True)

            # 2. Outstanding Card
            p2.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">OUTSTANDING</p>
                    <h3 style="margin:0; color:#FF4B4B;">{loan_info['Outstanding']:,.0f} UGX</h3>
                </div>
            """, unsafe_allow_html=True)

            # 3. Status Card (This is where your error is happening)
            p3.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid {status_color}; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">LOAN STATUS</p>
                    <h3 style="margin:0; color:{status_color}; text-transform: uppercase;">{loan_info['Status']}</h3>
                </div>
            """, unsafe_allow_html=True) 
            st.progress(min(max(loan_info['Amount_Paid'] / loan_info['Total_Repayable'], 0.0), 1.0))
            
            st.dataframe(display_df.style.format({
                "Amount": "{:,.0f}", "Interest": "{:,.0f}", "Total_Repayable": "{:,.0f}", "Amount_Paid": "{:,.0f}", "Outstanding": "{:,.0f}"
            }), use_container_width=True, hide_index=True)

    # ==============================
    # TAB 3: MANAGE
    # ==============================
    with tab_manage:
        if not loans_df.empty:
            st.subheader("🛠️ Edit or Remove Loan Records")
            manage_list = loans_df.apply(lambda x: f"ID: {x['Loan_ID']} | {x['Borrower']} - {x['Amount']}", axis=1).tolist()
            selected_manage = st.selectbox("Select Loan to Modify", manage_list)
            m_id = int(selected_manage.split(" | ")[0].replace("ID: ", ""))
            m_row = loans_df[loans_df["Loan_ID"] == m_id].iloc[0]

            with st.container():
                col_e1, col_e2 = st.columns(2)
                upd_amt = col_e1.number_input("Edit Principal", value=float(m_row["Amount"]), step=10000.0)
                try:
                    curr_rate = (float(m_row["Interest"]) / float(m_row["Amount"])) * 100 if float(m_row["Amount"]) > 0 else 0.0
                except: curr_rate = 0.0
                upd_rate = col_e1.number_input("Edit Interest Rate (%)", value=float(curr_rate), step=0.5)
                upd_paid = col_e1.number_input("Manual Paid Adjust", value=float(m_row["Amount_Paid"]))

                # --- RIGHT COLUMN (Status & Dates) ---
                upd_stat = col_e2.selectbox("Edit Status", ["Active", "Overdue", "Closed"], 
                                           index=["Active", "Overdue", "Closed"].index(m_row["Status"]))
                
                # SAFETY FIX: Handle missing 'Type' for older loans
                loan_types = ["Business", "Personal", "Emergency", "Other"]
                current_type = str(m_row.get("Type", "Business")) # Default to Business if empty
                
                # If the type in the sheet isn't in our list, use 'Business'
                if current_type not in loan_types:
                    current_type = "Business"
                
                upd_type = col_e2.selectbox("Edit Type", loan_types, 
                                           index=loan_types.index(current_type))
                
                try:
                    s_val, e_val = datetime.strptime(str(m_row["Start_Date"]), "%Y-%m-%d"), datetime.strptime(str(m_row["End_Date"]), "%Y-%m-%d")
                except: s_val, e_val = datetime.now(), datetime.now()
                upd_start = col_e2.date_input("Edit Start Date", value=s_val)
                upd_end = col_e2.date_input("Edit End Date", value=e_val)

                b_upd, b_del = st.columns(2)
                if b_upd.button("💾 Save Changes", use_container_width=True):
                    new_int = upd_amt * (upd_rate / 100)
                    loans_df.loc[loans_df["Loan_ID"] == m_id, ["Amount", "Amount_Paid", "Status", "Start_Date", "End_Date", "Interest", "Total_Repayable", "Type"]] = \
                        [upd_amt, upd_paid, upd_stat, upd_start.strftime("%Y-%m-%d"), upd_end.strftime("%Y-%m-%d"), new_int, (upd_amt + new_int), upd_type]
                    if save_data("Loans", loans_df):
                        st.success("Updated!"); st.rerun()

                if b_del.button("🗑️ Delete Permanently", use_container_width=True):
                    if save_data("Loans", loans_df[loans_df["Loan_ID"] != m_id]):
                        st.warning("Deleted!"); st.rerun()
# ==============================
# 14. PAYMENTS & COLLECTIONS PAGE (Upgraded)
# ==============================

def show_payments():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Payments Management</h2>", unsafe_allow_html=True)
    
    # 1. FETCH DATA
    loans_df = get_cached_data("Loans")
    payments_df = get_cached_data("Payments")

    if loans_df.empty:
        st.info("ℹ️ No loans found in the system.")
        return

    # Ensure column naming consistency
    if "status" in loans_df.columns:
        loans_df = loans_df.rename(columns={"status": "Status"})

    # TABS FOR CLEAN UI
    tab_new, tab_history, tab_manage = st.tabs(["➕ Record Payment", "📜 History & Trends", "⚙️ Edit/Delete"])

    # ==============================
    # TAB 1: RECORD NEW PAYMENT
    # ==============================
    with tab_new:
        active_loans = loans_df[loans_df["Status"] != "Closed"]
        if active_loans.empty:
            st.success("🎉 All loans are currently cleared!")
        else:
            loan_options = active_loans.apply(lambda x: f"ID: {x['Loan_ID']} - {x['Borrower']}", axis=1).tolist()
            selected_option = st.selectbox("Select Loan to Credit", loan_options)
            selected_id = int(selected_option.split(" - ")[0].replace("ID: ", ""))
            loan = active_loans[active_loans["Loan_ID"] == selected_id].iloc[0]

            # Calculation
            total_rep = pd.to_numeric(loan["Total_Repayable"], errors='coerce')
            paid_so_far = pd.to_numeric(loan["Amount_Paid"], errors='coerce')
            outstanding = total_rep - paid_so_far

            # --- STYLED CARDS ---
            c1, c2, c3 = st.columns(3)
            status_color = "#00ffcc" if loan['Status'] == "Active" else "#FF4B4B"
            
            c1.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">CLIENT</p><h3 style="margin:0; color:#2B3F87;">{loan['Borrower']}</h3></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">BALANCE DUE</p><h3 style="margin:0; color:#FF4B4B;">{outstanding:,.0f} <span style="font-size:14px;">UGX</span></h3></div>""", unsafe_allow_html=True)
            c3.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid {status_color}; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">STATUS</p><h3 style="margin:0; color:{status_color}; text-transform:uppercase;">{loan['Status']}</h3></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            with st.form("payment_form", clear_on_submit=True):
                col_a, col_b, col_c = st.columns(3) # Changed to 3 columns for better fit
                
                pay_amount = col_a.number_input("Amount Received (UGX)", min_value=0, step=10000)
                pay_method = col_b.selectbox("Method", ["Mobile Money", "Cash", "Bank Transfer"])
                
                # --- NEW: MANUAL DATE INPUT ---
                # Default to today, but you can now pick any date in the past
                pay_date = col_c.date_input("Payment Date", value=datetime.now())
                
                if st.form_submit_button("✅ Post Payment", use_container_width=True):
                    if 0 < pay_amount <= (outstanding + 100):
                        try:
                            # Create Payment Record
                            new_p_id = int(payments_df["Payment_ID"].max() + 1) if not payments_df.empty else 1
                            new_payment = pd.DataFrame([{
                                "Payment_ID": new_p_id, 
                                "Loan_ID": selected_id, 
                                "Borrower": loan["Borrower"],
                                "Amount": pay_amount, 
                                # Use the manually picked date instead of 'now'
                                "Date": pay_date.strftime("%Y-%m-%d"), 
                                "Method": pay_method, 
                                "Recorded_By": st.session_state.get("user", "Zoe (Admin)")
                            }])

                            # Update Loan Balance logic
                            idx = loans_df[loans_df["Loan_ID"] == selected_id].index[0]
                            loans_df.at[idx, "Amount_Paid"] = paid_so_far + pay_amount
                            
                            # Auto-Close logic
                            if loans_df.at[idx, "Amount_Paid"] >= (total_rep - 10):
                                loans_df.at[idx, "Status"] = "Closed"

                            if save_data("Payments", pd.concat([payments_df, new_payment], ignore_index=True)) and save_data("Loans", loans_df):
                                st.success(f"Payment for {pay_date.strftime('%d %b')} recorded!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Invalid amount. Cannot exceed balance due.")

    # ==============================
    # TAB 2: HISTORY
    # ==============================
    with tab_history:
        if not payments_df.empty:
            st.dataframe(
                payments_df.sort_values("Date", ascending=False).style.format({"Amount": "{:,.0f}"}), 
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No payment records found.")

    # ==============================
    # TAB 3: ADJUST PAYMENTS
    # ==============================
    with tab_manage:
        if payments_df.empty:
            st.info("No payments to manage.")
        else:
            st.subheader("⚠️ Adjust Previous Payments")
            pay_list = payments_df.apply(lambda x: f"PayID: {x['Payment_ID']} | {x['Borrower']} - {x['Amount']:,.0f} UGX", axis=1).tolist()
            selected_pay = st.selectbox("Select Payment Record", pay_list)
            
            p_id = int(selected_pay.split(" | ")[0].replace("PayID: ", ""))
            p_row = payments_df[payments_df["Payment_ID"] == p_id].iloc[0]
            target_loan_id = p_row["Loan_ID"]

            # DELETE LOGIC (Recalculates Loan Balance Automatically)
            if st.button("🗑️ Delete This Payment Permanently", use_container_width=True):
                # 1. Remove from Payments
                new_payments_df = payments_df[payments_df["Payment_ID"] != p_id]
                
                # 2. Recalculate Loan Balance for the affected loan
                loan_payments = new_payments_df[new_payments_df["Loan_ID"] == target_loan_id]
                total_collected = loan_payments["Amount"].sum() if not loan_payments.empty else 0
                
                l_idx = loans_df[loans_df["Loan_ID"] == target_loan_id].index[0]
                loans_df.at[l_idx, "Amount_Paid"] = total_collected
                
                # Re-open loan if it was closed but now has balance
                total_req = loans_df.at[l_idx, "Total_Repayable"]
                if total_collected < (total_req - 10):
                    loans_df.at[l_idx, "Status"] = "Active"

                if save_data("Payments", new_payments_df) and save_data("Loans", loans_df):
                    st.warning("Payment Deleted. Loan balance adjusted.")
                    st.rerun()
    
# ==============================
# 15. COLLATERAL MANAGEMENT PAGE
# ==============================

def show_collateral():
    st.markdown("<h2 style='color: #2B3F87;'>🛡️ Collateral Management</h2>", unsafe_allow_html=True)
    
    # 1. FETCH ALL DATA
    collateral_df = get_cached_data("Collateral")
    loans_df = get_cached_data("Loans") # <--- CRITICAL FIX: This stops the NameError
    col_df = collateral_df

    # 2. INITIALIZE IF EMPTY
    if collateral_df.empty:
        collateral_df = pd.DataFrame(columns=[
            "Collateral_ID", "Borrower", "Loan_ID", "Type", 
            "Description", "Value", "Status", "Date_Added"
        ])

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_reg, tab_view = st.tabs(["➕ Register Asset", "📋 Inventory & Status"])

    # --- TAB 1: REGISTER COLLATERAL ---
    with tab_reg:
        if loans_df.empty:
            st.warning("⚠️ No loans found. Issue a loan before adding collateral.")
        else:
            # Only show loans that are still Active or Overdue
            active_loan_mask = loans_df["Status"].isin(["Active", "Overdue"])
            available_loans = loans_df[active_loan_mask]

            if available_loans.empty:
                st.info("✅ All current loans are cleared. No assets need to be held.")
            else:
                with st.form("collateral_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    
                    # Searchable selection
                    loan_options = available_loans.apply(lambda x: f"ID: {x['Loan_ID']} - {x['Borrower']}", axis=1).tolist()
                    selected_loan = c1.selectbox("Link to Loan", loan_options)
                    
                    # Extract ID and Borrower Name
                    sel_id = int(selected_loan.split(" - ")[0].replace("ID: ", ""))
                    sel_borrower = selected_loan.split(" - ")[1]

                    asset_type = c2.selectbox("Asset Type", ["Logbook (Car)", "Land Title", "Electronics", "House Deed", "Other"])
                    desc = st.text_input("Asset Description", placeholder="e.g. Toyota Prado UBA 123X Black")
                    est_value = st.number_input("Estimated Value (UGX)", min_value=0, step=100000)

                    if st.form_submit_button("🔒 Secure Asset"):
                        if desc and est_value > 0:
                            new_c_id = int(collateral_df["Collateral_ID"].max() + 1) if not collateral_df.empty else 1
                            new_asset = pd.DataFrame([{
                                "Collateral_ID": new_c_id,
                                "Borrower": sel_borrower,
                                "Loan_ID": sel_id,
                                "Type": asset_type,
                                "Description": desc,
                                "Value": est_value,
                                "Status": "Held",
                                "Date_Added": datetime.now().strftime("%Y-%m-%d")
                            }])
                            
                            if save_data("Collateral", pd.concat([collateral_df, new_asset], ignore_index=True)):
                                st.success(f"Asset #{new_c_id} registered for {sel_borrower}!")
                                st.rerun()
                        else:
                            st.error("Please provide a description and value.")

    # --- TAB 2: VIEW & UPDATE ---
    with tab_view:
        if not col_df.empty:
            # 1. CLEANING & REPAIR
            col_df["Value"] = pd.to_numeric(col_df["Value"], errors='coerce').fillna(0)
            
            # 2. COLORED METRIC CARDS
            total_val = col_df["Value"].sum()
            in_custody = col_df[col_df["Status"] == "In Custody"].shape[0]
            
            m1, m2 = st.columns(2)
            # Total Value Card (Blue)
            m1.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL ASSET VALUE (EST)</p>
                    <h2 style="margin:0; color:#2B3F87;">{total_val:,.0f} <span style="font-size:14px;">UGX</span></h2>
                </div>
            """, unsafe_allow_html=True)

            # Assets in Custody Card (Cyan)
            m2.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #00D1FF; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">ASSETS IN CUSTODY</p>
                    <h2 style="margin:0; color:#00D1FF;">{in_custody}</h2>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 3. FORMATTED TABLE
            st.dataframe(
                col_df.style.format({"Value": "{:,.0f}"}),
                use_container_width=True, hide_index=True
            )

            # 4. DELETE & EDIT SECTION
            with st.expander("⚙️ Manage Collateral Records (Edit/Delete)"):
                manage_list = col_df.apply(lambda x: f"ID: {x['Collateral_ID']} | {x['Borrower']} - {x['Description']}", axis=1).tolist()
                selected_col = st.selectbox("Select Asset to Modify", manage_list)
                
                # Extract the actual ID (handling potential date-strings)
                c_id = selected_col.split(" | ")[0].replace("ID: ", "")
                c_row = col_df[col_df["Collateral_ID"].astype(str) == c_id].iloc[0]

                ce1, ce2 = st.columns(2)
                upd_desc = ce1.text_input("Edit Description", value=c_row["Description"])
                upd_val = ce1.number_input("Edit Value (UGX)", value=float(c_row["Value"]), step=100000.0)
                
                upd_stat = ce2.selectbox("Update Status", ["In Custody", "Released", "Disposed"], 
                                        index=["In Custody", "Released", "Disposed"].index(c_row["Status"]))

                btn_upd, btn_del = st.columns(2)

                if btn_upd.button("💾 Save Asset Changes", use_container_width=True):
                    col_df.loc[col_df["Collateral_ID"].astype(str) == c_id, ["Description", "Value", "Status"]] = [upd_desc, upd_val, upd_stat]
                    if save_data("Collateral", col_df):
                        st.success("Asset updated!"); st.rerun()

                if btn_del.button("🗑️ Delete Asset Record", use_container_width=True):
                    new_col_df = col_df[col_df["Collateral_ID"].astype(str) != c_id]
                    if save_data("Collateral", new_col_df):
                        st.warning("Asset record deleted!"); st.rerun()
        else:
            st.info("No collateral registered yet.")

# ==============================
# 16. COLLECTIONS & OVERDUE TRACKER
# ==============================

def show_overdue_tracker():
    st.markdown("<h2 style='color: #2B3F87;'>🔴 Collections Dashboard</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA (Memory Shield)
    loans_df = get_cached_data("Loans")

    if loans_df.empty:
        st.info("No loan data available to track.")
        return

    # 2. DATA PREPARATION
    # Ensure tracking columns exist
    for col in ["Follow_Up_Status", "Last_Contact_Date"]:
        if col not in loans_df.columns:
            loans_df[col] = "Pending"

    loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
    loans_df["Amount_Paid"] = pd.to_numeric(loans_df["Amount_Paid"], errors="coerce").fillna(0)
    loans_df["Total_Repayable"] = pd.to_numeric(loans_df["Total_Repayable"], errors="coerce").fillna(0)
    today = pd.Timestamp.today()

    # DETECT OVERDUE
    overdue_df = loans_df[
        (loans_df["End_Date"] < today) & 
        (loans_df["Amount_Paid"] < (loans_df["Total_Repayable"] - 1))
    ].copy()

    if overdue_df.empty:
        st.success("✨ Excellent! All collections are up to date.")
        return

    # 3. CALCULATE RISK & SEVERITY
    overdue_df["Days_Overdue"] = (today - overdue_df["End_Date"]).dt.days
    overdue_df["Outstanding"] = overdue_df["Total_Repayable"] - overdue_df["Amount_Paid"]

    def get_severity(days):
        if days <= 7: return "Mild"
        elif days <= 30: return "Moderate"
        return "Critical"

    overdue_df["Severity"] = overdue_df["Days_Overdue"].apply(get_severity)
    
    # Your Risk Score Logic (Outstanding weight + Days weight)
    overdue_df["Risk_Score"] = (overdue_df["Outstanding"] * 0.0001) + (overdue_df["Days_Overdue"] * 2)

    # 4. METRICS & FILTERS
    total_at_risk = overdue_df["Outstanding"].sum()
    critical_cases = overdue_df[overdue_df["Severity"] == "Critical"].shape[0]

    m1, m2 = st.columns(2)
    m1.metric("💰 Total Capital at Risk", f"{total_at_risk:,.0f} UGX")
    m2.metric("🔴 Critical Delinquency", critical_cases)

    # Filtering UI
    f1, f2 = st.columns([2, 1])
    search = f1.text_input("🔍 Find Borrower")
    sev_filter = f2.selectbox("Severity Level", ["All", "Mild", "Moderate", "Critical"])

    filtered = overdue_df.copy()
    if search:
        filtered = filtered[filtered["Borrower"].str.contains(search, case=False)]
    if sev_filter != "All":
        filtered = filtered[filtered["Severity"] == sev_filter]

    # Sort by Risk (Highest first)
    filtered = filtered.sort_values("Risk_Score", ascending=False)

    # COLOR-CODED DATAFRAME DISPLAY
    def color_severity(val):
        color = '#00ffcc' if val == 'Mild' else '#FFA500' if val == 'Moderate' else '#FF4B4B'
        return f'color: {color}; font-weight: bold;'

    st.dataframe(
        filtered[["Loan_ID", "Borrower", "Outstanding", "Days_Overdue", "Severity", "Follow_Up_Status"]].style.applymap(color_severity, subset=['Severity']),
        use_container_width=True, hide_index=True
    )

    # 5. SMART ACTION CENTER
    st.markdown("---")
    st.subheader("📞 Recovery Action Center")
    
    sel_loan_id = st.selectbox("Select Client to Contact", filtered["Loan_ID"].unique())
    loan_item = filtered[filtered["Loan_ID"] == sel_loan_id].iloc[0]

    # MESSAGE LOGIC
    severity = loan_item["Severity"]
    if severity == "Mild":
        msg = f"Reminder: Your loan is {loan_item['Days_Overdue']} days overdue. Balance: {loan_item['Outstanding']:,.0f} UGX. Please settle today."
    elif severity == "Moderate":
        msg = f"URGENT: Your loan is {loan_item['Days_Overdue']} days overdue. Balance: {loan_item['Outstanding']:,.0f} UGX. Pay immediately to avoid extra fees."
    else:
        msg = f"FINAL NOTICE: Loan overdue by {loan_item['Days_Overdue']} days. Pay {loan_item['Outstanding']:,.0f} UGX NOW to prevent legal action."

    st.info(f"📍 **Target:** {loan_item['Borrower']} | **Severity:** {severity}")
    
    msg_text = st.text_area("Recovery Message", msg, height=100)

    act_col1, act_col2 = st.columns(2)
    
    # WhatsApp Integration Button
    # Note: This assumes you have the phone number in your Loans or Borrowers sheet
    # For now, we'll use a placeholder logic
    whatsapp_url = f"https://wa.me/?text={msg_text.replace(' ', '%20')}"
    act_col1.markdown(f'<a href="{whatsapp_url}" target="_blank" style="text-decoration:none;"><button style="width:100%; height:45px; background-color:#25D366; color:white; border:none; border-radius:5px; font-weight:bold;">💬 Send via WhatsApp</button></a>', unsafe_allow_html=True)

    if act_col2.button("💾 Log Interaction", use_container_width=True):
        # Update the master dataframe
        loans_df.loc[loans_df["Loan_ID"] == sel_loan_id, "Follow_Up_Status"] = "Contacted"
        loans_df.loc[loans_df["Loan_ID"] == sel_loan_id, "Last_Contact_Date"] = datetime.now().strftime("%Y-%m-%d")
        
        if save_data("Loans", loans_df):
            st.success("Interaction logged successfully.")
            st.rerun()

# ==============================
# 17. ACTIVITY CALENDAR PAGE
# ==============================

def show_calendar():
    st.markdown("<h2 style='color: #2B3F87;'>📅 Activity Calendar</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA (Memory Shield)
    loans_df = get_cached_data("Loans")

    if loans_df.empty:
        st.info("📅 Calendar is clear! No active loans to track.")
        return

    # 2. DATA PREPARATION (Standardizing)
    loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
    loans_df["Total_Repayable"] = pd.to_numeric(loans_df["Total_Repayable"], errors="coerce").fillna(0)
    today = pd.Timestamp.today().normalize()
    
    # Filter out Closed loans for the calendar
    active_loans = loans_df[loans_df["Status"] != "Closed"].copy()

    # ==============================
    # 🚀 DAILY WORKLOAD METRICS
    # ==============================
    due_today_df = active_loans[active_loans["End_Date"].dt.date == today.date()]
    upcoming_df = active_loans[
        (active_loans["End_Date"] > today) & 
        (active_loans["End_Date"] <= today + pd.Timedelta(days=7))
    ]
    overdue_count = active_loans[active_loans["End_Date"] < today].shape[0]

    m1, m2, m3 = st.columns(3)
    m1.metric("📌 Due Today", len(due_today_df))
    m2.metric("⏳ Next 7 Days", len(upcoming_df))
    m3.metric("🔴 Overdue Cases", overdue_count)

    st.markdown("---")

    # ==============================
    # 📌 SECTION: DUE TODAY
    # ==============================
    st.subheader("📌 Action Items for Today")
    if due_today_df.empty:
        st.success("No deadlines for today. Focus on follow-ups! ✨")
    else:
        # Display with Neon Styling
        st.warning(f"⚠️ You have {len(due_today_df)} collection(s) to finalize today.")
        st.dataframe(
            due_today_df[["Loan_ID", "Borrower", "Total_Repayable"]].assign(Action="💰 COLLECT NOW"),
            use_container_width=True, hide_index=True
        )

    # ==============================
    # ⏳ SECTION: UPCOMING
    # ==============================
    st.subheader("⏳ Upcoming Deadlines (Next 7 Days)")
    if upcoming_df.empty:
        st.info("The next few days look quiet.")
    else:
        upcoming_display = upcoming_df.sort_values("End_Date").copy()
        upcoming_display["Due_Date"] = upcoming_display["End_Date"].dt.strftime("%d %b (%a)")
        
        st.dataframe(
            upcoming_display[["Due_Date", "Borrower", "Total_Repayable", "Loan_ID"]],
            use_container_width=True, hide_index=True
        )

    # ==============================
    # 🔴 SECTION: IMMEDIATE FOLLOW-UP
    # ==============================
    st.subheader("🔴 Past Due (Immediate Attention)")
    overdue_df = active_loans[active_loans["End_Date"] < today].copy()
    
    if overdue_df.empty:
        st.success("Clean Sheet! No overdue loans found. 🎉")
    else:
        overdue_df["Days_Late"] = (today - overdue_df["End_Date"]).dt.days
        overdue_df = overdue_df.sort_values("Days_Late", ascending=False)
        
        # Color coding for gravity
        def color_late(val):
            return 'color: #FF4B4B; font-weight: bold;' if val > 7 else 'color: #FFA500;'
            
        st.dataframe(
            overdue_df[["Loan_ID", "Borrower", "Days_Late", "Status"]].style.applymap(color_late, subset=['Days_Late']),
            use_container_width=True, hide_index=True
        )
# ==============================
# 18. EXPENSE MANAGEMENT PAGE
# ==============================

def show_expenses():
    st.markdown("<h2 style='color: #2B3F87;'>📁 Expense Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA (Memory Shield)
    df = get_cached_data("Expenses")

    if df.empty:
        df = pd.DataFrame(columns=["Expense_ID", "Category", "Amount", "Date", "Description"])

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_add, tab_view, tab_manage = st.tabs(["➕ Record Expense", "📊 Spending Analysis", "⚙️ Manage/Delete"])

    # --- TAB 1: ADD NEW EXPENSE ---
    with tab_add:
        with st.form("add_expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            category = col1.selectbox("Category", ["Rent", "Transport", "Utilities", "Salaries", "Marketing", "Other"])
            amount = col2.number_input("Amount (UGX)", min_value=0, step=1000)
            desc = st.text_input("Description (e.g., Office Power Bill March)")
            
            if st.form_submit_button("🚀 Save Expense"):
                if amount > 0 and desc:
                    new_id = int(df["Expense_ID"].max() + 1) if not df.empty else 1
                    new_entry = pd.DataFrame([{
                        "Expense_ID": new_id,
                        "Category": category,
                        "Amount": amount,
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Description": desc
                    }])
                    
                    if save_data("Expenses", pd.concat([df, new_entry], ignore_index=True)):
                        st.success(f"Expense of {amount:,.0f} recorded! ✅")
                        st.rerun()
                else:
                    st.error("Please provide both an amount and a description.")

    # --- TAB 2: ANALYSIS & LOG ---
    with tab_view:
        if not df.empty:
            # Ensure Amount is numeric
            df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
            total_spent = df["Amount"].sum()
            
            st.metric("Total Monthly Outflow", f"{total_spent:,.0f} UGX")
            
            # Category Breakdown Chart
            cat_summary = df.groupby("Category")["Amount"].sum().reset_index()
            fig_exp = px.pie(cat_summary, names="Category", values="Amount", 
                             title="Spending by Category",
                             hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_exp, use_container_width=True)
            
            st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No expense data to analyze yet.")

    # --- TAB 3: MANAGE / EDIT / DELETE ---
    with tab_manage:
        if not df.empty:
            # Selection Logic
            edit_options = df.apply(lambda x: f"ID: {int(x['Expense_ID'])} | {x['Category']} - {x['Description']}", axis=1).tolist()
            selected_to_edit = st.selectbox("Select Expense to Modify", edit_options)
            
            e_id = int(selected_to_edit.split(" | ")[0].replace("ID: ", ""))
            e_row = df[df["Expense_ID"] == e_id].iloc[0]

            with st.container():
                c_a, c_b = st.columns(2)
                upd_cat = c_a.selectbox("Update Category", ["Rent", "Transport", "Utilities", "Salaries", "Marketing", "Other"],
                                        index=["Rent", "Transport", "Utilities", "Salaries", "Marketing", "Other"].index(e_row["Category"]))
                upd_amt = c_b.number_input("Update Amount (UGX)", value=float(e_row["Amount"]), step=1000.0)
                upd_desc = st.text_input("Update Description", value=e_row["Description"])

                btn1, btn2 = st.columns([1, 1])
                
                if btn1.button("Update Record ✅"):
                    df.loc[df["Expense_ID"] == e_id, ["Category", "Amount", "Description"]] = [upd_cat, upd_amt, upd_desc]
                    if save_data("Expenses", df):
                        st.success("Updated!")
                        st.rerun()

                if btn2.button("Delete Record 🗑️"):
                    df = df[df["Expense_ID"] != e_id]
                    if save_data("Expenses", df):
                        st.warning("Deleted!")
                        st.rerun()

# ==============================
# 19. PETTY CASH MANAGEMENT PAGE
# ==============================

def show_petty_cash():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Petty Cash Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA (Memory Shield)
    df = get_cached_data("PettyCash")

    if df.empty:
        df = pd.DataFrame(columns=["Transaction_ID", "Type", "Amount", "Date", "Description"])
    else:
        # Prevent formatting bugs
        df["Transaction_ID"] = pd.to_numeric(df["Transaction_ID"], errors='coerce').fillna(0).astype(int)
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # 2. SMART BALANCE METRICS
    inflow = df[df["Type"] == "In"]["Amount"].sum()
    outflow = df[df["Type"] == "Out"]["Amount"].sum()
    balance = inflow - outflow

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Cash In", f"{inflow:,.0f} UGX")
    m2.metric("Total Cash Out", f"{outflow:,.0f} UGX")
    
    # Delta shows red if balance is low (under 50k)
    m3.metric("Current Balance", f"{balance:,.0f} UGX", 
              delta="Low Balance" if balance < 50000 else "Healthy",
              delta_color="normal" if balance >= 50000 else "inverse")

    st.markdown("---")

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_record, tab_history = st.tabs(["➕ Record Entry", "📜 Transaction History"])

    # --- TAB 1: RECORD ENTRY ---
    with tab_record:
        with st.form("petty_cash_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            ttype = col_a.selectbox("Transaction Type", ["Out", "In"])
            t_amount = col_b.number_input("Amount (UGX)", min_value=0, step=1000)
            desc = st.text_input("Purpose / Description", placeholder="e.g., Office Water Refill")

            if st.form_submit_button("💾 Save to Cashbook"):
                if t_amount > 0 and desc:
                    new_id = int(df["Transaction_ID"].max() + 1) if not df.empty else 1
                    new_row = pd.DataFrame([{
                        "Transaction_ID": new_id,
                        "Type": ttype,
                        "Amount": t_amount,
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Description": desc
                    }])
                    
                    if save_data("PettyCash", pd.concat([df, new_row], ignore_index=True)):
                        st.success("Transaction Recorded!")
                        st.rerun()
                else:
                    st.error("Please provide amount and description.")

    # --- TAB 2: HISTORY & MANAGEMENT ---
    with tab_history:
        if not df.empty:
            # Color-coded display
            def color_type(val):
                return 'color: #10B981;' if val == 'In' else 'color: #FF4B4B;'
            
            st.dataframe(
                df.sort_values("Date", ascending=False).style.applymap(color_type, subset=['Type']),
                use_container_width=True, hide_index=True
            )

            # ADMIN ACTIONS (Edit/Delete)
            with st.expander("⚙️ Advanced: Edit or Delete Transaction"):
                # Create a list of options WITHOUT modifying the master dataframe
                options = [f"ID: {int(row['Transaction_ID'])} | {row['Type']} - {row['Description']}" for _, row in df.iterrows()]
                selected_task = st.selectbox("Select Entry", options)
                
                sel_id = int(selected_task.split(" | ")[0].replace("ID: ", ""))
                item = df[df["Transaction_ID"] == sel_id].iloc[0]

                up_type = st.selectbox("Update Type", ["In", "Out"], index=0 if item["Type"] == "In" else 1)
                up_amt = st.number_input("Update Amount", value=float(item["Amount"]), step=1000.0)
                up_desc = st.text_input("Update Description", value=item["Description"])

                c1, c2 = st.columns(2)
                if c1.button("Save Changes"):
                    df.loc[df["Transaction_ID"] == sel_id, ["Type", "Amount", "Description"]] = [up_type, up_amt, up_desc]
                    if save_data("PettyCash", df):
                        st.success("Updated!")
                        st.rerun()

                if c2.button("🗑️ Delete Permanently"):
                    df_new = df[df["Transaction_ID"] != sel_id]
                    if save_data("PettyCash", df_new):
                        st.warning("Entry Deleted.")
                        st.rerun()
        else:
            st.info("No transaction history available.")

# ==============================
# 20. PAYROLL MANAGEMENT PAGE
# ==============================

def show_payroll():
    # 1. SECURITY CHECK
    if st.session_state.get("role") != "Admin":
        st.error("🔒 Restricted Access: Only Admins can manage payroll.")
        return

    st.markdown("<h2 style='color: #2B3F87;'>🧾 Payroll Management</h2>", unsafe_allow_html=True)

    # 2. FETCH DATA (High Speed)
    df = get_cached_data("Payroll")

    if df.empty:
        df = pd.DataFrame(columns=["Payroll_ID", "Employee", "Salary", "Date", "Status"])
    else:
        df["Payroll_ID"] = pd.to_numeric(df["Payroll_ID"], errors='coerce').fillna(0).astype(int)
        df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce").fillna(0)

    # 3. MONTHLY METRICS
    total_staff_cost = df[df["Status"] == "Paid"]["Salary"].sum()
    staff_count = df["Employee"].nunique()

    m1, m2 = st.columns(2)
    m1.metric("Total Salaries Paid", f"{total_staff_cost:,.0f} UGX")
    m2.metric("Staff Count", staff_count)

    st.markdown("---")

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_process, tab_logs = st.tabs(["➕ Process Salary", "📜 Payroll History"])

    # --- TAB 1: PROCESS PAYMENT ---
    with tab_process:
        with st.form("process_payroll_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            name = col_a.text_input("Employee Name", placeholder="e.g., Namuli Sarah")
            salary = col_b.number_input("Amount (UGX)", min_value=0, step=50000)
            
            if st.form_submit_button("💳 Confirm & Release Payment"):
                if name and salary > 0:
                    new_pay_id = int(df["Payroll_ID"].max() + 1) if not df.empty else 1
                    new_pay_entry = pd.DataFrame([{
                        "Payroll_ID": new_pay_id,
                        "Employee": name,
                        "Salary": salary,
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Status": "Paid"
                    }])
                    
                    if save_data("Payroll", pd.concat([df, new_pay_entry], ignore_index=True)):
                        st.success(f"Salary payment for {name} successfully logged!")
                        st.rerun()
                else:
                    st.error("Please provide both name and salary amount.")

    # --- TAB 2: LOGS & MANAGEMENT ---
    with tab_logs:
        if not df.empty:
            # Table View
            st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)

            # ADMIN POP OVER (For Edits)
            with st.popover("⚙️ Modify or Void Payroll Entry"):
                # Human-friendly options without breaking the dataframe
                pay_options = [f"ID: {int(r['Payroll_ID'])} | {r['Employee']} ({r['Date']})" for _, r in df.iterrows()]
                selected_task = st.selectbox("Select Record", pay_options)
                
                sel_id = int(selected_task.split(" | ")[0].replace("ID: ", ""))
                item = df[df["Payroll_ID"] == sel_id].iloc[0]

                up_name = st.text_input("Edit Name", value=item["Employee"])
                up_salary = st.number_input("Edit Salary", value=float(item["Salary"]), step=10000.0)
                up_status = st.selectbox("Update Status", ["Paid", "Pending", "Void"], 
                                         index=["Paid", "Pending", "Void"].index(item["Status"]))

                c1, c2 = st.columns(2)
                if c1.button("Save Updates"):
                    df.loc[df["Payroll_ID"] == sel_id, ["Employee", "Salary", "Status"]] = [up_name, up_salary, up_status]
                    if save_data("Payroll", df):
                        st.success("Payroll Record Updated!")
                        st.rerun()

                if c2.button("🗑️ Delete Entry"):
                    df_new = df[df["Payroll_ID"] != sel_id]
                    if save_data("Payroll", df_new):
                        st.warning("Entry Removed.")
                        st.rerun()
        else:
            st.info("No payroll history found.")
        
    
 

# ==============================
# 21. ADVANCED ANALYTICS & REPORTS
# ==============================

def show_reports():
    st.markdown("<h2 style='color: #2B3F87;'>📊 Advanced Analytics & Reports</h2>", unsafe_allow_html=True)
    
    # 1. FETCH ALL DATA (Memory Shield)
    loans = get_cached_data("Loans")
    payments = get_cached_data("Payments")
    expenses = get_cached_data("Expenses")
    payroll = get_cached_data("Payroll")
    petty = get_cached_data("PettyCash")

    if loans.empty or payments.empty:
        st.info("📈 Not enough data yet. Once you record more loans and payments, your P&L will appear here.")
        return

    # 2. DATA CLEANING & CONVERSION (Atomic Mode)
    # We ensure everything is a float so math doesn't crash
    l_amt = pd.to_numeric(loans["Amount"], errors="coerce").fillna(0).sum()
    l_int = pd.to_numeric(loans["Interest"], errors="coerce").fillna(0).sum()
    
    p_amt = pd.to_numeric(payments["Amount"], errors="coerce").fillna(0).sum()
    
    # Combined Outflows
    exp_amt = pd.to_numeric(expenses["Amount"], errors="coerce").fillna(0).sum()
    pay_amt = pd.to_numeric(payroll["Salary"], errors="coerce").fillna(0).sum()
    petty_out = pd.to_numeric(petty[petty["Type"]=="Out"]["Amount"], errors="coerce").fillna(0).sum()
    
    total_outflow = exp_amt + pay_amt + petty_out
    net_profit = p_amt - total_outflow

    # 3. KPI DASHBOARD
    st.subheader("🚀 Financial Performance")
    k1, k2, k3, k4 = st.columns(4)
    
    k1.metric("Capital Issued", f"{l_amt:,.0f} UGX")
    k2.metric("Interest Accrued", f"{l_int:,.0f} UGX")
    k3.metric("Total Collections", f"{p_amt:,.0f} UGX")
    
    # Profit metric turns red if negative
    k4.metric("Net Profit (Actual)", f"{net_profit:,.0f} UGX", 
              delta=f"{(net_profit/l_amt)*100:.1f}% Yield" if l_amt > 0 else None,
              delta_color="normal" if net_profit > 0 else "inverse")

    st.markdown("---")

    # 4. VISUAL ANALYTICS
    col_left, col_right = st.columns(2)

    with col_left:
        st.write("**💰 Income vs. Expenses (Monthly)**")
        # Prepare Monthly Data
        payments["Date"] = pd.to_datetime(payments["Date"])
        expenses["Date"] = pd.to_datetime(expenses["Date"])
        
        inc_trend = payments.groupby(payments["Date"].dt.strftime('%Y-%m')).Amount.sum().reset_index()
        exp_trend = expenses.groupby(expenses["Date"].dt.strftime('%Y-%m')).Amount.sum().reset_index()
        
        merged = pd.merge(inc_trend, exp_trend, on="Date", how="outer", suffixes=('_Inc', '_Exp')).fillna(0)
        merged.columns = ["Month", "Income", "Expenses"]
        
        fig_bar = px.bar(merged, x="Month", y=["Income", "Expenses"], 
                         barmode="group",
                         color_discrete_map={"Income": "#00ffcc", "Expenses": "#FF4B4B"})
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.write("**🛡️ Portfolio Weight (Top 5)**")
        top_borrowers = loans.groupby("Borrower").Amount.sum().sort_values(ascending=False).head(5).reset_index()
        fig_pie = px.pie(top_borrowers, names="Borrower", values="Amount", hole=0.5,
                         color_discrete_sequence=px.colors.sequential.GnBu_r)
        st.plotly_chart(fig_pie, use_container_width=True)

    # 5. RISK INDICATOR
    st.markdown("---")
    st.subheader("🚨 Risk Assessment")
    
    overdue_val = loans[loans["Status"] == "Overdue"].Amount.sum()
    risk_percent = (overdue_val / l_amt * 100) if l_amt > 0 else 0
    
    r1, r2 = st.columns([2, 1])
    r1.write(f"Your Portfolio at Risk (PAR) is **{risk_percent:.1f}%**.")
    r1.progress(min(risk_percent / 100, 1.0))
    
    if risk_percent < 10:
        r2.success("✅ Healthy Portfolio")
    elif risk_percent < 25:
        r2.warning("⚠️ Moderate Risk")
    else:
        r2.error("🆘 Critical Risk Level")

# ==============================
# 22. MASTER LEDGER & STATEMENTS
# ==============================

def show_ledger():
    st.markdown("<h2 style='color: #2B3F87;'>📘 Master Ledger</h2>", unsafe_allow_html=True)
    
    loans_df = get_cached_data("Loans")
    payments_df = get_cached_data("Payments")

    if loans_df.empty:
        st.info("No loan records found to generate a ledger.")
        return

    # 1. Selection
    loan_options = loans_df.apply(lambda x: f"ID: {x['Loan_ID']} - {x['Borrower']}", axis=1).tolist()
    selected_loan = st.selectbox("Select Loan to View Full Statement", loan_options)
    l_id = int(selected_loan.split(" - ")[0].replace("ID: ", ""))
    
    # Get specific loan info
    loan_info = loans_df[loans_df["Loan_ID"] == l_id].iloc[0]
    
    # --- STYLED BALANCE CARD ---
    current_balance = float(loan_info["Total_Repayable"]) - float(loan_info["Amount_Paid"])
    
    st.markdown(f"""
        <div style="background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px;">
            <p style="margin:0; font-size:14px; color:#666; font-weight:bold;">CURRENT OUTSTANDING BALANCE (INC. INTEREST)</p>
            <h1 style="margin:0; color:#2B3F87;">{current_balance:,.0f} <span style="font-size:18px;">UGX</span></h1>
        </div>
    """, unsafe_allow_html=True)

    # 2. BUILD THE LEDGER TABLE
    ledger_data = []

    # --- ROW 1: THE DISBURSEMENT (Total Repayable) ---
    ledger_data.append({
        "Date": loan_info["Start_Date"],
        "Description": f"Initial Loan Disbursement (Principal + Interest)",
        "Debit": float(loan_info["Total_Repayable"]),
        "Credit": 0,
        "Balance": float(loan_info["Total_Repayable"])
    })

    # --- SUBSEQUENT ROWS: PAYMENTS ---
    relevant_payments = payments_df[payments_df["Loan_ID"] == l_id].sort_values("Date")
    running_balance = float(loan_info["Total_Repayable"])
    
    for _, pay in relevant_payments.iterrows():
        running_balance -= float(pay["Amount"])
        ledger_data.append({
            "Date": pay["Date"],
            "Description": f"Repayment ({pay['Method']})",
            "Debit": 0,
            "Credit": float(pay["Amount"]),
            "Balance": running_balance
        })

    ledger_df = pd.DataFrame(ledger_data)

    # 3. DISPLAY FORMATTED TABLE
    st.dataframe(
        ledger_df.style.format({
            "Debit": "{:,.0f}",
            "Credit": "{:,.0f}",
            "Balance": "{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.markdown("### 🚀 Generate Client Statement")
    
    # --- PDF GENERATION LOGIC ---
    if st.button("✨ Prepare Neon PDF Statement", use_container_width=True):
        st.write("Constructing PDF...")
        
        # This part assumes you have a function to generate the bytes
        # If not yet built, the download button below will wait for it
        try:
            # Placeholder for the actual PDF generation logic
            # pdf_bytes = generate_pdf(ledger_df, loan_info) 
            
            st.download_button(
                label="📥 Download & Send to Client",
                data=b"PDF Content Placeholder", # Replace with your pdf_bytes variable
                file_name=f"Zoe_Statement_{loan_info['Borrower']}_{l_id}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Could not generate PDF: {e}")

    


# ==============================
# 23. SYSTEM SETTINGS (Admin Only)
# ==============================

def show_settings():
    # 1. Access Control
    if st.session_state.get("role") != "Admin":
        st.error("🔒 Access Denied: System Settings are restricted to Administrators.")
        return

    st.markdown("<h2 style='color: #2B3F87;'>⚙️ System Settings</h2>", unsafe_allow_html=True)

    # --- BRANDING SECTION ---
    st.subheader("🖼️ Business Branding")
    
    # Use our cached get_logo from Piece 3 for speed
    current_logo = get_logo()
    
    col_logo, col_upload = st.columns([1, 2])
    
    with col_logo:
        if current_logo:
            st.image(f"data:image/png;base64,{current_logo}", width=120)
            st.caption("Active Logo")
        else:
            st.info("No logo set.")

    with col_upload:
        uploaded_logo = st.file_uploader("Upload New Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if st.button("🚀 Apply New Branding", use_container_width=True):
            if uploaded_logo:
                # Use the optimized save_logo_to_sheet from Piece 7
                if save_logo_to_sheet(uploaded_logo):
                    st.success("Logo updated and cache cleared! ✅")
                    st.rerun()
            else:
                st.warning("Select a file first.")

    st.markdown("---")

    # --- GENERAL CONFIGURATION ---
    # We fetch these from the 'Settings' sheet to pre-fill the form
    settings_df = get_cached_data("Settings")
    
    def get_setting_value(key, default):
        if not settings_df.empty and key in settings_df["Key"].values:
            return settings_df[settings_df["Key"] == key].iloc[0]["Value"]
        return default

    st.subheader("🛠️ Regional & Loan Defaults")
    c1, c2 = st.columns(2)
    
    biz_name = c1.text_input("Business Name", value=get_setting_value("biz_name", "Zoe Consults"))
    currency = c2.selectbox("System Currency", ["UGX", "USD", "KES"], index=0)
    def_interest = st.slider("Default Interest Rate (%)", 1, 50, int(get_setting_value("def_interest", 15)))

    if st.button("💾 Save Global Configuration"):
        # Create a settings update package
        new_settings = pd.DataFrame([
            {"Key": "biz_name", "Value": biz_name},
            {"Key": "currency", "Value": currency},
            {"Key": "def_interest", "Value": str(def_interest)},
            {"Key": "logo", "Value": current_logo} # Keep existing logo
        ])
        if save_data("Settings", new_settings):
            st.success("System configurations updated! ✅")
            st.rerun()

    st.markdown("---")

    # --- SYSTEM MAINTENANCE ---
    st.subheader("⚠️ System Maintenance")
    st.write("Use these tools if the data looks 'stuck' or old.")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button("🧹 Clear App Cache"):
            st.cache_data.clear()
            st.success("Cache wiped. Re-syncing with Google Sheets...")
            st.rerun()
            
    with col_b:
        # Emergency Log out for all sessions (clears local session state)
        if st.button("🚪 Hard Reset Session"):
            st.session_state.clear()
            st.rerun()


# ==============================
# THE MASTER MAIN LOOP
# ==============================

def main():
    # 1. First, check if the user is even logged in
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_page()  # Show ONLY the login page
        st.stop()     # Stop right here so the sidebar doesn't try to load
    
    # 2. If they ARE logged in, check for inactivity
    check_session_timeout()

    # 3. NOW, call the Sidebar (This makes it reappear!)
    sidebar()

    # 4. ROUTING: Show the page based on the sidebar selection
    page = st.session_state.get("page", "Overview")

    if page == "Overview":
        show_overview()
    elif page == "Borrowers":
        show_borrowers()
    elif page == "Loans":
        show_loans()
    elif page == "Payments":
        show_payments()
    elif page == "Collateral":
        show_collateral()
    elif page == "Ledger":
        show_ledger()
    elif page == "Calendar":
        show_calendar()
    elif page == "Overdue Tracker":
        show_overdue_tracker()
    elif page == "Expenses":
        show_expenses()
    elif page == "PettyCash":
        show_petty_cash()
    elif page == "Payroll":
        show_payroll()
    elif page == "Reports":
        show_reports()
    elif page == "Settings":
        show_settings()

# This is the "Ignition Switch" that starts the app
if __name__ == "__main__":
    main()





