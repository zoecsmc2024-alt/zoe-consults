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
# 1. DEFINE YOUR COLORS ONCE
BRANDING = {
    "navy": "#2B3F87",      # Primary Header / Buttons
    "baby_blue": "#F0F8FF", # Row Highlights / Hover
    "white": "#FFFFFF",     # Backgrounds
    "text_gray": "#666666"  # Captions / Timestamps
}

# 2. THE GLOBAL STYLER (Apply this at the start of main())
def apply_custom_styles():
    st.markdown(f"""
        <style>
            /* Sidebar Background */
            [data-testid="stSidebar"] {{
                background-color: {BRANDING['navy']};
            }}
            
            [data-testid="stSidebar"] * {{
                color: white !important;
            }}
            
            /* Active Tab Highlight */
            .st-bb {{ border-bottom-color: {BRANDING['navy']}; }}
            .st-at {{ background-color: {BRANDING['baby_blue']}; }}
            
            /* Buttons */
            .stButton>button {{
                background-color: {BRANDING['navy']};
                color: white;
                border-radius: 8px;
                border: none;
            }}
            .stButton>button:hover {{
                background-color: #1a285e;
                color: {BRANDING['baby_blue']};
            }}
        </style>
    """, unsafe_allow_html=True)

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

def create_pdf(html_content):
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)
    return pdf_buffer.getvalue()

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
    st.markdown("<h2 style='text-align: center; color: #000080;'>🔐 LOGIN</h2>", unsafe_allow_html=True)
    
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
st.set_page_config(page_title="Zoe Admin", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* 1. FORCE MAIN BACKGROUND */
    .stApp {
        background-color: #F0F8FF !important; /* Baby Blue */
    }

    /* 2. FORCE SIDEBAR NAVY */
    [data-testid="stSidebar"] {
        background-color: #2B3F87 !important;
    }
    [data-testid="stSidebar"] * {
        color: #F0F8FF !important;
    }

    /* 3. FORCE METRIC CARD COLORS */
    /* This targets the actual boxes you see on the Dashboard and Loans page */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #2B3F87 !important;
        border-left: 5px solid #2B3F87 !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 12px rgba(43, 63, 135, 0.1) !important;
    }
    
    /* Force the Metric Label (e.g., "PAID") to Gray */
    div[data-testid="stMetricLabel"] > div {
        color: #666666 !important;
        font-weight: bold !important;
    }
    
    /* Force the Metric Value (the amount) to Zoe Navy */
    div[data-testid="stMetricValue"] > div {
        color: #2B3F87 !important;
    }

    /* 1. COMPACT SIDEBAR BUTTONS */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        color: #F0F8FF !important; /* Baby Blue Text */
        border: 1px solid rgba(240, 248, 255, 0.1) !important;
        width: 100% !important;
        text-align: left !important;
        padding: 6px 12px !important; /* REDUCED PADDING to stop scrolling */
        margin-bottom: 2px !important; /* Tighter spacing */
        border-radius: 6px !important;
        font-size: 14px !important; /* Slightly smaller text for fit */
        transition: all 0.2s ease !important;
    }

    /* 1. THE ULTIMATE CLICK FIX */
    section[data-testid="stSidebar"] .stButton > button:focus,
    section[data-testid="stSidebar"] .stButton > button:active,
    section[data-testid="stSidebar"] .stButton > button:focus-visible,
    section[data-testid="stSidebar"] .stButton > button:focus:not(:active) {
        background-color: #F0F8FF !important; /* Force Baby Blue on click */
        color: #2B3F87 !important;            /* Force Navy Text on click */
        border: 1px solid #F0F8FF !important;
        box-shadow: none !important;          /* Removes the glowy white outline */
        outline: none !important;             /* Removes the browser focus ring */
    }

    /* 2. MAKE BUTTONS SLIMMER (SAVE SPACE) */
    section[data-testid="stSidebar"] .stButton > button {
        padding: 4px 10px !important;         /* Extra slim padding */
        min-height: 35px !important;          /* Force buttons to be shorter */
        margin-top: -5px !important;          /* Pull them closer together */
    }

    /* THE ACTIVE TAB FIX - This makes the current page look 'Pressed' */
    .active-menu-item {
        background-color: #F0F8FF !important;
        color: #2B3F87 !important;
        padding: 10px 15px !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        margin-bottom: 5px !important;
        display: flex !important;
        align-items: center !important;
    }

    /* 5. DATA FRAME / TABLE HEADERS */
    /* This tries to force standard Streamlit tables to look Navy */
    thead tr th {
        background-color: #2B3F87 !important;
        color: white !important;
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

    # 1. THE LOGO LOADER
    logo_base64 = get_logo() 
    
    if logo_base64:
        img_src = f"data:image/png;base64,{logo_base64}"
        st.sidebar.markdown(f"""
            <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                <div style="width: 85px; height: 85px; border-radius: 50%; overflow: hidden; 
                            border: 3px solid #F0F8FF; box-shadow: 0px 0px 15px rgba(240, 248, 255, 0.3);">
                    <img src="{img_src}" style="width: 100%; height: 100%; object-fit: cover;">
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # 2. BRANDING & USER INFO (Updated to Navy/Baby Blue)
    st.sidebar.markdown(f"""
        <div style="text-align: center;">
            <h2 style="color: #FFFFFF; margin-bottom: 0;">ZOE CONSULTS</h2>
            <div style="color: #F0F8FF; font-size: 12px; margin-top: 5px;">
                <span style="height: 8px; width: 8px; background-color: #00ffcc; border-radius: 50%; display: inline-block; margin-right: 5px;"></span> System Online
            </div>
            <p style='color:#F0F8FF; font-size:14px; margin-top:10px; opacity: 0.9;'>
                👤 <b>{user}</b> <span style='font-size: 12px;'>({role})</span>
            </p>
        </div>
        <hr style='border-top: 1px solid rgba(255,255,255,0.2); margin: 20px 0;'>
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

        else:
            # Clean Button Navigation with 'Secondary' type for transparency
            if st.sidebar.button(f"{icon} {item}", key=f"nav_{item}", use_container_width=True, type="secondary"):
                st.session_state.page = item
                st.rerun()

    # 4. LOGOUT (Clean & Simple)
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==============================
# 11. DASHBOARD LOGIC (OVERVIEW)
# ==============================

def show_overview():
    st.markdown("<h2 style='color: #4A90E2;'>📊 Financial Dashboard</h2>", unsafe_allow_html=True)
    
    # 1. LOAD PRIMARY DATA
    df = get_cached_data("Loans")
    pay_df = get_cached_data("Payments")
    exp_df = get_cached_data("Expenses")

    if df is None or df.empty:
        st.warning("⚠️ No data found in 'Loans'. Add some borrowers to get started!")
        return

    # 2. DATA CLEANING
    # Updated Line 553
    # We search for Principal because that's our new header!
    df["Principal"] = pd.to_numeric(df.get("Principal", 0), errors="coerce").fillna(0)
    df["Interest"] = pd.to_numeric(df["Interest"], errors="coerce").fillna(0)
    df["Amount_Paid"] = pd.to_numeric(df["Amount_Paid"], errors="coerce").fillna(0)
    df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
    
    today = pd.Timestamp.today().normalize()
    
    # RECOVERY FILTER: Include Rolled loans in Active count
    active_statuses = ["Active", "Overdue", "Rolled/Overdue"]
    active_df = df[df["Status"].isin(active_statuses)].copy()


    # 3. METRICS CALCULATION
    total_issued = active_df["Principal"].sum() if "Principal" in active_df.columns else 0
    total_interest_expected = active_df["Interest"].sum()
    total_collected = df["Amount_Paid"].sum() 
    
    overdue_mask = (active_df["End_Date"] < today) & (active_df["Status"] != "Cleared")
    overdue_count = active_df[overdue_mask].shape[0]

    
    # 4. METRICS ROW (Zoe Soft Blue Style)
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">💰 ACTIVE PRINCIPAL</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{total_issued:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
    m2.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">📈 EXPECTED INTEREST</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{total_interest_expected:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
    m3.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #2E7D32;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">✅ TOTAL COLLECTED</p><h3 style="margin:0;color:#2E7D32;font-size:18px;">{total_collected:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
    m4.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #FF4B4B;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">🚨 OVERDUE FILES</p><h3 style="margin:0;color:#FF4B4B;font-size:18px;">{overdue_count}</h3></div>""", unsafe_allow_html=True)

    # 5. RECENT ACTIVITY TABLES
    st.write("---")
    t1, t2 = st.columns(2)

    with t1:
        st.markdown("<h4 style='color: #4A90E2;'>📝 Recent Portfolio Activity</h4>", unsafe_allow_html=True)
        # We define rows_html once and then fill it
        rows_html = ""
        
        if not active_df.empty:
            # We take the 5 most recent based on End_Date
            recent_loans = active_df.sort_values(by="End_Date", ascending=False).head(5)
            
            for i, (idx, r) in enumerate(recent_loans.iterrows()):
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                
                # SAFE GET: prevents KeyError
                b_name = r.get('Borrower', 'Unknown')
                p_amt = float(r.get('Principal', 0))
                b_stat = r.get('Status', 'Active')
                e_date = pd.to_datetime(r.get('End_Date')).strftime('%d %b') if r.get('End_Date') else "-"

                rows_html += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                    <td style="padding:10px;">{b_name}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:#4A90E2;">{p_amt:,.0f}</td>
                    <td style="padding:10px; text-align:center;"><span style="font-size:10px; background:#e1f5fe; padding:2px 5px; border-radius:5px;">{b_stat}</span></td>
                    <td style="padding:10px; text-align:center; color:#666;">{e_date}</td>
                </tr>"""
        
        st.markdown(f"""
            <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px; border: 1px solid #4A90E2;">
                <thead>
                    <tr style="background:#4A90E2; color:white;">
                        <th style="padding:10px;">Borrower</th>
                        <th style="padding:10px; text-align:right;">Principal</th>
                        <th style="padding:10px; text-align:center;">Status</th>
                        <th style="padding:10px; text-align:center;">Due</th>
                    </tr>
                </thead>
                <tbody>{rows_html if rows_html else "<tr><td colspan='4' style='text-align:center;padding:10px;'>No active loans</td></tr>"}</tbody>
            </table>
        """, unsafe_allow_html=True)

    with t2:
        st.markdown("<h4 style='color: #2E7D32;'>💸 Recent Cash Inflows</h4>", unsafe_allow_html=True)
        pay_rows = ""
        
        if pay_df is not None and not pay_df.empty:
            recent_pay = pay_df.sort_values(by="Date", ascending=False).head(5)
            for i, (idx, r) in enumerate(recent_pay.iterrows()):
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                p_borr = r.get('Borrower', 'Unknown')
                p_val = float(r.get('Amount', 0))
                p_date = pd.to_datetime(r.get('Date')).strftime('%d %b') if r.get('Date') else "-"
                
                pay_rows += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                    <td style="padding:10px;">{p_borr}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:green;">{p_val:,.0f}</td>
                    <td style="padding:10px; text-align:center; color:#666;">{p_date}</td>
                </tr>"""
        
        st.markdown(f"""
            <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px; border: 1px solid #2E7D32;">
                <thead>
                    <tr style="background:#2E7D32; color:white;">
                        <th style="padding:10px;">Borrower</th>
                        <th style="padding:10px; text-align:right;">Amount</th>
                        <th style="padding:10px; text-align:center;">Date</th>
                    </tr>
                </thead>
                <tbody>{pay_rows if pay_rows else "<tr><td colspan='3' style='text-align:center;padding:10px;'>No recent payments</td></tr>"}</tbody>
            </table>
        """, unsafe_allow_html=True)
    # 6. DASHBOARD VISUALS
    st.markdown("---")
    st.markdown("<h4 style='color: #4A90E2;'>📈 Portfolio Analytics</h4>", unsafe_allow_html=True)
    c_pie, c_bar = st.columns(2)

    with c_pie:
        status_counts = df["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_pie = px.pie(status_counts, names="Status", values="Count", hole=0.5, title="Loan Distribution", color_discrete_sequence=["#4A90E2", "#FF4B4B", "#FFA500"])
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="#2B3F87", margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    with c_bar:
        if not pay_df.empty and not exp_df.empty:
            pay_df["Date"] = pd.to_datetime(pay_df["Date"])
            exp_df["Date"] = pd.to_datetime(exp_df["Date"])
            inc_m = pay_df.groupby(pay_df["Date"].dt.strftime('%b %Y'))["Amount"].sum().reset_index()
            exp_m = exp_df.groupby(exp_df["Date"].dt.strftime('%b %Y'))["Amount"].sum().reset_index()
            m_cash = pd.merge(inc_m, exp_m, on="Date", how="outer", suffixes=('_Inc', '_Exp')).fillna(0)
            m_cash.columns = ["Month", "Income", "Expenses"]
            fig_bar = px.bar(m_cash, x="Month", y=["Income", "Expenses"], barmode="group", title="Performance", color_discrete_map={"Income": "#2E7D32", "Expenses": "#FF4B4B"})
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#2B3F87")
            st.plotly_chart(fig_bar, use_container_width=True)

# ==============================
# 12. BORROWERS MANAGEMENT PAGE
# ==============================

def show_borrowers():
    # Primary Header in Soft Blue
    st.markdown("<h2 style='color: #4A90E2;'>👥 Borrowers Management</h2>", unsafe_allow_html=True)

    # 1. LOAD DATA
    df = get_cached_data("Borrowers")
    loans_df = get_cached_data("Loans") 

    if df.empty:
        df = pd.DataFrame(columns=["Borrower_ID", "Name", "Phone", "Email", "National_ID", "Address", "Next_of_Kin", "Status", "Date_Added"])

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_list, tab_add, tab_manage = st.tabs(["📋 View All", "➕ Add New", "⚙️ Audit Portfolio"])

    # --- TAB 1: SEARCH & LIST (Soft Blue Table) ---
    with tab_list:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        search = col1.text_input("🔍 Search Name or Phone")
        status_filter = col2.selectbox("Filter Status", ["All", "Active", "Inactive"])

        filtered_df = df.copy()
        if search:
            filtered_df = filtered_df[
                filtered_df["Name"].str.contains(search, case=False, na=False) |
                filtered_df["Phone"].str.contains(search, case=False, na=False)
            ]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df["Status"] == status_filter]

        if not filtered_df.empty:
            rows_html = ""
            for i, r in filtered_df.iterrows():
                bg_color = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                rows_html += f"""
                <tr style="background-color: {bg_color}; border-bottom: 1px solid #ddd;">
                    <td style="padding:12px;"><b>{r['Name']}</b></td>
                    <td style="padding:12px;">{r['Phone']}</td>
                    <td style="padding:12px; font-size: 11px; color:#666;">{r.get('National_ID', 'N/A')}</td>
                    <td style="padding:12px; text-align:center;">
                        <span style="background:#4A90E2; color:white; padding:3px 8px; border-radius:12px; font-size:10px;">
                            {r['Status']}
                        </span>
                    </td>
                </tr>"""

            st.markdown(f"""
                <div style="border:2px solid #4A90E2; border-radius:10px; overflow:hidden; margin-top:20px;">
                    <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:13px;">
                        <thead>
                            <tr style="background:#4A90E2; color:white; text-align:left;">
                                <th style="padding:12px;">Borrower Name</th>
                                <th style="padding:12px;">Phone</th>
                                <th style="padding:12px;">National ID</th>
                                <th style="padding:12px; text-align:center;">Status</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No borrowers found.")

    # --- TAB 2: ADD BORROWER ---
    with tab_add:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("add_borrower_form", clear_on_submit=True):
            st.markdown("<h4 style='color: #4A90E2;'>📝 Register New Borrower</h4>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name*")
            phone = c2.text_input("Phone Number*")
            email = c1.text_input("Email Address")
            kin = c2.text_input("Next of Kin")
            nid = c1.text_input("National ID / NIN")
            addr = c2.text_input("Physical Address")
            
            if st.form_submit_button("🚀 Save Borrower Profile", use_container_width=True):
                if name and phone:
                    new_id = int(df["Borrower_ID"].max() + 1) if not df.empty else 1
                    new_entry = pd.DataFrame([{
                        "Borrower_ID": new_id, "Name": name, "Phone": phone,
                        "Email": email, "National_ID": nid, "Address": addr, 
                        "Next_of_Kin": kin, "Status": "Active",
                        "Date_Added": datetime.now().strftime("%Y-%m-%d")
                    }])
                    if save_data("Borrowers", pd.concat([df, new_entry], ignore_index=True)):
                        st.success(f"✅ {name} registered!"); st.rerun()
                else:
                    st.error("⚠️ Required: Name and Phone Number.")

    # --- TAB 3: AUDIT PORTFOLIO (Safety Sync) ---
    with tab_manage:
        if not df.empty:
            target_name = st.selectbox("Select Borrower to Audit", df["Name"].tolist())
            b_data = df[df["Name"] == target_name].iloc[0]
            
            st.markdown(f"""
                <div style="background-color: #F0F8FF; padding: 15px; border-radius: 10px; border-left: 5px solid #4A90E2;">
                    <p style="margin:0; color:#2B3F87;"><b>📍 Address:</b> {b_data.get('Address', 'N/A')} | <b>📞 Kin:</b> {b_data.get('Next_of_Kin', 'N/A')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # THE FIX: Ensure we find ALL active/overdue/rolled loans for this person
            user_loans = loans_df[loans_df["Borrower"] == target_name].copy()
            
            if not user_loans.empty:
                for col in ['Amount_Paid', 'Total_Repayable', 'Amount']:
                    user_loans[col] = pd.to_numeric(user_loans[col], errors='coerce').fillna(0)
                
                total_remaining = user_loans['Total_Repayable'].sum() - user_loans['Amount_Paid'].sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Loans", len(user_loans))
                # Count both standard and Rolled/Overdue
                active_count = user_loans[user_loans["Status"].isin(["Active", "Overdue", "Rolled/Overdue"])].shape[0]
                m2.metric("Active/Rolled", active_count)
                m3.markdown(f"<div style='text-align:center;'><p style='margin:0;font-size:12px;color:#666;font-weight:bold;'>TOTAL BALANCE</p><h3 style='color:#FF4B4B;margin:0;'>{total_remaining:,.0f}</h3></div>", unsafe_allow_html=True)

                # History Table
                history_rows = ""
                for i, row in user_loans.iterrows():
                    bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                    stat_c = "#4A90E2" if row['Status'] in ["Active", "Rolled/Overdue"] else "#FF4B4B" if row['Status'] == "Overdue" else "#666"
                    history_rows += f"""
                    <tr style="background-color: {bg};">
                        <td style="padding:10px;">#{row['Loan_ID']}</td>
                        <td style="padding:10px; font-weight:bold; color:#2B3F87;">{row['Amount']:,.0f}</td>
                        <td style="padding:10px; text-align:center;"><span style="background:{stat_c}; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{row['Status']}</span></td>
                        <td style="padding:10px; text-align:right;">{pd.to_datetime(row['End_Date']).strftime('%d %b %Y')}</td>
                    </tr>"""
                
                st.markdown(f"""
                    <div style='border:1px solid #4A90E2; border-radius:8px; overflow:hidden; margin-top:15px;'>
                        <table style='width:100%; font-size:12px; border-collapse:collapse;'>
                            <tr style='background:#4A90E2; color:white;'>
                                <th style='padding:10px; text-align:left;'>ID</th>
                                <th style='padding:10px; text-align:left;'>Principal</th>
                                <th style='padding:10px; text-align:center;'>Status</th>
                                <th style='padding:10px; text-align:right;'>Due Date</th>
                            </tr>
                            {history_rows}
                        </table>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("ℹ️ No loan history for this borrower.")





# ==============================
# 13. LOANS MANAGEMENT PAGE
# ==============================

def show_loans():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Loans Management</h2>", unsafe_allow_html=True)
    
    # 1. LOAD DATA
    borrowers_df = get_cached_data("Borrowers")
    loans_df = get_cached_data("Loans")

    if borrowers_df.empty:
        st.warning("⚠️ No borrowers found. Register a client in the Borrowers tab first!")
        return
        
    active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]

    # --- TABBED INTERFACE ---
    tab_issue, tab_view, tab_manage = st.tabs(["➕ Issue Loan", "📊 Portfolio", "⚙️ Manage Loans"])

    # ==============================
    # TAB 1: ISSUE LOAN (Branded Form)
    # ==============================
    with tab_issue:
        if active_borrowers.empty:
            st.info("💡 Tip: Activate a borrower to issue a loan.")
        else:
            with st.form("loan_issue_form"):
                st.markdown("<h4 style='color: #2B3F87;'>📝 Create New Loan Agreement</h4>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                selected_borrower = col1.selectbox("Select Borrower", active_borrowers["Name"].unique())
                amount = col1.number_input("Principal Amount (UGX)", min_value=0, step=50000)
                date_issued = col1.date_input("Date Issued", value=datetime.now())
                
                l_type = col2.selectbox("Loan Type", ["Business", "Personal", "Emergency", "Other"])
                interest_rate = col2.number_input("Monthly Interest Rate (%)", min_value=0.0, step=0.5)
                date_due = col2.date_input("Due Date", value=date_issued + timedelta(days=30))

                # Math Preview
                interest = (interest_rate / 100) * amount
                total_due = amount + interest
                
                st.markdown(f"""
                    <div style="background-color: #F0F8FF; padding: 10px; border-radius: 8px; border-left: 5px solid #2B3F87;">
                        <p style="margin:0; color:#2B3F87;"><b>Summary:</b> Total Repayable Amount will be <b>{total_due:,.0f} UGX</b></p>
                    </div>
                """, unsafe_allow_html=True)

                st.write("")
                if st.form_submit_button("🚀 Confirm & Issue Loan", use_container_width=True):
                    if amount > 0:
                        last_id = loans_df["Loan_ID"].max()
                        new_id = int(last_id + 1) if pd.notna(last_id) else 1
                        
                        safe_interest = float(interest) if pd.notna(interest) else 0.0
                        safe_total = float(total_due) if pd.notna(total_due) else float(amount)

                        # --- CORRECTED INDENTATION BELOW ---
                        new_loan = pd.DataFrame([{
                            "Loan_ID": new_id, 
                            "Borrower": selected_borrower, 
                            "Type": l_type,
                            "Principal": float(amount),  # Matched to your Google Sheet header
                            "Interest_Rate": float(interest_rate),
                            "Interest": safe_interest,
                            "Total_Repayable": safe_total, 
                            "Amount_Paid": 0.0,
                            "Start_Date": date_issued.strftime("%Y-%m-%d"),
                            "End_Date": date_due.strftime("%Y-%m-%d"),
                            "Status": "Active"
                        }])
                        
                        updated_df = pd.concat([loans_df, new_loan], ignore_index=True).fillna(0)
                        
                        if save_data("Loans", updated_df):
                            st.success(f"✅ Loan #{new_id} successfully issued to {selected_borrower}!")
                            st.rerun()

    # ==============================
    # TAB 2: PORTFOLIO INSPECTOR (Zoe Soft Blue)
    # ==============================
    with tab_view:
        if not loans_df.empty:
            # Create a fresh copy to work with
            display_df = loans_df.copy()
            
            # 1. CLEAN DATA TYPES IMMEDIATELY
            for col in ["Principal", "Amount", "Interest", "Amount_Paid", "Interest_Rate"]:
                if col in display_df.columns:
                    display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
                else:
                    display_df[col] = 0.0

            # 2. STATUS FILTERING
            display_df["Status"] = display_df["Status"].astype(str).str.strip()
            display_df["Loan_ID"] = display_df["Loan_ID"].astype(str)
            relevant_statuses = ["Active", "Overdue", "Rolled/Overdue"]
            display_df = display_df[display_df["Status"].isin(relevant_statuses)].copy()

            if display_df.empty:
                st.info("ℹ️ No active loans found.")
            else:
                # 3. METRIC CALCULATIONS
                actual_p = display_df["Principal"] if "Principal" in display_df.columns else display_df["Amount"]
                display_df["Total_Repayable"] = actual_p + display_df["Interest"]
                display_df["Outstanding_Balance"] = display_df["Total_Repayable"] - display_df["Amount_Paid"]
                
                sel_id = st.selectbox("🔍 Select Loan to Inspect", display_df["Loan_ID"].unique())
                loan_info = display_df[display_df["Loan_ID"] == sel_id].iloc[0]
                
                # --- METRIC CARDS (Updated for Principal) ---
                p1, p2, p3 = st.columns(3)
                p1.markdown(f"""<div style="background-color:#F0F8FF;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">RECEIVED</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{loan_info.get('Amount_Paid', 0):,.0f} UGX</h3></div>""", unsafe_allow_html=True)
                p2.markdown(f"""<div style="background-color:#ffffff;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">OUTSTANDING</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{loan_info.get('Outstanding_Balance', 0):,.0f} UGX</h3></div>""", unsafe_allow_html=True)
                s_color = "#4A90E2" if loan_info.get('Status') != "Overdue" else "#FF4B4B"
                p3.markdown(f"""<div style="background-color:#ffffff;padding:20px;border-radius:15px;border-left:5px solid {s_color};box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">STATUS</p><h3 style="margin:0;color:{s_color};font-size:18px;">{str(loan_info.get('Status', 'ACTIVE')).upper()}</h3></div>""", unsafe_allow_html=True)

                # --- THE COMPLETE "ZOE" PORTFOLIO TABLE (RESTORING ALL COLUMNS) ---
                rows_html = ""
                for i, r in display_df.iterrows():
                    bg_color = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                    stat_bg = "#4A90E2" if r.get('Status') == "Active" else "#FF4B4B" if r.get('Status') == "Overdue" else "#FFA500"

                    # 1. Fetch dates safely (Checking all possible names)
                    s_date_raw = r.get('Start_Date') or r.get('Issued On') or r.get('Date')
                    start_date = pd.to_datetime(s_date_raw).strftime('%d %b %y') if pd.notna(s_date_raw) else "-"
                    
                    e_date_raw = r.get('End_Date') or r.get('Due Date')
                    end_date = pd.to_datetime(e_date_raw).strftime('%d %b %y') if pd.notna(e_date_raw) else "-"
                    
                    # 2. Last Rolled Date logic
                    roll_date = r.get('Rollover_Date', '-')
                    if roll_date and roll_date != '-':
                        try: roll_date = pd.to_datetime(roll_date).strftime('%d %b')
                        except: pass

                    # 3. Principal & Rate Recovery (Checking new Principal header)
                    p_val = float(r.get('Principal', 0)) if float(r.get('Principal', 0)) > 0 else float(r.get('Amount', 0))
                    
                    raw_rate = float(r.get('Interest_Rate', 0))
                    if raw_rate == 0 and p_val > 0:
                        calculated_rate = (float(r.get('Interest', 0)) / p_val) * 100
                    else:
                        calculated_rate = raw_rate

                    rows_html += f"""
                    <tr style="background-color: {bg_color}; border-bottom: 1px solid #ddd;">
                        <td style="padding:10px;"><b>#{r.get('Loan_ID', '0')}</b></td>
                        <td style="padding:10px;">{r.get('Borrower', 'Unknown')}</td>
                        <td style="padding:10px; text-align:center; color:#666;">{start_date}</td>
                        <td style="padding:10px; text-align:right; font-weight:bold; color:#4A90E2;">{p_val:,.0f}</td>
                        <td style="padding:10px; text-align:center; color:#2B3F87; font-weight:bold;">{calculated_rate:.1f}%</td>
                        <td style="padding:10px; text-align:right; color:#D32F2F;">{float(r.get('Outstanding_Balance', 0)):,.0f}</td>
                        <td style="padding:10px; text-align:center;">
                            <span style="background:{stat_bg}; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r.get('Status', 'Active')}</span>
                        </td>
                        <td style="padding:10px; text-align:center; font-size:11px; color:#666;">{roll_date}</td>
                        <td style="padding:10px; text-align:center; font-size:11px; font-weight:bold; color:#2B3F87;">{end_date}</td>
                    </tr>"""

                final_table_html = f"""
                <div style="border:2px solid #4A90E2; border-radius:10px; overflow:hidden; background:white;">
                    <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
                        <thead>
                            <tr style="background:#4A90E2; color:white;">
                                <th style="padding:12px;">ID</th>
                                <th style="padding:12px;">Borrower</th>
                                <th style="padding:12px; text-align:center;">Issued On</th>
                                <th style="padding:12px; text-align:right;">Principal</th>
                                <th style="padding:12px; text-align:center;">Rate (%)</th>
                                <th style="padding:12px; text-align:right;">Balance</th>
                                <th style="padding:12px; text-align:center;">Status</th>
                                <th style="padding:12px; text-align:center;">Last Rolled</th>
                                <th style="padding:12px; text-align:center;">Due Date</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>"""
                
                st.components.v1.html(final_table_html, height=600, scrolling=True)
            

    # ==============================
    # TAB 3: MANAGE (Zoe Settings)
    # ==============================
    with tab_manage:
        if not loans_df.empty:
            st.markdown("<h4 style='color: #2B3F87;'>🛠️ Modify Loan Agreement</h4>", unsafe_allow_html=True)
            
            # 1. Selection List (Using Principal)
            manage_list = loans_df.apply(lambda x: f"ID: {x.get('Loan_ID', 'N/A')} | {x.get('Borrower', 'Unknown')} - {float(x.get('Principal', 0)):,.0f} UGX", axis=1).tolist()
            selected_manage = st.selectbox("Search and Select Loan ID", manage_list)
            m_id = int(selected_manage.split(" | ")[0].replace("ID: ", ""))
            m_row = loans_df[loans_df["Loan_ID"] == m_id].iloc[0]

            with st.container():
                col_e1, col_e2 = st.columns(2)
                
                # 2. Left Column Adjustments
                upd_amt = col_e1.number_input("Adjust Principal", value=float(m_row.get("Principal", 0)), step=10000.0)
                
                # Dynamic Rate Recovery
                try: 
                    curr_rate = (float(m_row.get("Interest", 0)) / float(m_row.get("Principal", 1))) * 100 
                except: 
                    curr_rate = 0.0
                
                upd_rate = col_e1.number_input("Adjust Rate (%)", value=float(curr_rate), step=0.5)
                upd_paid = col_e1.number_input("Adjust Total Paid", value=float(m_row.get("Amount_Paid", 0)))

                # 3. Right Column Adjustments
                upd_stat = col_e2.selectbox("Change Status", ["Active", "Overdue", "Closed", "Rolled/Overdue"], 
                                           index=["Active", "Overdue", "Closed", "Rolled/Overdue"].index(m_row.get("Status", "Active")))
                
                loan_types = ["Business", "Personal", "Emergency", "Other"]
                current_type = str(m_row.get("Type", "Business"))
                if current_type not in loan_types: current_type = "Business"
                upd_type = col_e2.selectbox("Change Type", loan_types, index=loan_types.index(current_type))
                
                # 4. Date Adjustments (Indented properly)
                raw_start = m_row.get("Start_Date", datetime.now().strftime("%Y-%m-%d"))
                try:
                    val_start = pd.to_datetime(raw_start).date()
                except:
                    val_start = datetime.now().date()

                upd_start = col_e2.date_input("Adjust Start Date", value=val_start)
                
                # End Date Safety
                try:
                    val_end = pd.to_datetime(m_row.get("End_Date")).date()
                except:
                    val_end = datetime.now().date()
                upd_end = col_e2.date_input("Adjust End Date", value=val_end)

                # 5. Save & Delete Buttons
                b_upd, b_del = st.columns(2)
                
                if b_upd.button("💾 Save Changes", use_container_width=True):
                    new_int = upd_amt * (upd_rate / 100)
                    # We map exactly to your NEW Google Sheet headers here
                    loans_df.loc[loans_df["Loan_ID"] == m_id, ["Principal", "Amount_Paid", "Status", "Start_Date", "End_Date", "Interest", "Total_Repayable", "Type", "Interest_Rate"]] = \
                        [upd_amt, upd_paid, upd_stat, upd_start.strftime("%Y-%m-%d"), upd_end.strftime("%Y-%m-%d"), new_int, (upd_amt + new_int), upd_type, upd_rate]
                    
                    if save_data("Loans", loans_df):
                        st.success("Loan records updated!")
                        st.rerun()

                if b_del.button("🗑️ Delete Permanently", use_container_width=True):
                    if save_data("Loans", loans_df[loans_df["Loan_ID"] != m_id]):
                        st.warning("Loan record deleted!")
                        st.rerun()
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
        # Use lowercase for status check to be safe
        active_loans = loans_df[loans_df["Status"].astype(str).str.lower() != "closed"]
        
        if active_loans.empty:
            st.success("🎉 All loans are currently cleared!")
        else:
            # 1. Selection logic
            loan_options = active_loans.apply(lambda x: f"ID: {x.get('Loan_ID', 'N/A')} - {x.get('Borrower', 'Unknown')}", axis=1).tolist()
            selected_option = st.selectbox("Select Loan to Credit", loan_options)
            selected_id = int(selected_option.split(" - ")[0].replace("ID: ", ""))
            loan = active_loans[active_loans["Loan_ID"] == selected_id].iloc[0]

            # 2. Calculation (Properly Indented)
            # Safe recovery: Total Repayable or (Principal + Interest)
            total_rep = float(loan.get("Total_Repayable", 0))
            if total_rep == 0:
                total_rep = float(loan.get("Principal", 0)) + float(loan.get("Interest", 0))

            # Convert to numeric safely
            total_rep = pd.to_numeric(total_rep, errors='coerce')
            paid_so_far = pd.to_numeric(loan.get("Amount_Paid", 0), errors='coerce')
            outstanding = total_rep - paid_so_far

            # --- STYLED CARDS (Continue here) ---
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
    # TAB 2: HISTORY (Color via Emojis)
    # ==============================
    with tab_history:
        if not payments_df.empty:
            # 1. Clean the data
            df_display = payments_df.copy()
            df_display["Amount"] = pd.to_numeric(df_display.get("Amount", 0), errors="coerce").fillna(0)
            
            # 2. Add a "Trend" Emoji Column based on Amount
            def get_color_emoji(amt):
                if amt >= 5000000: return "🟢 Large"  # Over 5M
                if amt >= 1000000: return "🔵 Medium" # Over 1M
                return "⚪ Small"
            
            df_display["Level"] = df_display["Amount"].apply(get_color_emoji)
            
            # 3. Sort by Date
            df_display = df_display.sort_values("Date", ascending=False)

            # 4. Reorder columns to put the "Level" first for visual impact
            cols = ["Level"] + [c for c in df_display.columns if c != "Level"]
            
            # 5. Display (Safe version, no .style)
            st.dataframe(
                df_display[cols], 
                use_container_width=True, 
                hide_index=True
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
    loans_df = get_cached_data("Loans") 
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
            active_loan_mask = loans_df["Status"].isin(["Active", "Overdue", "Rolled/Overdue"])
            available_loans = loans_df[active_loan_mask]

            if available_loans.empty:
                st.info("✅ All current loans are cleared. No assets need to be held.")
            else:
                with st.form("collateral_form", clear_on_submit=True):
                    st.markdown("<h4 style='color: #2B3F87;'>🔒 Secure New Asset</h4>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    
                    loan_options = available_loans.apply(lambda x: f"ID: {x['Loan_ID']} - {x['Borrower']}", axis=1).tolist()
                    selected_loan = c1.selectbox("Link to Active Loan", loan_options)
                    
                    sel_id = int(selected_loan.split(" - ")[0].replace("ID: ", ""))
                    sel_borrower = selected_loan.split(" - ")[1]

                    asset_type = c2.selectbox("Asset Type", ["Logbook (Car)", "Land Title", "Electronics", "House Deed", "Other"])
                    desc = st.text_input("Asset Description", placeholder="e.g. Toyota Prado UBA 123X Black")
                    est_value = st.number_input("Estimated Value (UGX)", min_value=0, step=100000)

                    if st.form_submit_button("💾 Save & Secure Asset", use_container_width=True):
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
                                st.success(f"✅ Asset #{new_c_id} registered for {sel_borrower}!")
                                st.rerun()
                        else:
                            st.error("⚠️ Please provide both a description and an estimated value.")

    # --- TAB 2: VIEW & UPDATE (Zoe Portfolio Style) ---
    with tab_view:
        if not col_df.empty:
            col_df["Value"] = pd.to_numeric(col_df["Value"], errors='coerce').fillna(0)
            
            # --- BRANDED METRICS ---
            total_val = col_df[col_df["Status"] != "Released"]["Value"].sum()
            in_custody = col_df[col_df["Status"].isin(["In Custody", "Held"])].shape[0]
            
            m1, m2 = st.columns(2)
            m1.markdown(f"""
                <div style="background-color: #F0F8FF; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL ASSET SECURITY</p>
                    <h2 style="margin:0; color:#2B3F87;">{total_val:,.0f} <span style="font-size:14px;">UGX</span></h2>
                </div>
            """, unsafe_allow_html=True)

            m2.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">ACTIVE ASSETS</p>
                    <h2 style="margin:0; color:#2B3F87;">{in_custody}</h2>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- RESTORED & STYLED INVENTORY TABLE ---
            rows_html = ""
            for i, r in col_df.iterrows():
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                
                # Format the date nicely
                try:
                    formatted_date = pd.to_datetime(r['Date_Added']).strftime('%d %b %Y')
                except:
                    formatted_date = str(r.get('Date_Added', 'N/A'))

                rows_html += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                    <td style="padding:10px; color:#666; font-size:11px;">#{r['Collateral_ID']}</td>
                    <td style="padding:10px;"><b>{r['Borrower']}</b></td>
                    <td style="padding:10px;">{r['Type']}</td>
                    <td style="padding:10px; font-size:11px; color:#444;">{r['Description']}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{r['Value']:,.0f}</td>
                    <td style="padding:10px; text-align:center;">
                        <span style="background:#2B3F87; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r['Status']}</span>
                    </td>
                    <td style="padding:10px; text-align:right; font-size:11px; color:#666;">{formatted_date}</td>
                </tr>"""

            st.markdown(f"""
                <div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;">
                    <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
                        <thead>
                            <tr style="background:#2B3F87; color:white; text-align:left;">
                                <th style="padding:12px;">ID</th>
                                <th style="padding:12px;">Borrower</th>
                                <th style="padding:12px;">Type</th>
                                <th style="padding:12px;">Description</th>
                                <th style="padding:12px; text-align:right;">Value (UGX)</th>
                                <th style="padding:12px; text-align:center;">Status</th>
                                <th style="padding:12px; text-align:right;">Date Secured</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            """, unsafe_allow_html=True)

            # 4. DELETE & EDIT SECTION
            with st.expander("⚙️ Manage Collateral Records"):
                manage_list = col_df.apply(lambda x: f"ID: {x['Collateral_ID']} | {x['Borrower']} - {x['Description']}", axis=1).tolist()
                selected_col = st.selectbox("Select Asset to Modify", manage_list)
                
                c_id = selected_col.split(" | ")[0].replace("ID: ", "")
                c_row = col_df[col_df["Collateral_ID"].astype(str) == c_id].iloc[0]

                ce1, ce2 = st.columns(2)
                upd_desc = ce1.text_input("Edit Description", value=c_row["Description"])
                upd_val = ce1.number_input("Edit Value (UGX)", value=float(c_row["Value"]), step=100000.0)
                
                collateral_options = ["In Custody", "Released", "Disposed", "Held"]
                current_c_status = str(c_row.get("Status", "In Custody"))
                if current_c_status not in collateral_options: current_c_status = "Held"
                
                upd_stat = ce2.selectbox("Update Status", collateral_options, index=collateral_options.index(current_c_status))
                
                btn_upd, btn_del = st.columns(2)
                if btn_upd.button("💾 Save Asset Changes", use_container_width=True):
                    col_df.loc[col_df["Collateral_ID"].astype(str) == c_id, ["Description", "Value", "Status"]] = [upd_desc, upd_val, upd_stat]
                    if save_data("Collateral", col_df):
                        st.success("✅ Asset updated!"); st.rerun()

                if btn_del.button("🗑️ Delete Asset Record", use_container_width=True):
                    new_col_df = col_df[col_df["Collateral_ID"].astype(str) != c_id]
                    if save_data("Collateral", new_col_df):
                        st.warning("⚠️ Asset record deleted!"); st.rerun()
        else:
            st.info("💡 No collateral registered yet.")
# ==============================
# 16. COLLECTIONS & OVERDUE TRACKER (Fixed Amount Recovery)
# ==============================
def show_overdue_tracker():
    st.markdown("### 🚨 Loan Overdue & Rollover Tracker")

    # 🛑 THE GATEKEEPER: Check if data exists in session_state
    if 'loans' not in st.session_state or st.session_state.loans is None:
        # If it's missing, try to load it manually once
        with st.spinner("Fetching latest loan data..."):
            loans_data = get_cached_data("Loans")
            if loans_data is not None:
                st.session_state.loans = loans_data
            else:
                st.error("❌ Could not load loan data. Please refresh the page.")
                return

    # Now it's safe to copy because we know it exists
    loans = st.session_state.loans.copy()
    
    # Do the same safety check for ledger if needed
    ledger = st.session_state.get('ledger', pd.DataFrame())
    # --- PREP DATA ---
    loans['End_Date'] = pd.to_datetime(loans['End_Date'], errors='coerce')
    today = datetime.now()

    # Filter for loans that are actually past their due date
    overdue_df = loans[
        (loans['Status'].isin(["Active", "Overdue", "Rolled/Overdue"])) & 
        (loans['End_Date'] < today)
    ].copy()

    if overdue_df.empty:
        st.success("✨ All accounts are up to date!")
        return

    st.warning(f"Found {len(overdue_df)} accounts requiring monthly rollover.")
    st.dataframe(overdue_df[["Loan_ID", "Borrower", "Principal", "End_Date", "Status"]], use_container_width=True)

    # --- ROLLOVER BUTTON ---
    if st.button("🔄 Execute Monthly Rollover (Compound All)", use_container_width=True):
        updated_df = loans.copy()

        for i, r in overdue_df.iterrows():
            current_id = str(r['Loan_ID'])
            
            # 1. Get the most recent balance for THIS SPECIFIC LOAN ID
            final_amt = 0
            if not ledger.empty:
                # Filter ledger for this specific Loan ID to get the correct balance
                loan_ledger = ledger[ledger['Loan_ID'].astype(str) == current_id]
                if not loan_ledger.empty:
                    # Get the very last balance recorded for this loan
                    final_amt = float(loan_ledger.sort_values('Date').tail(1)['Balance'].values[0])

            # 2. Fallback if no ledger entry exists
            if final_amt == 0:
                # Use Principal + Interest from the loan record
                p_val = float(r.get('Principal', 0))
                i_val = float(r.get('Interest', 0))
                final_amt = p_val + i_val

            # 3. Calculate New Date (Move 1 month forward)
            new_date = r['End_Date'] + pd.DateOffset(months=1)

            # 4. Apply Updates
            updated_df.loc[i, 'Principal'] = final_amt
            updated_df.loc[i, 'End_Date'] = new_date
            updated_df.loc[i, 'Status'] = "Rolled/Overdue"
            updated_df.loc[i, 'Rollover_Date'] = datetime.now().strftime('%Y-%m-%d')

        # --- FINAL CLEANING (The "Timestamp" Fix) ---
        date_cols = ["Start_Date", "End_Date", "Rollover_Date", "Due Date", "Date"]
        for col in date_cols:
            if col in updated_df.columns:
                updated_df[col] = pd.to_datetime(updated_df[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")

        # 5. Save to Google Sheets
        if save_loans(updated_df):
            # Crucial: Update the session state so the change is instant
            st.session_state.loans = updated_df
            st.success("✅ Rollover successful! All balances compounded to next month.")
            st.rerun()
        else:
            st.error("❌ Save failed. Please check your connection.")
# ==============================
# 17. ACTIVITY CALENDAR PAGE
# ==============================

def show_calendar():
    st.markdown("<h2 style='color: #2B3F87;'>📅 Activity Calendar</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA
    loans_df = get_cached_data("Loans")

    if loans_df.empty:
        st.info("📅 Calendar is clear! No active loans to track.")
        return

    # 2. DATA PREPARATION (Bulletproofed)
    # Ensure columns exist before processing
    for col in ["End_Date", "Total_Repayable", "Status", "Borrower", "Loan_ID"]:
        if col not in loans_df.columns:
            loans_df[col] = 0 if col == "Total_Repayable" else "Unknown"

    # Convert to proper types
    loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
    loans_df["Total_Repayable"] = pd.to_numeric(loans_df["Total_Repayable"], errors="coerce").fillna(0)
    
    # Today's reference date
    today = pd.Timestamp.today().normalize()
    
    # Filter for loans that aren't closed
    active_loans = loans_df[loans_df["Status"].astype(str).str.lower() != "closed"].copy()

    # 3. DAILY WORKLOAD METRICS (Zoe Branded Cards)
    due_today_df = active_loans[active_loans["End_Date"].dt.date == today.date()]
    upcoming_df = active_loans[
        (active_loans["End_Date"] > today) & 
        (active_loans["End_Date"] <= today + pd.Timedelta(days=7))
    ]
    overdue_count = active_loans[active_loans["End_Date"] < today].shape[0]

    m1, m2, m3 = st.columns(3)
    
    # Due Today Card (Navy)
    m1.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">📌 DUE TODAY</p>
            <h3 style="margin:0; color:#2B3F87;">{len(due_today_df)} <span style="font-size:14px;">TASKS</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # Upcoming Card (Baby Blue)
    m2.markdown(f"""
        <div style="background-color: #F0F8FF; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">⏳ NEXT 7 DAYS</p>
            <h3 style="margin:0; color:#2B3F87;">{len(upcoming_df)} <span style="font-size:14px;">PENDING</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # Overdue Card (Red Alert)
    m3.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">🔴 OVERDUE CASES</p>
            <h3 style="margin:0; color:#FF4B4B;">{overdue_count} <span style="font-size:14px;">URGENT</span></h3>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- SECTION: DUE TODAY ---
    st.markdown("<h4 style='color: #2B3F87;'>📌 Action Items for Today</h4>", unsafe_allow_html=True)
    if due_today_df.empty:
        st.success("✨ No deadlines for today. Focus on follow-ups!")
    else:
        st.warning(f"⚠️ You have {len(due_today_df)} collection(s) to finalize today.")
        
        # Styled Table for Today
        today_rows = ""
        for i, r in due_today_df.iterrows():
            bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
            today_rows += f"""
            <tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                <td style="padding:10px;"><b>#{r['Loan_ID']}</b></td>
                <td style="padding:10px;">{r['Borrower']}</td>
                <td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{r['Total_Repayable']:,.0f}</td>
                <td style="padding:10px; text-align:center;"><span style="background:#2B3F87; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">💰 COLLECT NOW</span></td>
            </tr>"""
        
        st.markdown(f"""
            <div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;">
                <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
                    <tr style="background:#2B3F87; color:white;">
                        <th style="padding:10px;">Loan ID</th><th style="padding:10px;">Borrower</th>
                        <th style="padding:10px; text-align:right;">Amount Due</th><th style="padding:10px; text-align:center;">Action</th>
                    </tr>
                    {today_rows}
                </table>
            </div>
        """, unsafe_allow_html=True)

    # --- SECTION: UPCOMING ---
    st.markdown("<br><h4 style='color: #2B3F87;'>⏳ Upcoming Deadlines (Next 7 Days)</h4>", unsafe_allow_html=True)
    if upcoming_df.empty:
        st.info("The next few days look quiet.")
    else:
        # --- SECTION: UPCOMING (FIXED AMOUNT LOGIC) ---
        upcoming_display = upcoming_df.sort_values("End_Date").copy()
        up_rows = ""
        for i, r in upcoming_display.iterrows():
            bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
            
            # AUTO-RECOVERY LOGIC:
            # If Total_Repayable is 0, we try to use Principal + Interest
            display_amt = float(r.get('Total_Repayable', 0))
            if display_amt == 0:
                display_amt = float(r.get('Principal', 0)) + float(r.get('Interest', 0))

            up_rows += f"""
            <tr style="background-color: {bg};">
                <td style="padding:10px; color:#2B3F87; font-weight:bold;">{r['End_Date'].strftime('%d %b (%a)')}</td>
                <td style="padding:10px;">{r.get('Borrower', 'Unknown')}</td>
                <td style="padding:10px; text-align:right; font-weight:bold;">{display_amt:,.0f} UGX</td>
                <td style="padding:10px; text-align:right; color:#666;">ID: #{r.get('Loan_ID', 'N/A')}</td>
            </tr>"""

        st.markdown(f"""
            <div style="border:1px solid #2B3F87; border-radius:10px; overflow:hidden;">
                <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
                    <tr style="background:#2B3F87; color:white;">
                        <th style="padding:10px;">Due Date</th><th style="padding:10px;">Borrower</th>
                        <th style="padding:10px; text-align:right;">Amount</th><th style="padding:10px; text-align:right;">Ref</th>
                    </tr>
                    {up_rows}
                </table>
            </div>
        """, unsafe_allow_html=True)

    # --- SECTION: IMMEDIATE FOLLOW-UP ---
    st.markdown("<br><h4 style='color: #FF4B4B;'>🔴 Past Due (Immediate Attention)</h4>", unsafe_allow_html=True)
    overdue_df = active_loans[active_loans["End_Date"] < today].copy()
    
    if overdue_df.empty:
        st.success("Clean Sheet! No overdue loans found. 🎉")
    else:
        overdue_df["Days_Late"] = (today - overdue_df["End_Date"]).dt.days
        overdue_df = overdue_df.sort_values("Days_Late", ascending=False)
        
        od_rows = ""
        for i, r in overdue_df.iterrows():
            bg = "#FFF5F5" # Slight red tint for rows
            late_color = "#FF4B4B" if r['Days_Late'] > 7 else "#FFA500"
            od_rows += f"""
            <tr style="background-color: {bg}; border-bottom: 1px solid #FFDADA;">
                <td style="padding:10px;"><b>#{r['Loan_ID']}</b></td>
                <td style="padding:10px;">{r['Borrower']}</td>
                <td style="padding:10px; text-align:center; font-weight:bold; color:{late_color};">{r['Days_Late']} Days</td>
                <td style="padding:10px; text-align:center;"><span style="background:{late_color}; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r['Status']}</span></td>
            </tr>"""

        st.markdown(f"""
            <div style="border:2px solid #FF4B4B; border-radius:10px; overflow:hidden;">
                <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
                    <tr style="background:#FF4B4B; color:white;">
                        <th style="padding:10px;">Loan ID</th><th style="padding:10px;">Borrower</th>
                        <th style="padding:10px; text-align:center;">Late By</th><th style="padding:10px; text-align:center;">Status</th>
                    </tr>
                    {od_rows}
                </table>
            </div>
        """, unsafe_allow_html=True)
# ==============================
# 18. EXPENSE MANAGEMENT PAGE
# ==============================

def show_expenses():
    st.markdown("<h2 style='color: #2B3F87;'>📁 Expense Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA
    df = get_cached_data("Expenses")

    # The Master Category List for Zoe Consults
    EXPENSE_CATS = ["Rent", "Insurance Account", "Utilities", "Salaries", "Marketing", "Office Expenses"]

    if df.empty:
        df = pd.DataFrame(columns=["Expense_ID", "Category", "Amount", "Date", "Description", "Payment_Date", "Receipt_No"])

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_add, tab_view, tab_manage = st.tabs(["➕ Record Expense", "📊 Spending Analysis", "⚙️ Manage/Delete"])

    # --- TAB 1: ADD NEW EXPENSE ---
    with tab_add:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("add_expense_form", clear_on_submit=True):
            st.markdown("<h4 style='color: #2B3F87;'>📝 Log Business Outflow</h4>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            # UPDATED CATEGORY LIST
            category = col1.selectbox("Category", EXPENSE_CATS)
            amount = col2.number_input("Amount (UGX)", min_value=0, step=1000)
            
            desc = st.text_input("Description (e.g., Office Power Bill March)")
            
            c_date, c_receipt = st.columns(2)
            p_date = c_date.date_input("Actual Payment Date", value=datetime.now())
            receipt_no = c_receipt.text_input("Receipt / Invoice #", placeholder="e.g. RCP-101")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀 Save Expense Record", use_container_width=True):
                if amount > 0 and desc:
                    new_id = int(df["Expense_ID"].max() + 1) if not df.empty else 1
                    new_entry = pd.DataFrame([{
                        "Expense_ID": new_id,
                        "Category": category,
                        "Amount": amount,
                        "Date": datetime.now().strftime("%Y-%m-%d"), 
                        "Description": desc,
                        "Payment_Date": p_date.strftime("%Y-%m-%d"), 
                        "Receipt_No": receipt_no                    
                    }])
                    
                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    if save_data("Expenses", updated_df):
                        st.success(f"✅ Expense of {amount:,.0f} recorded under {category}!")
                        st.rerun()
                else:
                    st.error("⚠️ Please provide both an amount and a description.")

    # --- TAB 2: ANALYSIS & LOG ---
    with tab_view:
        if not df.empty:
            df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
            total_spent = df["Amount"].sum()
            
            st.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL MONTHLY OUTFLOW</p>
                    <h2 style="margin:0; color:#FF4B4B;">{total_spent:,.0f} <span style="font-size:14px;">UGX</span></h2>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            cat_summary = df.groupby("Category")["Amount"].sum().reset_index()
            fig_exp = px.pie(cat_summary, names="Category", values="Amount", 
                             title="Spending Distribution",
                             hole=0.4, color_discrete_sequence=["#2B3F87", "#F0F8FF", "#FF4B4B", "#ADB5BD"])
            fig_exp.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="#2B3F87")
            st.plotly_chart(fig_exp, use_container_width=True)
            
            st.markdown("<h4 style='color: #2B3F87;'>📜 Detailed Expense Log</h4>", unsafe_allow_html=True)
            
            rows_html = ""
            # We already figured out the correct date column name here:
            date_col = "Date" if "Date" in df.columns else df.columns[0] 
            
            sorted_df = df.sort_values(date_col, ascending=False)
            
            for i, r in sorted_df.iterrows():
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                
                # SAFE GET: Use .get() to prevent KeyError if a column is missing
                d_val = r.get(date_col, "-")
                c_val = r.get('Category', 'Other')
                desc = r.get('Description', '-')
                amt  = float(r.get('Amount', 0))
                rec  = r.get('Receipt_No', '-')

                rows_html += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                    <td style="padding:10px; color:#666; font-size:11px;">{d_val}</td>
                    <td style="padding:10px;"><b>{c_val}</b></td>
                    <td style="padding:10px; font-size:11px;">{desc}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:#FF4B4B;">{amt:,.0f}</td>
                    <td style="padding:10px; text-align:center; color:#666; font-size:10px;">{rec}</td>
                </tr>"""

            st.markdown(f"""
                <div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;">
                    <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
                        <thead>
                            <tr style="background:#2B3F87; color:white; text-align:left;">
                                <th style="padding:12px;">Date</th>
                                <th style="padding:12px;">Category</th>
                                <th style="padding:12px;">Description</th>
                                <th style="padding:12px; text-align:right;">Amount (UGX)</th>
                                <th style="padding:12px; text-align:center;">Receipt #</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("💡 No expense data recorded yet.")

    # --- TAB 3: MANAGE / EDIT / DELETE ---
    with tab_manage:
        if not df.empty:
            st.markdown("<h4 style='color: #2B3F87;'>🛠️ Adjust Expense Records</h4>", unsafe_allow_html=True)
            edit_options = df.apply(lambda x: f"ID: {int(x['Expense_ID'])} | {x['Category']} - {x['Description']}", axis=1).tolist()
            selected_to_edit = st.selectbox("Select Record", edit_options)
            
            e_id = int(selected_to_edit.split(" | ")[0].replace("ID: ", ""))
            e_row = df[df["Expense_ID"] == e_id].iloc[0]

            with st.container():
                c_a, c_b = st.columns(2)
                # FIXED LOGIC: We look for the current category in our new Master List
                current_cat = e_row["Category"]
                if current_cat not in EXPENSE_CATS:
                    current_cat = "Office Expenses" # Fallback
                
                upd_cat = c_a.selectbox("Update Category", EXPENSE_CATS, 
                                        index=EXPENSE_CATS.index(current_cat))
                
                upd_amt = c_b.number_input("Update Amount", value=float(e_row["Amount"]), step=1000.0)
                
                c_c, c_d = st.columns(2)
                upd_date = c_c.text_input("Update Payment Date", value=str(e_row.get("Payment_Date", "")))
                upd_receipt = c_d.text_input("Update Receipt No", value=str(e_row.get("Receipt_No", "")))
                
                upd_desc = st.text_input("Update Description", value=e_row["Description"])

                btn1, btn2 = st.columns(2)
                if btn1.button("💾 Save Changes", use_container_width=True):
                    df.loc[df["Expense_ID"] == e_id, 
                           ["Category", "Amount", "Description", "Payment_Date", "Receipt_No"]] = \
                           [upd_cat, upd_amt, upd_desc, upd_date, upd_receipt]
                    
                    if save_data("Expenses", df):
                        st.success("Record updated! ✅")
                        st.rerun()

                if btn2.button("🗑️ Delete Permanently", use_container_width=True):
                    df = df[df["Expense_ID"] != e_id]
                    if save_data("Expenses", df):
                        st.warning("Expense Record Deleted!")
                        st.rerun()
# ==============================
# 19. PETTY CASH MANAGEMENT PAGE
# ==============================

def show_petty_cash():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Petty Cash Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA
    df = get_cached_data("PettyCash")

    if df.empty:
        df = pd.DataFrame(columns=["Transaction_ID", "Type", "Amount", "Date", "Description"])
    else:
        df["Transaction_ID"] = pd.to_numeric(df["Transaction_ID"], errors='coerce').fillna(0).astype(int)
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # 2. SMART BALANCE METRICS
    inflow = df[df["Type"] == "In"]["Amount"].sum()
    outflow = df[df["Type"] == "Out"]["Amount"].sum()
    balance = inflow - outflow

    # --- STYLED NEON CARDS ---
    c1, c2, c3 = st.columns(3)
    
    # Inflow Card (Green)
    c1.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #10B981; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL CASH IN</p>
            <h3 style="margin:0; color:#10B981;">{inflow:,.0f} <span style="font-size:14px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # Outflow Card (Red)
    c2.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL CASH OUT</p>
            <h3 style="margin:0; color:#FF4B4B;">{outflow:,.0f} <span style="font-size:14px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # Balance Card (Dynamic Color)
    bal_color = "#2B3F87" if balance >= 50000 else "#FF4B4B"
    c3.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid {bal_color}; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">CURRENT BALANCE</p>
            <h3 style="margin:0; color:{bal_color};">{balance:,.0f} <span style="font-size:14px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

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
                        st.success(f"Successfully recorded {t_amount:,.0f} UGX!")
                        st.rerun()
                else:
                    st.error("Please provide amount and description.")

    # --- TAB 2: HISTORY ---
    with tab_history:
        if not df.empty:
            def color_type(val):
                return 'color: #10B981;' if val == 'In' else 'color: #FF4B4B;'
            
            # Show Table with commas and color coding
            st.dataframe(
                df.sort_values("Date", ascending=False)
                .style.applymap(color_type, subset=['Type'])
                .format({"Amount": "{:,.0f}"}),
                use_container_width=True, hide_index=True
            )

            # ADMIN ACTIONS
            with st.expander("⚙️ Advanced: Edit or Delete Transaction"):
                options = [f"ID: {int(row['Transaction_ID'])} | {row['Type']} - {row['Description']}" for _, row in df.iterrows()]
                selected_task = st.selectbox("Select Entry to Modify", options)
                
                sel_id = int(selected_task.split(" | ")[0].replace("ID: ", ""))
                item = df[df["Transaction_ID"] == sel_id].iloc[0]

                up_type = st.selectbox("Update Type", ["In", "Out"], index=0 if item["Type"] == "In" else 1)
                up_amt = st.number_input("Update Amount", value=float(item["Amount"]), step=1000.0)
                up_desc = st.text_input("Update Description", value=item["Description"])

                c_up, c_del = st.columns(2)
                if c_up.button("💾 Save Changes", use_container_width=True):
                    df.loc[df["Transaction_ID"] == sel_id, ["Type", "Amount", "Description"]] = [up_type, up_amt, up_desc]
                    if save_data("PettyCash", df):
                        st.success("Updated Successfully!")
                        st.rerun()

                if c_del.button("🗑️ Delete Permanently", use_container_width=True):
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
    if st.session_state.get("role") != "Admin":
        st.error("🔒 Restricted Access.")
        return

    st.markdown("<h2 style='color: #4A90E2;'>🧾 Payroll Management</h2>", unsafe_allow_html=True)

    # 1. SYNC COLUMNS TO MATCH YOUR IMAGE EXACTLY
    df = get_cached_data("Payroll")
    required_columns = [
        "Payroll_ID", "Employee", "TIN", "Designation", "Mob_No", "Account_No", "NSSF_No",
        "Arrears", "Basic_Salary", "Absent_Deduction", "LST", "Gross_Salary", 
        "PAYE", "NSSF_5", "Advance_DRS", "Other_Deductions", "Net_Pay", 
        "NSSF_10", "NSSF_15", "Date"
    ]
    
    if df.empty:
        df = pd.DataFrame(columns=required_columns)
    else:
        for col in required_columns:
            if col not in df.columns: df[col] = 0
        df = df.fillna(0)

    # 2. THE EXACT MATH ENGINE (From your Manual Sheet)
    def run_manual_sync_calculations(basic, arrears, absent_deduct, advance, other):
        # Gross = (Basic + Arrears) - Absenteeism
        gross = (float(basic) + float(arrears)) - float(absent_deduct)
        
        # Taxes
        lst = 100000 / 12 if gross > 1000000 else 0
        
        # NSSF SPLIT (Match your yellow columns)
        n5 = gross * 0.05   # Employee Part
        n10 = gross * 0.10  # Employer Part
        n15 = n5 + n10      # Total
        
        # PAYE (Standard UG formula)
        taxable = gross - n5 # TAXABLE is Gross minus the 5% NSSF
        paye = 0
        if taxable > 410000: paye = 25000 + (0.30 * (taxable - 410000))
        elif taxable > 282000: paye = (taxable - 282000) * 0.20 + 4700
        elif taxable > 235000: paye = (taxable - 235000) * 0.10

        # Total Deductions = PAYE + LST + NSSF(5%) + Advance + Others
        # Note: We only subtract the 5% NSSF from the employee's pay!
        total_deductions = paye + lst + n5 + float(advance) + float(other)
        net = gross - total_deductions
        
        return {
            "gross": round(gross), "lst": round(lst), "n5": round(n5),
            "n10": round(n10), "n15": round(n15), "paye": round(paye), "net": round(net)
        }

    tab_process, tab_logs = st.tabs(["➕ Process Salary", "📜 Payroll History"])

    with tab_process:
        with st.form("new_payroll_form", clear_on_submit=True):
            name = st.text_input("Employee Name")
            c1, c2, c3 = st.columns(3)
            f_tin = c1.text_input("TIN")
            f_desig = c2.text_input("Designation")
            f_mob = c3.text_input("Mob No.")
            c4, c5 = st.columns(2)
            f_acc = c4.text_input("Account No.")
            f_nssf_no = c5.text_input("NSSF No.")
            st.write("---")
            c6, c7, c8 = st.columns(3)
            f_arrears = c6.number_input("ARREARS", min_value=0.0)
            f_basic = c7.number_input("SALARY (Basic)", min_value=0.0)
            f_absent = c8.number_input("Absenteeism Deduction", min_value=0.0)
            c9, c10 = st.columns(2)
            f_adv = c9.number_input("S.DRS / ADVANCE", min_value=0.0)
            f_other = c10.number_input("Other Deductions", min_value=0.0)

            if st.form_submit_button("💳 Confirm & Release Payment"):
                if name and f_basic > 0:
                    calc = run_manual_sync_calculations(f_basic, f_arrears, f_absent, f_adv, f_other)
                    new_row = pd.DataFrame([{
                        "Payroll_ID": int(df["Payroll_ID"].max()+1) if not df.empty else 1,
                        "Employee": name, "TIN": f_tin, "Designation": f_desig, "Mob_No": f_mob,
                        "Account_No": f_acc, "NSSF_No": f_nssf_no, "Arrears": f_arrears,
                        "Basic_Salary": f_basic, "Absent_Deduction": f_absent,
                        "Gross_Salary": calc['gross'], "LST": calc['lst'], "PAYE": calc['paye'],
                        "NSSF_5": calc['n5'], "NSSF_10": calc['n10'], "NSSF_15": calc['n15'],
                        "Advance_DRS": f_adv, "Other_Deductions": f_other, "Net_Pay": calc['net'],
                        "Date": datetime.now().strftime("%Y-%m-%d")
                    }])
                    if save_data("Payroll", pd.concat([df, new_row], ignore_index=True)):
                        st.success("✅ Payroll Saved!"); st.rerun()

    # --- TAB 2: HISTORY ---
    with tab_logs:
        if not df.empty:
            # 1. TOP ROW: Title and Print Button
            p_col1, p_col2 = st.columns([4, 1])
            p_col1.markdown(f"<h3 style='color: #4A90E2;'>{datetime.now().strftime('%B %Y')} Summary</h3>", unsafe_allow_html=True)
            
            if p_col2.button("📥 Print PDF", key="print_payroll_final"):
                st.components.v1.html("""<script>window.parent.focus(); window.parent.print();</script>""", height=0)

            # 2. CSS PRINT SHIELD (Keeps the printout clean)
            st.markdown("""
                <style>
                @media print {
                    body * { visibility: hidden; }
                    #payroll-box, #payroll-box * { visibility: visible; -webkit-print-color-adjust: exact !important; }
                    #payroll-box { position: absolute; left: 0; top: 0; width: 100% !important; border: 2px solid #2B3F87 !important; padding: 40px !important; background-color: white !important; }
                    [data-testid="stSidebar"], [data-testid="stHeader"], .stButton { display: none !important; }
                }
                </style>
            """, unsafe_allow_html=True)

            def fm(x): 
                try: return f"{int(float(x)):,}" 
                except: return "0"

            # 3. BUILD ROWS (With A/C Provision & NSSF 15% Math)
            rows_html = ""
            for i, r in df.iterrows():
                # Force math for the 15% column so it's never zero
                n5 = float(r.get('NSSF_5', 0)) if r.get('NSSF_5') != "" else 0
                n10 = float(r.get('NSSF_10', 0)) if r.get('NSSF_10') != "" else 0
                n15_total = n5 + n10

                rows_html += f"""
                <tr>
                    <td style='text-align:center; border:1px solid #ddd; padding: 15px 10px;'>{i+1}</td>
                    <td style='border:1px solid #ddd; padding: 15px 10px;'>
                        <div style="font-weight:bold; font-size:12px;">{r['Employee']}</div>
                        <div style="font-size:10px; color:#555;">{r.get('Designation', '-')}</div>
                        <div style="font-size:10px; color:#2B3F87; margin-top:4px;"><b>A/C:</b> {r.get('Account_No', '-')}</div>
                    </td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px;'>{fm(r['Arrears'])}</td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px;'>{fm(r['Basic_Salary'])}</td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px; font-weight:bold;'>{fm(r['Gross_Salary'])}</td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px;'>{fm(r['PAYE'])}</td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px;'>{fm(n5)}</td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px; background:#E3F2FD; font-weight:bold; color:#2B3F87;'>{fm(r['Net_Pay'])}</td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px; background:#FFF9C4;'>{fm(n10)}</td>
                    <td style='text-align:right; border:1px solid #ddd; padding: 15px 10px; background:#FFF9C4; font-weight:bold;'>{fm(n15_total)}</td>
                </tr>"""

            # 4. FINAL HTML STRUCTURE (Merged into one clean variable)
            main_html = f"""
            <div id="payroll-box" style="border: 2px solid #4A90E2; padding: 35px; background: white; font-family: sans-serif; border-radius: 10px;">
                <div style="text-align:center; border-bottom:3px solid #2B3F87; padding-bottom:15px; margin-bottom:25px;">
                    <h1 style="color:#2B3F87; margin:0;">ZOE CONSULTS SMC LTD</h1>
                    <p style="margin:5px 0; color:#666;"><b>OFFICIAL PAYROLL REPORT - {datetime.now().strftime('%B %Y')}</b></p>
                </div>
                <table style="width:100%; border-collapse:collapse; font-size:11px;">
                    <thead>
                        <tr style="background:#2B3F87; color:white;">
                            <th style="padding:12px; border:1px solid #ddd;">S/N</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:left;">Employee Details</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right;">Arrears</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right;">Basic</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right;">Gross</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right;">P.A.Y.E</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right;">NSSF(5%)</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right; background:#1a285e;">Net Pay</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right; color:black; background:#FFD700;">10% NSSF</th>
                            <th style="padding:12px; border:1px solid #ddd; text-align:right; color:black; background:#FFD700;">NSSF 15%</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
                <div style="margin-top:100px; display:flex; justify-content:space-around; font-size:12px;">
                    <div style="text-align:center; border-top:1px solid #000; width:200px; padding-top:8px;"><b>PREPARED BY</b></div>
                    <div style="text-align:center; border-top:1px solid #000; width:200px; padding-top:8px;"><b>APPROVED BY</b></div>
                </div>
            </div>"""
            
            # 5. RENDER THE PREVIEW
            st.components.v1.html(main_html, height=800, scrolling=True)

            # 6. MODIFY & DELETE SECTION (Inside the if block)
            st.write("---")
            with st.expander("⚙️ Modify / Delete Record"):
                pay_opts = [f"{r['Employee']} (ID: {r['Payroll_ID']})" for _, r in df.iterrows()]
                if pay_opts:
                    sel_opt = st.selectbox("Select Record", pay_opts)
                    sid = str(sel_opt.split("(ID: ")[1].replace(")", ""))
                    item = df[df['Payroll_ID'].astype(str) == sid].iloc[0]
                    
                    u_name = st.text_input("Edit Name", value=str(item['Employee']))
                    u_basic = st.number_input("Edit Basic", value=float(item['Basic_Salary'] if item['Basic_Salary'] != "" else 0))
                    u_arr = st.number_input("Edit Arrears", value=float(item['Arrears'] if item['Arrears'] != "" else 0))
                    
                    c_s, c_d = st.columns(2)
                    if c_s.button("💾 Save Updates", use_container_width=True):
                        # Simple recalculation for basic updates
                        res_u = calculate_zoe_payroll(u_basic, u_arr, 0, 0, 0)
                        df.loc[df['Payroll_ID'].astype(str) == sid, ["Employee","Basic_Salary","Arrears","Gross_Salary","PAYE","NSSF_15","Net_Pay"]] = \
                            [u_name, u_basic, u_arr, res_u['gross'], res_u['paye'], res_u['nssf'], res_u['net']]
                        if save_data("Payroll", df): st.success("Updated!"); st.rerun()
                    
                    if c_d.button("🗑️ Delete Record", use_container_width=True):
                        if save_data("Payroll", df[df['Payroll_ID'].astype(str) != sid]): st.warning("Deleted!"); st.rerun()

        else:
            st.info("No payroll records found for this period.")
        
    
 

# ==============================
# 21. ADVANCED ANALYTICS & REPORTS
# ==============================

def show_reports():
    st.markdown("<h2 style='color: #4A90E2;'>📊 Advanced Analytics & Reports</h2>", unsafe_allow_html=True)
    
    # 1. FETCH ALL DATA
    loans = get_cached_data("Loans")
    payments = get_cached_data("Payments")
    expenses = get_cached_data("Expenses")
    payroll = get_cached_data("Payroll")
    petty = get_cached_data("PettyCash")

    if loans.empty:
        st.info("📈 Record more loans to see your financial analytics.")
        return

    # 2. THE ULTIMATE PAYROLL SAFETY CHECK
    # This line forces payroll to be a DataFrame if it's not one already
    if not isinstance(payroll, pd.DataFrame):
        payroll = pd.DataFrame()

    pay_amt, nssf_total, paye_total = 0, 0, 0
    
    if not payroll.empty:
        # Use a super-safe way to pull column totals
        pay_amt = pd.to_numeric(payroll.get("Gross_Salary", pd.Series([0])), errors="coerce").fillna(0).sum()
        n5 = pd.to_numeric(payroll.get("NSSF_5", pd.Series([0])), errors="coerce").fillna(0).sum()
        n10 = pd.to_numeric(payroll.get("NSSF_10", pd.Series([0])), errors="coerce").fillna(0).sum()
        nssf_total = n5 + n10
        paye_total = pd.to_numeric(payroll.get("PAYE", pd.Series([0])), errors="coerce").fillna(0).sum()

    # 3. OTHER DATA SUMS (Properly Indented)
    # Safe Principal Lookup
    l_amt_col = "Principal" if "Principal" in loans.columns else "Amount"
    l_amt = pd.to_numeric(loans.get(l_amt_col, 0), errors="coerce").fillna(0).sum()
    
    # Other Metric Totals
    l_int = pd.to_numeric(loans.get("Interest", 0), errors="coerce").fillna(0).sum()
    p_amt = pd.to_numeric(payments.get("Amount", 0), errors="coerce").fillna(0).sum() if not payments.empty else 0
    exp_amt = pd.to_numeric(expenses.get("Amount", 0), errors="coerce").fillna(0).sum() if not expenses.empty else 0
    
    # Force petty to be a DataFrame safely
    if not isinstance(petty, pd.DataFrame): 
        petty = pd.DataFrame()
    
    petty_out = 0
    if not petty.empty and "Type" in petty.columns:
        petty_out = pd.to_numeric(petty[petty["Type"]=="Out"].get("Amount", 0), errors="coerce").fillna(0).sum()
    
    # 💰 FINANCIAL LOGIC:
    # Total Outflow = Expenses + Petty Cash Out + (Taxes if defined)
    # Note: nssf_total and paye_total must be defined above this line!
    total_outflow = exp_amt + petty_out + (nssf_total if 'nssf_total' in locals() else 0) + (paye_total if 'paye_total' in locals() else 0)
    
    # Net Profit = Inflows (Payments) - Outflows (Expenses)
    net_profit = p_amt - total_outflow

    # 4. KPI DASHBOARD (Soft Blue)
    st.subheader("🚀 Financial Performance")
    k1, k2, k3, k4 = st.columns(4)
    # ... rest of your KPI and charts code ...
    
    k1.markdown(f"""<div style="background-color:#fff;padding:15px;border-radius:10px;border-left:5px solid #4A90E2;box-shadow:2px 2px 8px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">CAPITAL ISSUED</p><h4 style="margin:0;color:#4A90E2;">{l_amt:,.0f}</h4></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div style="background-color:#fff;padding:15px;border-radius:10px;border-left:5px solid #4A90E2;box-shadow:2px 2px 8px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">INTEREST ACCRUED</p><h4 style="margin:0;color:#4A90E2;">{l_int:,.0f}</h4></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div style="background-color:#fff;padding:15px;border-radius:10px;border-left:5px solid #2E7D32;box-shadow:2px 2px 8px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">COLLECTIONS</p><h4 style="margin:0;color:#2E7D32;">{p_amt:,.0f}</h4></div>""", unsafe_allow_html=True)
    
    p_color = "#2E7D32" if net_profit >= 0 else "#FF4B4B"
    k4.markdown(f"""<div style="background-color:#fff;padding:15px;border-radius:10px;border-left:5px solid {p_color};box-shadow:2px 2px 8px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">NET PROFIT</p><h4 style="margin:0;color:{p_color};">{net_profit:,.0f}</h4></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. VISUAL ANALYTICS
    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.write("**💰 Income vs. Expenses (Monthly)**")
        if not payments.empty:
            pay_copy = payments.copy()
            pay_copy["Date"] = pd.to_datetime(pay_copy.get("Date"))
            # Safe Amount lookup
            p_val_col = "Amount" if "Amount" in pay_copy.columns else pay_copy.columns[0]
            inc_trend = pay_copy.groupby(pay_copy["Date"].dt.strftime('%Y-%m'))[p_val_col].sum().reset_index()
            
            exp_copy = expenses.copy() if not expenses.empty else pd.DataFrame(columns=["Amount", "Date"])
            if not exp_copy.empty:
                exp_copy["Date"] = pd.to_datetime(exp_copy.get("Date"))
                exp_trend = exp_copy.groupby(exp_copy["Date"].dt.strftime('%Y-%m'))["Amount"].sum().reset_index()
            else:
                exp_trend = pd.DataFrame(columns=["Date", "Amount"])

            # Merge trends
            merged = pd.merge(inc_trend, exp_trend, left_on="Date", right_on="Date", how="outer").fillna(0)
            merged.columns = ["Month", "Income", "Expenses"]
            
            fig_bar = px.bar(merged, x="Month", y=["Income", "Expenses"], barmode="group",
                             color_discrete_map={"Income": "#00ffcc", "Expenses": "#FF4B4B"})
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No payment data to chart.")

    with col_right:
        st.write("**🛡️ Portfolio Weight (Top 5)**")
        if not loans.empty:
            # Safe Principal/Amount lookup
            val_col = "Principal" if "Principal" in loans.columns else "Amount"

            # Safe grouping logic (Properly Indented)
            top_borrowers = loans.groupby("Borrower")[val_col].sum().sort_values(ascending=False).head(5).reset_index()

            # Rename for chart clarity
            top_borrowers.columns = ["Borrower", "Total_Loaned"]
            
            # CRITICAL FIX: values must match the new column name "Total_Loaned"
            fig_pie = px.pie(top_borrowers, names="Borrower", values="Total_Loaned", hole=0.5,
                             color_discrete_sequence=px.colors.sequential.GnBu_r)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No loan data for portfolio analysis.")

    # 6. RISK INDICATOR (Properly Indented)
    st.markdown("---")
    st.subheader("🚨 Risk Assessment")
    
    # Use the same 'val_col' logic we set up for the pie chart
    val_col = "Principal" if "Principal" in loans.columns else "Amount"

    # Safe filtering for overdue amounts
    overdue_mask = loans["Status"].isin(["Overdue", "Rolled/Overdue"])
    overdue_val = pd.to_numeric(loans.loc[overdue_mask, val_col], errors="coerce").fillna(0).sum()
    
    # Use the l_amt we calculated in Section 3
    risk_percent = (overdue_val / l_amt * 100) if l_amt > 0 else 0
    
    r1, r2 = st.columns([2, 1])
    
    with r1:
        st.write(f"Your Portfolio at Risk (PAR) is **{risk_percent:.1f}%**.")
        # Progress bar cap at 1.0 (100%)
        st.progress(min(float(risk_percent) / 100, 1.0))
        st.write(f"Total Overdue: **{overdue_val:,.0f} UGX**")
        
    with r2:
        if risk_percent < 10: 
            st.success("✅ Healthy Portfolio")
        elif risk_percent < 25: 
            st.warning("⚠️ Moderate Risk")
        else: 
            st.error("🆘 Critical Risk Level")

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
    # Using .get() here too just in case!
    loan_options = loans_df.apply(lambda x: f"ID: {x.get('Loan_ID', 'N/A')} - {x.get('Borrower', 'Unknown')}", axis=1).tolist()
    selected_loan = st.selectbox("Select Loan to View Full Statement", loan_options)
    
    # Extract the ID safely
    l_id = int(selected_loan.split(" - ")[0].replace("ID: ", ""))
    
    # Get specific loan info
    loan_info = loans_df[loans_df["Loan_ID"] == l_id].iloc[0]
    
    # --- MATH ENGINE (Properly Indented) ---
    # We use .get() and fallback to math if Total_Repayable is missing
    t_repayable = float(loan_info.get("Total_Repayable", 0))
    if t_repayable == 0:
        t_repayable = float(loan_info.get("Principal", 0)) + float(loan_info.get("Interest", 0))

    a_paid = float(loan_info.get("Amount_Paid", 0))

    # Now we calculate the balance safely
    current_balance = t_repayable - a_paid
    
    # --- DISPLAY THE CARD ---
    st.markdown(f"""
        <div style="background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px;">
            <p style="margin:0; font-size:14px; color:#666; font-weight:bold;">CURRENT OUTSTANDING BALANCE (INC. INTEREST)</p>
            <h1 style="margin:0; color:#2B3F87;">{current_balance:,.0f} <span style="font-size:18px;">UGX</span></h1>
        </div>
    """, unsafe_allow_html=True)

    # 2. BUILD THE LEDGER TABLE
    ledger_data = []

    # --- ROW 1: THE DISBURSEMENT (Initial Debt) ---
    # We pull the Start_Date safely from your Google Sheet
    disburse_date = loan_info.get("Start_Date", datetime.now().strftime("%Y-%m-%d"))
    
    ledger_data.append({
        "Date": disburse_date,
        "Description": "Initial Loan Disbursement (Principal + Interest)",
        "Debit": t_repayable,
        "Credit": 0,
        "Balance": t_repayable
    })

    # --- SUBSEQUENT ROWS: PAYMENTS ---
    # (Your code would then loop through payments and append them to ledger_data)
        

    # --- SUBSEQUENT ROWS: PAYMENTS ---
    relevant_payments = payments_df[payments_df["Loan_ID"] == l_id].sort_values("Date")
    running_balance = float(t_repayable)
    
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
    
    if st.button("✨ Preview Consolidated Statement", use_container_width=True):
        # 1. FETCH ALL RELEVANT DATA
        borrowers_df = get_cached_data("Borrowers")
        all_loans_df = get_cached_data("Loans")
        all_payments_df = get_cached_data("Payments")
        
        # Identify the Borrower
        current_b_name = loan_info['Borrower'] 
        
        # Find all loans for this person
        client_loans = all_loans_df[all_loans_df["Borrower"] == current_b_name]
        
        # Get Borrower Details for the Header
        b_data = borrowers_df[borrowers_df["Name"] == current_b_name]
        b_details = b_data.iloc[0] if not b_data.empty else {}

        # 2. Colors & Header
        navy_blue = "#000080"
        baby_blue = "#E1F5FE"
        
        html_statement = f"""
        <div style="font-family: 'Arial', sans-serif; padding: 25px; border: 1px solid #eee; max-width: 850px; margin: auto; background-color: white; color: #333;">
            
            <div style="background-color: {navy_blue}; color: white; padding: 30px; border-radius: 8px 8px 0 0; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="margin:0; letter-spacing: 1px;">ZOE CONSULTS SMC LTD</h1>
                    <p style="margin:5px 0 0 0; opacity: 0.8;">Consolidated Client Statement</p>
                </div>
                <div style="text-align: right;">
                    <p style="margin:0; font-weight: bold;">CLIENT: {current_b_name}</p>
                    <p style="margin:0; font-size: 12px;">{datetime.now().strftime('%d %b %Y')}</p>
                </div>
            </div>
            
            <div style="padding: 15px; border: 1px solid #ddd; border-top: none; background-color: #fcfcfc;">
                <table style="width: 100%; font-size: 13px;">
                    <tr>
                        <td><strong>Phone:</strong> {b_details.get('Phone', 'N/A')} | <strong>NIN:</strong> {b_details.get('National_ID', 'N/A')}</td>
                        <td style="text-align: right;"><strong>Address:</strong> {b_details.get('Address', 'N/A')}</td>
                    </tr>
                </table>
            </div>

            <h3 style="color: {navy_blue}; margin-top: 30px; border-bottom: 2px solid {navy_blue}; padding-bottom: 5px;">💼 Account Summaries</h3>
        """

        # 3. LOOP THROUGH EACH LOAN
        grand_total_balance = 0
        
        for index, l_row in client_loans.iterrows():
            l_id = l_row['Loan_ID']
            
            # BUILD LEDGER SAFELY
            l_ledger = []
            
            # Find the date and amount using .get() to avoid KeyErrors
            orig_date = l_row.get('Date') if 'Date' in l_row else l_row.get('date', 'N/A')
            orig_repay = pd.to_numeric(l_row.get('Total_Repayable', 0), errors='coerce')
            
            l_ledger.append({
                "Date": orig_date, 
                "Description": "Principal + Interest", 
                "Debit": orig_repay, 
                "Credit": 0
            })
            
            # Fetch payments for this specific loan
            l_payments = all_payments_df[all_payments_df["Loan_ID"] == l_id]
            for _, p in l_payments.iterrows():
                # Safety check for payment columns too
                p_date = p.get('Date') if 'Date' in p else p.get('date', 'N/A')
                p_amt = pd.to_numeric(p.get('Amount', 0), errors='coerce')
                
                l_ledger.append({
                    "Date": p_date, 
                    "Description": f"Payment (Rec: {p.get('Receipt_No', 'N/A')})", 
                    "Debit": 0, 
                    "Credit": p_amt
                })
            
            # Convert to DataFrame for Balance Calculation
            temp_df = pd.DataFrame(l_ledger)
            if not temp_df.empty:
                temp_df['Balance'] = temp_df['Debit'].cumsum() - temp_df['Credit'].cumsum()
                current_l_balance = temp_df.iloc[-1]['Balance']
                grand_total_balance += current_l_balance
            else:
                current_l_balance = 0

            # --- REMAINDER OF YOUR HTML CODE ---

            # Add Loan Header and Table to HTML
            html_statement += f"""
            <div style="margin-top: 20px; padding: 10px; background-color: {baby_blue}; border-radius: 5px;">
                <span style="font-weight: bold; color: {navy_blue};">LOAN ID: {l_id}</span> | 
                <span>Status: {l_row['Status']}</span> | 
                <span style="float: right;">Loan Balance: <strong>{current_l_balance:,.0f} UGX</strong></span>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 20px;">
                <tr style="border-bottom: 1px solid {navy_blue}; color: {navy_blue}; font-weight: bold;">
                    <th style="padding: 8px; text-align: left;">Date</th>
                    <th style="padding: 8px; text-align: left;">Description</th>
                    <th style="padding: 8px; text-align: right;">Debit</th>
                    <th style="padding: 8px; text-align: right;">Credit</th>
                    <th style="padding: 8px; text-align: right;">Balance</th>
                </tr>
            """
            
            for _, row in temp_df.iterrows():
                html_statement += f"""
                <tr>
                    <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['Date']}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['Description']}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['Debit']:,.0f}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['Credit']:,.0f}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{row['Balance']:,.0f}</td>
                </tr>
                """
            html_statement += "</table>"

        # 4. FINAL GRAND TOTAL SECTION
        html_statement += f"""
            <div style="margin-top: 30px; padding: 20px; border: 2px solid {navy_blue}; border-radius: 8px; text-align: right; background-color: #f0f4ff;">
                <h2 style="margin: 0; color: {navy_blue};">GRAND TOTAL OUTSTANDING</h2>
                <h1 style="margin: 5px 0 0 0; color: #FF4B4B;">{grand_total_balance:,.0f} UGX</h1>
            </div>

            <div style="margin-top: 40px; text-align: center; font-size: 11px; color: #777;">
                <p>Zoe Consults SMC Ltd | Kampala, Uganda</p>
                <p><em>Trust is the foundation of our partnership.</em></p>
            </div>
        </div>
        """
        
        # --- DISPLAY THE HTML PREVIEW ---
        # ... (Your existing HTML generation logic above) ...
        
        # 4. DISPLAY THE PREVIEW (This was already in your code)
        st.components.v1.html(html_statement, height=1000, scrolling=True)

        # 5. ADD THE PRINT BUTTON (Move it here!)
        print_button_script = f"""
            <script>
                function printStatement() {{
                    var printContents = document.getElementById('printable-area').innerHTML;
                    var originalContents = document.body.innerHTML;
                    document.body.innerHTML = printContents;
                    window.print();
                    document.body.innerHTML = originalContents;
                    window.location.reload(); // Refreshes to restore Streamlit state
                }}
            </script>
            <div id="printable-area" style="display:none;">{html_statement}</div>
            <button onclick="printStatement()" style="
                background-color: #000080; color: white; border: none; 
                padding: 12px; border-radius: 5px; width: 100%; cursor: pointer; font-weight: bold;
            ">
                📥 Download / Print PDF Statement
            </button>
        """
        st.components.v1.html(print_button_script, height=100)

        st.info("💡 **Consolidated View:** All active and pending loans for this client are listed above.")
    


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





