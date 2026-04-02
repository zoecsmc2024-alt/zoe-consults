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
import re  # Added for ID parsing
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from fpdf import FPDF
from streamlit_calendar import calendar

# --- TOP OF YOUR SCRIPT ---
# 1. DEFINE SCOPES
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "Zoe_Consults_Data"

# 2. INITIALIZE CONNECTION (MATCHING YOUR IMPORTS)
try:
    # This uses the 'Credentials' you already imported at the top!
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds) 
    
    # Check if the connection works immediately
    # sheet_test = client.open(SHEET_NAME) 
except Exception as e:
    st.error(f"❌ Connection to Google Sheets failed: {e}")
    st.info("Check your 'gcp_service_account' in Streamlit Secrets.")
    st.stop()

# 1. MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="Zoe Admin", layout="wide", initial_sidebar_state="expanded")

# 2. BRANDING COLORS
BRANDING = {
    "navy": "#2B3F87",      # Primary Header / Buttons
    "baby_blue": "#F0F8FF", # Row Highlights / Hover
    "white": "#FFFFFF",     # Backgrounds
    "text_gray": "#666666"  # Captions / Timestamps
}

SHEET_ID = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"
# 3. GLOBAL DATA LOADER (RE-CHECKING CLIENT)
@st.cache_resource
def connect_to_gsheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def open_main_sheet():
    client = connect_to_gsheets()
    return client.open_by_key(SHEET_ID)

@st.cache_data(ttl=600)
def get_cached_data(worksheet_name):
    try:
        sheet = open_main_sheet()
        data = sheet.worksheet(worksheet_name).get_all_records()
        df = pd.DataFrame(data)
        return df.dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"⚠️ Error loading {worksheet_name}: {e}")
        return pd.DataFrame()
# ==============================
# 1. BRANDING & COLOR PALETTE
# ==============================
BRANDING = {
    "navy": "#2B3F87",      # Primary Header / Buttons
    "baby_blue": "#F0F8FF", # Row Highlights / Hover
    "white": "#FFFFFF",     # Backgrounds
    "text_gray": "#666666"  # Captions / Timestamps
}

# ==============================
# 2. GLOBAL STYLER
# ==============================
def apply_custom_styles():
    """
    Applies the Zoe Consults branding to the Streamlit UI.
    Maintains navy sidebar and specific button hover logic.
    """
    st.markdown(f"""
        <style>
            /* Sidebar Background */
            [data-testid="stSidebar"] {{
                background-color: {BRANDING['navy']};
            }}
            
            /* Sidebar Text/Icons */
            [data-testid="stSidebar"] * {{
                color: white !important;
            }}
            
            /* Active Tab Highlight */
            .st-bb {{ border-bottom-color: {BRANDING['navy']}; }}
            .st-at {{ background-color: {BRANDING['baby_blue']}; }}
            
            /* Main App Buttons */
            .stButton>button {{
                background-color: {BRANDING['navy']};
                color: white;
                border-radius: 8px;
                border: none;
                padding: 0.5rem 1rem;
                transition: all 0.3s ease;
            }}
            
            /* Button Hover Effects */
            .stButton>button:hover {{
                background-color: #1a285e;
                color: {BRANDING['baby_blue']};
                border: none;
            }}

            /* Card-like containers (Metric Boxes) */
            div[data-testid="stMetric"] {{
                background-color: white;
                border: 1px solid #ddd;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            }}
        </style>
    """, unsafe_allow_html=True)

# ==============================
# 1. GLOBAL SETTINGS & AUTH
# ==============================
SHEET_ID = "1XV1k6EuPLVo5TlmrNAq3FAVGTtCmJQKupF3HrFxLcwg"

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
    """Generates a PDF from HTML content using pisa."""
    from xhtml2pdf import pisa # Local import to ensure compatibility
    pdf_buffer = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html_content), dest=pdf_buffer)
    return pdf_buffer.getvalue()

# Ensure your client is initialized at the top of the script
# client = gspread.authorize(creds) 


@st.cache_data(ttl=3600)
def get_logo():
    """
    Fetches the logo once per hour to avoid API quota issues.
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

def save_data(worksheet_name, dataframe):
    """
    Overwrites a worksheet and forces the app to refresh its cache.
    """
    try:
        sheet = open_main_sheet()
        worksheet = sheet.worksheet(worksheet_name)
        worksheet.clear()
        
        # Prepare data: Convert everything to strings to ensure GSheets compatibility
        data_to_upload = [dataframe.columns.values.tolist()] + dataframe.astype(str).values.tolist()
        worksheet.update(data_to_upload)
        
        # 🔥 Clear cache so the next 'get_cached_data' pull is fresh
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
    """
    Fast password verification with error handling.
    Safely compares plain text input against a stored hash.
    """
    try:
        # If using bcrypt, ensure we are comparing bytes to bytes
        return bcrypt.checkpw(input_password.encode(), stored_hash.encode())
    except Exception:
        return False

def check_session_timeout():
    """
    Quietly monitors inactivity. 
    If the user is gone too long, it wipes the session state for safety.
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
        keys_to_clear = ["logged_in", "user", "role", "last_activity", "page"]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.warning("⏳ Session expired for security. Please login again.")
        st.rerun()
    
    # Update timestamp quietly on every interaction
    st.session_state.last_activity = now

# ==============================
# 5. THE LOGIN INTERFACE
# ==============================

def login_page():
    """
    A clean, centered login page.
    Note: sidebar() call is omitted here to prevent UI 'flickering' for logged-out users.
    """
    # Apply global styles for branding on login
    apply_custom_styles()
    
    st.markdown("<h2 style='text-align: center; color: #2B3F87;'>🔐 LOGIN</h2>", unsafe_allow_html=True)
    
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
                    # Logic here can be expanded to check database/GSG values
                    st.error("❌ Access Denied. Check credentials.")

# ==============================
# 6. THE AUTH GATEKEEPER (Main Script Entry)
# ==============================

# This block ensures that no part of the app is visible unless logged in.
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    login_page()
    st.stop() # Prevents execution of the rest of the app
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
    # Initialize PDF
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
    
    # Safe data retrieval with formatting
    loan_id = loan_data.get('Loan_ID', 'N/A')
    start_date = loan_data.get('Start_Date', 'N/A')
    try:
        total_due = float(loan_data.get('Total_Repayable', 0))
    except (ValueError, TypeError):
        total_due = 0.0
    
    pdf.cell(0, 8, f"Loan ID: {loan_id}  |  Start Date: {start_date}", 0, 1)
    pdf.cell(0, 8, f"Total Repayable: {total_due:,.0f} UGX", 0, 1)
    pdf.ln(5)

    # --- TABLE HEADERS ---
    # Background for headers (Light Gray)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 9)
    
    # Table Column Widths: 25 + 65 + 30 + 30 + 35 = 185 total (Centered on A4)
    pdf.cell(25, 10, "Date", 1, 0, 'C', True)
    pdf.cell(65, 10, "Description", 1, 0, 'C', True)
    pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
    pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
    pdf.cell(35, 10, "Balance", 1, 1, 'C', True)

    # --- TABLE ROWS ---
    pdf.set_font("Arial", '', 8)
    for _, row in ledger_df.iterrows():
        # Ensure date is string and clean
        date_str = str(row.get('Date', ''))[:10]
        
        # Clean numeric values for formatting
        def clean_num(val):
            try: return float(val)
            except: return 0.0

        pdf.cell(25, 8, date_str, 1)
        pdf.cell(65, 8, str(row.get('Description', ''))[:40], 1) # Cap description length
        pdf.cell(30, 8, f"{clean_num(row.get('Debit', 0)):,.0f}", 1, 0, 'R')
        pdf.cell(30, 8, f"{clean_num(row.get('Credit', 0)):,.0f}", 1, 0, 'R')
        pdf.cell(35, 8, f"{clean_num(row.get('Balance', 0)):,.0f}", 1, 1, 'R')

    # Return the bytes for the download button
    # dest='S' returns the document as a string/bytes
    return pdf.output(dest='S').encode('latin-1')

# ==============================
# 8. SYSTEM & UI CONFIGURATION
# ==============================

# NOTE: st.set_page_config was moved to the very top of the script (Section 1) 
# to comply with Streamlit's "Must be first command" rule.

def apply_ui_theme():
    st.markdown("""
    <style>
        /* 1. PAGE LAYOUT: FULL WIDTH */
        .block-container {
            max-width: 100% !important;
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            padding-left: 5rem !important;
            padding-right: 5rem !important;
        }

        /* 2. MAIN APP BACKGROUND */
        .stApp {
            background-color: #F0F8FF !important; /* Baby Blue Page BG */
        }

        /* 3. THE DEEP BLUE SIDEBAR */
        [data-testid="stSidebar"] {
            background-color: #0A192F !important; /* Deep Midnight Blue */
            min-width: 260px !important;
        }

        /* Sidebar Branding Text */
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] p, [data-testid="stSidebar"] b {
            color: #F0F8FF !important;
        }

        /* 4. REMOVE BUTTON BOXES - TEXT ONLY NAV */
        section[data-testid="stSidebar"] .stButton > button {
            background-color: transparent !important;
            color: #F0F8FF !important; /* Baby Blue Text */
            border: none !important;     /* REMOVES THE BOX */
            box-shadow: none !important; /* REMOVES ANY GLOW/SHADOW */
            width: 100% !important;
            text-align: left !important;
            padding: 8px 15px !important;
            margin-bottom: 5px !important;
            font-size: 16px !important;
            font-weight: 400 !important;
            transition: all 0.3s ease !important;
        }

        /* Hover Effect: Text Glows & Slides Right Slightly */
        section[data-testid="stSidebar"] .stButton > button:hover {
            color: #FFFFFF !important; /* Brighter on hover */
            background-color: rgba(240, 248, 255, 0.1) !important; /* Very faint highlight */
            padding-left: 25px !important; /* Subtle "slide" effect */
            text-decoration: none !important;
        }

        /* Active Page Indicator (Optional - subtle underline) */
        section[data-testid="stSidebar"] .stButton > button:focus {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            background-color: transparent !important;
        }

        /* 5. METRIC CARDS (Clean Matching Style) */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E0E0E0 !important;
            border-left: 8px solid #0A192F !important; 
            border-radius: 12px !important;
            padding: 20px !important;
        }

        /* 6. HIDE THE DEFAULT OVERLAY ON HOVER */
        button:focus:not(:focus-visible) {
            outline: none !important;
            box-shadow: none !important;
        }
        
    </style>
    """, unsafe_allow_html=True)
# Execute the UI theme application
apply_ui_theme()
# ==============================
# 9. UTILITY FUNCTIONS (WhatsApp, Receipts, Logo)
# ==============================

def send_whatsapp(phone, msg):
    """
    Sends a WhatsApp message via Twilio.
    Wrapped in a try-block so the app doesn't crash if the internet blips.
    Ensures that secrets are pulled from st.secrets.
    """
    try:
        # Initializing Twilio Client
        client_tw = Client(st.secrets["TWILIO_SID"], st.secrets["TWILIO_TOKEN"])
        
        # Formatting phone number for international standards if necessary
        # (Assuming phone input comes in as '256...')
        target_phone = f'whatsapp:{phone}'
        
        client_tw.messages.create(
            from_='whatsapp:+14155238886', # Your Twilio Sandbox/Verified number
            body=msg,
            to=target_phone
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
        # Load current settings using our cached helper from Section 2
        settings = get_cached_data("Settings") 
        
        # Convert image to Base64 string for storage in a cell
        # Seeking to start of file to ensure full read
        image_file.seek(0)
        encoded = base64.b64encode(image_file.read()).decode()
        
        # Logic to update or append the 'logo' key
        if not settings.empty and "Key" in settings.columns:
            if "logo" in settings["Key"].values:
                settings.loc[settings["Key"] == "logo", "Value"] = encoded
            else:
                new_row = pd.DataFrame([{"Key": "logo", "Value": encoded}])
                settings = pd.concat([settings, new_row], ignore_index=True)
        else:
            # Create fresh settings if sheet is empty or columns missing
            settings = pd.DataFrame([{"Key": "logo", "Value": encoded}])
        
        # Save back to Google via our Section 2 helper
        success = save_data("Settings", settings)
        
        if success:
            # Force cache clear so the UI immediately reflects the new logo
            st.cache_data.clear() 
            return True
    except Exception as e:
        st.error(f"❌ Logo Save Error: {e}")
    return False

# NOTE: For the 'make_receipt' function, we will rely on the FPDF 
# logic established in Section 4 for visual consistency across 
# all Zoe Consults documents.

# ==============================
# 10. THE SIDEBAR NAVIGATION
# ==============================

def sidebar():
    """
    Main Navigation Sidebar for Zoe Admin.
    Handles branding, user info, and role-based access control.
    """
    # Safety Check: Ensure session state variables exist
    role = st.session_state.get("role", "Staff")
    user = st.session_state.get("user", "Guest")
    current_page = st.session_state.get("page", "Overview")

    # 1. THE LOGO LOADER (Uses Base64 from Google Sheets)
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
    
    # 2. BRANDING & USER INFO
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
    # Key: Display Name | Value: Icon Emoji
    menu = {
        "Overview": "📊", "Loans": "💵", "Borrowers": "👥", "Collateral": "🛡️",
        "Calendar": "📅", "Ledger": "📄", "Overdue Tracker": "🚨",
        "Payments": "💰", "Expenses": "📁", "PettyCash": "📉",
        "Payroll": "🧾", "Reports": "📈", "Settings": "⚙️"
    }
    
    # Restricted Pages for Admin Only
    restricted = ["Settings", "Reports", "Payroll"]

    for item, icon in menu.items():
        # Permission Check: Skip restricted items if user is not Admin
        if role != "Admin" and item in restricted:
            continue

        # Render Button. If clicked, update page state and rerun app.
        # 'type="secondary"' allows the CSS Click Fix from Section 5 to take effect.
        if st.sidebar.button(f"{icon} {item}", key=f"nav_{item}", use_container_width=True, type="secondary"):
            st.session_state.page = item
            st.rerun()

    # 4. LOGOUT (Clean & Simple)
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", key="logout_btn", use_container_width=True):
        # Clear all session state variables and return to login screen
        st.session_state.clear()
        st.rerun()

# ==============================
# 11. DASHBOARD LOGIC (OVERVIEW)
# ==============================

def show_overview():
    """
    Main Dashboard view. 
    Calculates portfolio metrics and renders visual analytics.
    """
    st.markdown("## 📊 Financial Dashboard")
    
    # 1. LOAD ALL DATA AT THE VERY START (The Fix for NameErrors)
    df = get_cached_data("Loans")
    pay_df = get_cached_data("Payments")
    exp_df = get_cached_data("Expenses") 

    if df.empty:
        st.info("No loan records found.")
        return

    # 2. TRANSLATE HEADERS IMMEDIATELY (The Fix for KeyErrors)
    # This turns "Amount Paid" into "Amount_Paid" so your math works across the app
    df.columns = df.columns.str.strip().str.replace(" ", "_")
    if not pay_df.empty:
        pay_df.columns = pay_df.columns.str.strip().str.replace(" ", "_")
    if not exp_df.empty:
        exp_df.columns = exp_df.columns.str.strip().str.replace(" ", "_")

    # 3. CLEAN DATA TYPES
    # Converting columns to numeric safely to prevent "TypeError" during summation
    df["Interest"] = pd.to_numeric(df.get("Interest", 0), errors="coerce").fillna(0)
    df["Amount_Paid"] = pd.to_numeric(df.get("Amount_Paid", 0), errors="coerce").fillna(0)
    df["Principal"] = pd.to_numeric(df.get("Principal", 0), errors="coerce").fillna(0)
    df["End_Date"] = pd.to_datetime(df.get("End_Date"), errors="coerce")
    
    today = pd.Timestamp.today().normalize()
    
    # RECOVERY FILTER: Include Rolled loans in Active count for accurate portfolio health
    active_statuses = ["Active", "Overdue", "Rolled/Overdue"]
    active_df = df[df["Status"].isin(active_statuses)].copy()

    # 4. METRICS CALCULATION
    total_issued = active_df["Principal"].sum() if "Principal" in active_df.columns else 0
    total_interest_expected = active_df["Interest"].sum()
    total_collected = df["Amount_Paid"].sum() 
    
    # Logic for Overdue Count: Past due date and not yet cleared
    overdue_mask = (active_df["End_Date"] < today) & (active_df["Status"] != "Cleared")
    overdue_count = active_df[overdue_mask].shape[0]

    # 5. METRICS ROW (Zoe Soft Blue Style)
    # Using raw HTML to maintain the specific border-left and shadow branding
    m1, m2, m3, m4 = st.columns(4)
    
    m1.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">💰 ACTIVE PRINCIPAL</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{total_issued:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
    m2.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">📈 EXPECTED INTEREST</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{total_interest_expected:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
    m3.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #2E7D32;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">✅ TOTAL COLLECTED</p><h3 style="margin:0;color:#2E7D32;font-size:18px;">{total_collected:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
    m4.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #FF4B4B;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:11px;color:#666;font-weight:bold;">🚨 OVERDUE FILES</p><h3 style="margin:0;color:#FF4B4B;font-size:18px;">{overdue_count}</h3></div>""", unsafe_allow_html=True)

    # 6. RECENT ACTIVITY TABLES
    st.write("---")
    t1, t2 = st.columns(2)

    with t1:
        st.markdown("<h4 style='color: #4A90E2;'>📝 Recent Portfolio Activity</h4>", unsafe_allow_html=True)
        rows_html = ""
        
        if not active_df.empty:
            recent_loans = active_df.sort_values(by="End_Date", ascending=False).head(5)
            for i, (idx, r) in enumerate(recent_loans.iterrows()):
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                b_name = r.get('Borrower', 'Unknown')
                p_amt = float(r.get('Principal', 0))
                b_stat = r.get('Status', 'Active')
                e_date_raw = r.get('End_Date')
                e_date = pd.to_datetime(e_date_raw).strftime('%d %b') if pd.notna(e_date_raw) else "-"

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
                p_date_raw = r.get('Date')
                p_date = pd.to_datetime(p_date_raw).strftime('%d %b') if pd.notna(p_date_raw) else "-"
                
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

    # 7. DASHBOARD VISUALS
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
        # Combined Cashflow Chart (Income vs Expenses)
        if not pay_df.empty and not exp_df.empty:
            pay_df["Date"] = pd.to_datetime(pay_df["Date"], errors='coerce')
            exp_df["Date"] = pd.to_datetime(exp_df["Date"], errors='coerce')
            
            # Formatting for grouping by Month-Year
            inc_m = pay_df.groupby(pay_df["Date"].dt.strftime('%b %Y'))["Amount"].sum().reset_index()
            exp_m = exp_df.groupby(exp_df["Date"].dt.strftime('%b %Y'))["Amount"].sum().reset_index()
            
            m_cash = pd.merge(inc_m, exp_m, on="Date", how="outer", suffixes=('_Inc', '_Exp')).fillna(0)
            m_cash.columns = ["Month", "Income", "Expenses"]
            
            fig_bar = px.bar(m_cash, x="Month", y=["Income", "Expenses"], barmode="group", title="Performance", color_discrete_map={"Income": "#2E7D32", "Expenses": "#FF4B4B"})
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#2B3F87")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("💡 Tip: Record both payments and expenses to see the performance chart.")
# ==============================
# 12. BORROWERS MANAGEMENT PAGE
# ==============================

def show_borrowers():
    """
    Manages borrower profiles. 
    Includes viewing, registering, auditing history, and profile modification.
    """
    st.markdown("<h2 style='color: #2B3F87;'>👥 Borrowers Management</h2>", unsafe_allow_html=True)
    
    # 1. FETCH DATA
    borrowers_df = get_cached_data("Borrowers")
    
    if borrowers_df is None or borrowers_df.empty:
        df = pd.DataFrame(columns=["Borrower_ID", "Name", "Phone", "Address", "National_ID", "Status"])
    else:
        df = borrowers_df.copy()

    # --- TABS ---
    tab_view, tab_add, tab_audit = st.tabs(["📑 View All", "➕ Add New", "⚙️ Audit & Manage"])

    # --- TAB 1: VIEW ALL ---
    with tab_view:
        col1, col2 = st.columns([3, 1]) 
        with col1:
            search = st.text_input("🔍 Search Name or Phone", placeholder="Type to filter...", key="bor_search").lower()
        with col2:
            status_filter = st.selectbox("Filter Status", ["All", "Active", "Inactive"], key="bor_status_filt")

        filtered_df = df.copy()
        if not filtered_df.empty:
            filtered_df["Name"] = filtered_df["Name"].astype(str)
            filtered_df["Phone"] = filtered_df["Phone"].astype(str)
            mask = (filtered_df["Name"].str.lower().str.contains(search, na=False) | 
                    filtered_df["Phone"].str.contains(search, na=False))
            filtered_df = filtered_df[mask]
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df["Status"] == status_filter]

            if not filtered_df.empty:
                rows_html = ""
                for i, r in filtered_df.reset_index().iterrows():
                    bg_color = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                    rows_html += f"""
                    <tr style="background-color: {bg_color}; border-bottom: 1px solid #ddd;">
                        <td style="padding:12px;"><b>{r['Name']}</b></td>
                        <td style="padding:12px;">{r['Phone']}</td>
                        <td style="padding:12px; font-size: 11px; color:#666;">{r.get('National_ID', 'N/A')}</td>
                        <td style="padding:12px; text-align:center;">
                            <span style="background:#4A90E2; color:white; padding:3px 8px; border-radius:12px; font-size:10px;">{r['Status']}</span>
                        </td>
                    </tr>"""
                st.markdown(f"<div style='border:2px solid #4A90E2; border-radius:10px; overflow:hidden; margin-top:20px;'><table style='width:100%; border-collapse:collapse; font-family:sans-serif; font-size:13px;'><thead><tr style='background:#4A90E2; color:white; text-align:left;'><th style='padding:12px;'>Borrower Name</th><th style='padding:12px;'>Phone</th><th style='padding:12px;'>National ID</th><th style='padding:12px; text-align:center;'>Status</th></tr></thead><tbody>{rows_html}</tbody></table></div>", unsafe_allow_html=True)

    # --- TAB 2: ADD BORROWER ---
    with tab_add:
        with st.form("add_borrower_form", clear_on_submit=True):
            st.markdown("<h4 style='color: #4A90E2;'>📝 Register New Borrower</h4>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name*")
            phone = c2.text_input("Phone Number*")
            nid = c1.text_input("National ID / NIN")
            addr = c2.text_input("Physical Address")
            if st.form_submit_button("🚀 Save Borrower Profile", use_container_width=True):
                if name and phone:
                    new_id = int(df["Borrower_ID"].max() + 1) if not df.empty else 1
                    new_entry = pd.DataFrame([{"Borrower_ID": new_id, "Name": name, "Phone": phone, "National_ID": nid, "Address": addr, "Status": "Active", "Date_Added": datetime.now().strftime("%Y-%m-%d")}])
                    if save_data("Borrowers", pd.concat([df, new_entry], ignore_index=True)):
                        st.success(f"✅ {name} registered!"); st.rerun()

    # --- TAB 3: AUDIT & MANAGE ---
    with tab_audit:
        if not df.empty:
            target_name = st.selectbox("Select Borrower to Audit/Manage", df["Name"].tolist(), key="audit_manage_select")
            
            # Identify specific borrower record
            borrower_idx = df[df["Name"] == target_name].index[0]
            b_data = df.loc[borrower_idx]
            
            # --- SHOW LOAN HISTORY ---
            u_loans = get_cached_data("Loans").copy()
            # Clean headers for consistency
            u_loans.columns = [str(c).strip().replace(" ", "_") for c in u_loans.columns]
            
            if "Borrower" in u_loans.columns:
                user_loans = u_loans[u_loans["Borrower"] == target_name].copy()
                if not user_loans.empty:
                    st.metric("Total Loans Found", len(user_loans))
                    # Convert headers back for display table
                    display_history = user_loans[["Loan_ID", "Status", "Principal", "End_Date"]].copy()
                    display_history.columns = ["Loan ID", "Status", "Principal", "End Date"]
                    st.table(display_history)
                else:
                    st.info("ℹ️ No loans recorded for this borrower yet.")

            st.markdown("---")
            st.markdown("### ⚙️ Modify Borrower Details")
            
            # --- 1. EDIT FORM SECTION ---
            with st.expander(f"📝 Edit Profile: {target_name}"):
                with st.form(f"edit_bor_{target_name}"):
                    c1, c2 = st.columns(2)
                    
                    e_name = c1.text_input("Full Name", value=str(b_data['Name']))
                    e_phone = c1.text_input("Phone Number", value=str(b_data['Phone']))
                    e_nid = c1.text_input("National ID / NIN", value=str(b_data.get('National_ID', '')))
                    
                    e_email = c2.text_input("Email Address", value=str(b_data.get('Email', '')))
                    e_kin = c2.text_input("Next of Kin", value=str(b_data.get('Next_of_Kin', '')))
                    
                    status_idx = 0 if b_data['Status'] == "Active" else 1
                    e_status = c2.selectbox("Account Status", ["Active", "Inactive"], index=status_idx)
                    e_addr = st.text_input("Physical Address", value=str(b_data.get('Address', '')))
                    
                    if st.form_submit_button("💾 Save Updated Profile", use_container_width=True):
                        df.at[borrower_idx, 'Name'] = e_name
                        df.at[borrower_idx, 'Phone'] = e_phone
                        df.at[borrower_idx, 'National_ID'] = e_nid
                        df.at[borrower_idx, 'Email'] = e_email
                        df.at[borrower_idx, 'Next_of_Kin'] = e_kin
                        df.at[borrower_idx, 'Status'] = e_status
                        df.at[borrower_idx, 'Address'] = e_addr
                        
                        if save_data("Borrowers", df):
                            st.success(f"✅ {e_name}'s profile has been updated!")
                            st.rerun()

            # --- 2. DELETE ACTION SECTION ---
            st.markdown("### ⚠️ Danger Zone")
            if st.button(f"🗑️ Delete {target_name} Permanently", key=f"del_btn_{target_name}"):
                # Relationship Safety Check
                has_loans = False
                if not u_loans.empty and "Borrower" in u_loans.columns:
                    has_loans = not u_loans[u_loans["Borrower"] == target_name].empty

                if has_loans:
                    st.error("❌ Cannot delete! This borrower has loan records in the system. Close all loans first.")
                else:
                    new_df = df.drop(borrower_idx)
                    if save_data("Borrowers", new_df):
                        st.warning(f"⚠️ {target_name} removed from system.")
                        st.rerun()


# ==============================
# 13. LOANS MANAGEMENT PAGE (Luxe Edition)
# ==============================

def show_loans():
    """
    Core engine for issuing and managing loan agreements.
    Features Midnight Blue branding, Start Date tracking, and formatted currency.
    """
    st.markdown("<h2 style='color: #0A192F;'>💵 Loans Management</h2>", unsafe_allow_html=True)
    
    # 1. LOAD & NORMALIZE DATA
    loans_df = get_cached_data("Loans")
    borrowers_df = get_cached_data("Borrowers")
    
    if borrowers_df is not None and not borrowers_df.empty:
        borrowers_df.columns = [str(c).strip().replace(" ", "_") for c in borrowers_df.columns]
        active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]
    else:
        active_borrowers = pd.DataFrame()
    
    if loans_df is None or loans_df.empty:
        loans_df = pd.DataFrame(columns=["Loan_ID", "Borrower", "Principal", "Interest", "Total_Repayable", "Amount_Paid", "Balance", "Status", "Start_Date", "End_Date"])
    
    loans_df.columns = [str(col).strip().replace(" ", "_") for col in loans_df.columns]

    # Clean numeric columns for math and comma formatting
    num_cols = ["Principal", "Interest", "Total_Repayable", "Amount_Paid", "Balance"]
    for col in num_cols:
        if col in loans_df.columns:
            loans_df[col] = pd.to_numeric(loans_df[col], errors='coerce').fillna(0)

    # Auto-Calc Balance
    loans_df["Balance"] = loans_df["Total_Repayable"] - loans_df["Amount_Paid"]
    
    tab_view, tab_add, tab_manage, tab_actions = st.tabs(["📑 Portfolio View", "➕ New Loan", "🛠️ Manage/Edit", "⚙️ Actions"])

    # ==============================
    # TAB: PORTFOLIO VIEW (Restored Peach Luxe Theme)
    # ==============================
    with tab_view:
        if not loans_df.empty:
            display_df = loans_df.copy()
            display_df["Loan_ID"] = display_df["Loan_ID"].astype(str).str.replace(".0", "", regex=False)
            
            # Show all records (Persistence for Christine!)
            active_view = display_df.copy()

            if active_view.empty:
                st.info("ℹ️ No loan records found.")
            else:
                # 1. SELECT LOAN FOR INSPECTION CARDS
                sel_id = st.selectbox("🔍 Select Loan to Inspect", active_view["Loan_ID"].unique(), key="inspect_sel_v5")
                loan_info = active_view[active_view["Loan_ID"] == sel_id].iloc[0]
                
                # 2. BRANDED METRIC CARDS (Restored Peach/Navy Blend)
                c1, c2, c3 = st.columns(3)
                
                # Logic values
                rec_val = float(loan_info.get('Amount_Paid', 0))
                out_val = float(loan_info.get('Balance', 0))
                stat_val = str(loan_info.get('Status', 'Active')).upper()

                # Using that warm Peachish/Alice background for cards
                card_style = "background-color:#FFF9F5; padding:20px; border-radius:15px; border-left:10px solid #0A192F; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"
                text_style = "margin:0; color:#0A192F;"

                c1.markdown(f"""<div style="{card_style}"><p style="{text_style} font-size:11px; font-weight:bold;">✅ RECEIVED</p><h3 style="{text_style} font-size:18px;">{rec_val:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
                c2.markdown(f"""<div style="{card_style}"><p style="{text_style} font-size:11px; font-weight:bold;">🚨 OUTSTANDING</p><h3 style="{text_style} font-size:18px;">{out_val:,.0f} <span style="font-size:10px;">UGX</span></h3></div>""", unsafe_allow_html=True)
                c3.markdown(f"""<div style="{card_style}"><p style="{text_style} font-size:11px; font-weight:bold;">📑 STATUS</p><h3 style="{text_style} font-size:18px;">{stat_val}</h3></div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # --- 3. THE LUXE ROW & BADGE STYLING ---
                def style_loan_table(row):
                    # Default row color (Peachish-White)
                    bg_color = "#FFF9F5" 
                    
                    # Logic for the Status column Badges
                    status = row["Status"]
                    if status == "Active": s_color = "#4A90E2"      # Baby Blue
                    elif status == "Closed": s_color = "#2E7D32"    # Emerald Green
                    elif status == "Overdue": s_color = "#FF4B4B"   # Hot Red
                    elif "Rolled" in str(status): s_color = "#FFA500" # Orange
                    else: s_color = "#666666"

                    # Build the styles
                    styles = [f'background-color: {bg_color}; color: #0A192F;'] * len(row)
                    # Overwrite the Status column with a Badge look
                    status_idx = row.index.get_loc("Status")
                    styles[status_idx] = f'background-color: {s_color}; color: white; font-weight: bold; border-radius: 5px;'
                    return styles

                # 4. PREP DATA
                show_cols = ["Loan_ID", "Borrower", "Principal", "Balance", "Status"]
                for d_col in ["Start_Date", "Start Date", "End_Date", "End Date"]:
                    if d_col in active_view.columns: show_cols.append(d_col)
                
                final_table = active_view[show_cols].copy()

                for col in ["Principal", "Balance"]:
                    if col in final_table.columns:
                        final_table[col] = pd.to_numeric(final_table[col], errors='coerce').fillna(0)

                # 5. RENDER THE PEACHY TABLE
                st.dataframe(
                    final_table.style.format({
                        "Principal": "{:,.0f}",
                        "Balance": "{:,.0f}"
                    }).apply(style_loan_table, axis=1), # Apply peach rows & status badges
                    use_container_width=True, 
                    hide_index=True
                )
    # ==============================
    # TAB: NEW LOAN (Standardized)
    # ==============================
    with tab_add:
        if active_borrowers.empty:
            st.info("💡 Tip: Activate a borrower in the 'Borrowers' section.")
        else:
            with st.form("loan_issue_form"):
                st.markdown("<h4 style='color: #0A192F;'>📝 Create New Loan Agreement</h4>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                selected_borrower = col1.selectbox("Select Borrower", active_borrowers["Name"].unique())
                amount = col1.number_input("Principal Amount (UGX)", min_value=0, step=50000)
                date_issued = col1.date_input("Start Date", value=datetime.now())
                
                l_type = col2.selectbox("Loan Type", ["Business", "Personal", "Emergency", "Other"])
                interest_rate = col2.number_input("Monthly Interest Rate (%)", min_value=0.0, step=0.5)
                date_due = col2.date_input("Due Date", value=date_issued + timedelta(days=30))

                interest = (interest_rate / 100) * amount
                total_due = amount + interest
                
                st.markdown(f"""<div style="background-color: #F0F8FF; padding: 10px; border-radius: 8px; border-left: 5px solid #0A192F;"><p style="margin:0; color:#0A192F;"><b>Preview:</b> Total Repayable will be <b>{total_due:,.0f} UGX</b></p></div>""", unsafe_allow_html=True)

                if st.form_submit_button("🚀 Confirm & Issue Loan", use_container_width=True):
                    if amount > 0:
                        last_id = pd.to_numeric(loans_df["Loan_ID"], errors='coerce').max()
                        new_id = int(last_id + 1) if pd.notna(last_id) else 1
                        
                        new_loan = pd.DataFrame([{
                            "Loan_ID": new_id, "Borrower": selected_borrower, "Type": l_type,
                            "Principal": float(amount), "Interest": float(interest),
                            "Total_Repayable": float(total_due), "Amount_Paid": 0.0,
                            "Status": "Active", "Start_Date": date_issued.strftime("%Y-%m-%d"),
                            "End_Date": date_due.strftime("%Y-%m-%d")
                        }])
                        
                        updated_df = pd.concat([loans_df, new_loan], ignore_index=True).fillna(0)
                        # Restore spaces for Google Sheets save
                        final_save = updated_df.copy()
                        final_save.columns = [c.replace("_", " ") for c in final_save.columns]
                        
                        if save_data("Loans", final_save):
                            st.success(f"✅ Loan #{new_id} issued to {selected_borrower}!")
                            st.rerun()

    # (Keep Manage/Edit and Actions tabs exactly as they were...)
    # ... (Keep Manage/Edit and Actions tabs exactly as they were) ...
    # ==============================
    # TAB: MANAGE / EDIT LOANS (Safety Fix)
    # ==============================
    with tab_manage:
        st.markdown("### 🛠️ Modify Loan Agreement")
        m_df = loans_df.copy()
        
        if m_df.empty:
            st.info("ℹ️ No loans available to edit.")
        else:
            m_df['Loan_ID'] = m_df['Loan_ID'].fillna("0").astype(str).str.replace(".0", "", regex=False)
            m_options = [f"ID: {r['Loan_ID']} | {r['Borrower']}" for _, r in m_df.iterrows()]
            
            selected_m = st.selectbox("🔍 Select Loan to Manage", m_options, key="manage_sel_box_v3")
            
            # Parsing ID safely
            import re
            match = re.search(r'ID:\s*(\d+)', str(selected_m))
            clean_id = match.group(1) if match else "0"
            
            loan_row = m_df[m_df["Loan_ID"] == clean_id].iloc[0]

            # --- THE FORM START ---
            with st.form("edit_loan_form_luxe"):
                c1, c2 = st.columns(2)
                up_name = c1.text_input("Borrower Name", value=str(loan_row.get('Borrower', '')))
                up_p = c1.number_input("Principal", value=float(loan_row.get('Principal', 0)))
                up_paid = c1.number_input("Amount Paid", value=float(loan_row.get('Amount_Paid', 0)))
                
                status_list = ["Active", "Overdue", "Rolled/Overdue", "Closed", "Defaulted"]
                curr_s = str(loan_row.get('Status', 'Active')).strip()
                up_status = c2.selectbox("Status", status_list, index=status_list.index(curr_s) if curr_s in status_list else 0)
                
                # --- DATE SAFETY FIX (Prevents ValueError) ---
                try:
                    # Try to parse the date from the sheet
                    raw_date = loan_row.get('End_Date')
                    if pd.isna(raw_date) or raw_date == "":
                        current_end = datetime.now().date()
                    else:
                        current_end = pd.to_datetime(raw_date).date()
                except:
                    # Fallback to today if it fails
                    current_end = datetime.now().date()
                
                up_end = c2.date_input("End Date", value=current_end)

                # --- SUBMIT BUTTONS MUST BE INSIDE THE FORM ---
                b_save = st.form_submit_button("💾 Save Changes", use_container_width=True)

                if b_save:
                    # Logic to find the row index in the original loans_df
                    # (Standardizing ID column check)
                    id_check_col = "Loan_ID" if "Loan_ID" in loans_df.columns else "Loan ID"
                    idx = loans_df[loans_df[id_check_col].astype(str).str.replace(".0", "", regex=False) == clean_id].index[0]
                    
                    loans_df.at[idx, 'Borrower'] = up_name
                    loans_df.at[idx, 'Principal'] = up_p
                    loans_df.at[idx, 'Amount_Paid'] = up_paid
                    loans_df.at[idx, 'Status'] = up_status
                    loans_df.at[idx, 'End_Date'] = up_end.strftime('%Y-%m-%d')
                    
                    # Restore spaces for Google Sheets save
                    final_save_df = loans_df.copy()
                    final_save_df.columns = [c.replace("_", " ") for c in final_save_df.columns]
                    
                    if save_data("Loans", final_save_df):
                        st.success("✅ Updated Successfully!")
                        st.rerun()

            # --- DELETE BUTTON (Outside the Edit Form for safety) ---
            st.markdown("---")
            if st.button("🗑️ Delete Permanently", use_container_width=True, key="del_loan_btn"):
                id_check_col = "Loan_ID" if "Loan_ID" in loans_df.columns else "Loan ID"
                new_df = loans_df[loans_df[id_check_col].astype(str).str.replace(".0", "", regex=False) != clean_id]
                
                # Restore spaces for Google Sheets save
                final_save_df = new_df.copy()
                final_save_df.columns = [c.replace("_", " ") for c in final_save_df.columns]
                
                if save_data("Loans", final_save_df):
                    st.warning(f"⚠️ Loan #{clean_id} deleted.")
                    st.rerun()
    with tab_actions:
        st.info("⚙️ Loan Settlements and Rollover actions will appear here in the next update.")
            # ==============================
# 14. PAYMENTS & COLLECTIONS PAGE (Upgraded)
# ==============================

def show_payments():
    """
    Manages cash inflows. Includes payment posting, 
    automatic loan status updating, and visual history logs.
    """
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
        # Standardize column headers for logic processing
        loans_df.columns = loans_df.columns.str.strip().str.replace(" ", "_")
        active_loans = loans_df[loans_df["Status"].astype(str).str.lower() != "closed"].copy()
        
        if active_loans.empty:
            st.success("🎉 All loans are currently cleared!")
        else:
            # 1. Selection logic with Safe ID parsing
            active_loans['Loan_ID'] = active_loans['Loan_ID'].fillna("0").astype(str).str.replace(".0", "", regex=False)
            
            loan_options = active_loans.apply(
                lambda x: f"ID: {x.get('Loan_ID', 'N/A')} - {x.get('Borrower', 'Unknown')}", 
                axis=1
            ).tolist()
            
            selected_option = st.selectbox("Select Loan to Credit", loan_options, key="payment_selector_unique")
            
            # Safe Parsing of the ID from selection string
            try:
                raw_id = selected_option.split(" - ")[0].replace("ID: ", "")
                selected_id_str = str(raw_id).strip()
                loan = active_loans[active_loans["Loan_ID"] == selected_id_str].iloc[0]
            except Exception as e:
                st.error(f"❌ Error parsing Loan ID: {e}")
                st.stop()

            # 2. Financial Calculations
            total_rep = float(loan.get("Total_Repayable", 0))
            if total_rep == 0:
                total_rep = float(loan.get("Principal", 0)) + float(loan.get("Interest", 0))

            paid_so_far = pd.to_numeric(loan.get("Amount_Paid", 0), errors='coerce') or 0.0
            outstanding = total_rep - paid_so_far

            # --- STYLED CARDS ---
            c1, c2, c3 = st.columns(3)
            status_val = str(loan.get('Status', 'Active')).strip()
            status_color = "#2E7D32" if status_val == "Active" else "#FF4B4B"
            
            c1.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">CLIENT</p><h3 style="margin:0; color:#2B3F87; font-size:18px;">{loan['Borrower']}</h3></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">BALANCE DUE</p><h3 style="margin:0; color:#FF4B4B; font-size:18px;">{outstanding:,.0f} <span style="font-size:12px;">UGX</span></h3></div>""", unsafe_allow_html=True)
            c3.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid {status_color}; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">STATUS</p><h3 style="margin:0; color:{status_color}; text-transform:uppercase; font-size:18px;">{status_val}</h3></div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- PAYMENT FORM ---
            with st.form("payment_form", clear_on_submit=True):
                col_a, col_b, col_c = st.columns(3)
                pay_amount = col_a.number_input("Amount Received (UGX)", min_value=0, step=10000)
                pay_method = col_b.selectbox("Method", ["Mobile Money", "Cash", "Bank Transfer", "Cheque"])
                pay_date = col_c.date_input("Payment Date", value=datetime.now())
                
                if st.form_submit_button("✅ Post Payment", use_container_width=True):
                    if pay_amount > 0:
                        try:
                            # 1. Standardize the Loans ID lookup
                            loans_df['Loan_ID'] = loans_df['Loan_ID'].astype(str).str.replace(".0", "", regex=False).str.strip()
                            search_id = str(selected_id_str).strip()
                            idx = loans_df[loans_df["Loan_ID"] == search_id].index[0]

                            # 2. MATCH YOUR SHEET HEADERS EXACTLY (The Fix!)
                            p_id_col = "Payment ID"
                            last_p_id = pd.to_numeric(payments_df[p_id_col], errors='coerce').fillna(0).max() if not payments_df.empty else 0
                            
                            new_payment = pd.DataFrame([{
                                "Payment ID": int(last_p_id + 1),
                                "Loan ID": search_id,
                                "Borrower": loan["Borrower"],
                                "Amount": float(pay_amount),
                                "Date": pay_date.strftime("%Y-%m-%d"),
                                "Method": pay_method,
                                "Recorded By": st.session_state.get("user", "Zoe (Admin)")
                            }])

                            # 3. Update Loan Balance
                            new_total_paid = float(paid_so_far) + float(pay_amount)
                            loans_df.at[idx, "Amount_Paid"] = new_total_paid
                            if new_total_paid >= (total_rep - 10):
                                loans_df.at[idx, "Status"] = "Closed"

                            # 4. STRICT SYNC (Ensures no new columns are created)
                            save_payments = pd.concat([payments_df, new_payment], ignore_index=True)
                            expected_cols = ["Payment ID", "Loan ID", "Borrower", "Amount", "Date", "Method", "Recorded By"]
                            save_payments = save_payments[expected_cols].fillna("") 
                            
                            save_loans = loans_df.copy()
                            save_loans.columns = [c.replace("_", " ") for c in save_loans.columns]
                            
                            if save_data("Payments", save_payments) and save_data("Loans", save_loans.fillna(0)):
                                st.success("✅ Payment recorded successfully!")
                                st.cache_data.clear()
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"🚨 Error: {str(e)}")
                    else:
                        st.error(f"⚠️ Invalid amount. Balance due is {outstanding:,.0f} UGX.")
    # ==============================
    # TAB 2: HISTORY (Color via Emojis)
    # ==============================
    with tab_history:
        if not payments_df.empty:
            df_display = payments_df.copy()
            df_display["Amount"] = pd.to_numeric(df_display.get("Amount", 0), errors="coerce").fillna(0)
            
            def get_color_emoji(amt):
                if amt >= 5000000: return "🟢 Large"
                if amt >= 1000000: return "🔵 Medium"
                return "⚪ Small"
            
            df_display["Level"] = df_display["Amount"].apply(get_color_emoji)
            df_display = df_display.sort_values("Date", ascending=False)
            
            cols = ["Level"] + [c for c in df_display.columns if c != "Level"]
            st.dataframe(df_display[cols], use_container_width=True, hide_index=True)
        else:
            st.info("No payment records found.")

    # ==============================
    # TAB: EDIT / DELETE PAYMENTS (The Payment-Only Fix)
    # ==============================
    with tab_manage:
        st.markdown("### 🛠️ Modify Payment Records")
        
        if payments_df.empty:
            st.info("ℹ️ No payments recorded to manage.")
        else:
            # 1. Standardize IDs
            p_id_col = "Payment_ID" if "Payment_ID" in payments_df.columns else "Payment ID"
            m_p_df = payments_df.copy()
            m_p_df[p_id_col] = m_p_df[p_id_col].fillna(0).astype(str).str.replace(".0", "", regex=False)
            
            # Create a selection list
            p_options = [f"Receipt: {r[p_id_col]} | {r['Borrower']} - {float(r['Amount']):,.0f} UGX" for _, r in m_p_df.iterrows()]
            selected_p = st.selectbox("🔍 Select Receipt to Edit/Delete", p_options, key="edit_pay_sel")
            
            # Extract ID
            import re
            p_match = re.search(r'Receipt:\s*(\d+)', str(selected_p))
            p_clean_id = p_match.group(1) if p_match else "0"
            
            p_row = m_p_df[m_p_df[p_id_col] == p_clean_id].iloc[0]

            # --- THE PAYMENT FORM ---
            with st.form("edit_payment_form_luxe"):
                st.info(f"Editing Receipt #{p_clean_id} for {p_row['Borrower']}")
                c1, c2 = st.columns(2)
                
                new_p_amt = c1.number_input("Adjust Amount (UGX)", value=float(p_row.get('Amount', 0)))
                new_p_date = c2.date_input("Adjust Date", value=pd.to_datetime(p_row.get('Date')).date())
                new_p_method = st.selectbox("Update Method", ["Cash", "Mobile Money", "Bank Transfer"], index=0)

                # --- SAVE BUTTON ---
                if st.form_submit_button("💾 Save Payment Changes", use_container_width=True):
                    # Find and update row in payments_df
                    p_idx = payments_df[payments_df[p_id_col].astype(str).str.replace(".0", "", regex=False) == p_clean_id].index[0]
                    
                    payments_df.at[p_idx, 'Amount'] = new_p_amt
                    payments_df.at[p_idx, 'Date'] = new_p_date.strftime('%Y-%m-%d')
                    payments_df.at[p_idx, 'Method'] = new_p_method
                    
                    # Clean headers for save
                    save_pay_df = payments_df.copy()
                    save_pay_df.columns = [c.replace("_", " ") for c in save_pay_df.columns]
                    
                    if save_data("Payments", save_pay_df):
                        st.success(f"✅ Receipt #{p_clean_id} updated! Remember to check the Loan Balance if you changed the amount.")
                        st.cache_data.clear()
                        st.rerun()

            # --- DELETE BUTTON ---
            st.markdown("---")
            if st.button("🗑️ Delete Receipt Permanently", use_container_width=True):
                new_pay_df = payments_df[payments_df[p_id_col].astype(str).str.replace(".0", "", regex=False) != p_clean_id]
                
                # Clean headers for save
                save_pay_df = new_pay_df.copy()
                save_pay_df.columns = [c.replace("_", " ") for c in save_pay_df.columns]
                
                if save_data("Payments", save_pay_df):
                    st.warning(f"⚠️ Receipt #{p_clean_id} has been deleted.")
                    st.cache_data.clear()
                    st.rerun()
    
# ==============================
# 15. COLLATERAL MANAGEMENT PAGE
# ==============================

def show_collateral():
    """
    Handles asset security for loans. Includes asset registration,
    inventory tracking, and status management (Held/Released).
    """
    st.markdown("<h2 style='color: #2B3F87;'>🛡️ Collateral Management</h2>", unsafe_allow_html=True)
    
    # 1. FETCH ALL DATA
    collateral_df = get_cached_data("Collateral")
    loans_df = get_cached_data("Loans") 
    
    # 2. INITIALIZE & NORMALIZE
    if collateral_df.empty:
        collateral_df = pd.DataFrame(columns=[
            "Collateral_ID", "Borrower", "Loan_ID", "Type", 
            "Description", "Value", "Status", "Date_Added", "Photo_Link"
        ])
    else:
        # Standardize Collateral Headers
        collateral_df.columns = collateral_df.columns.str.strip().str.replace(" ", "_")

    # Standardize Loan Headers so we can find 'Loan_ID' reliably
    if not loans_df.empty:
        loans_df.columns = loans_df.columns.str.strip().str.replace(" ", "_")

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_reg, tab_view = st.tabs(["➕ Register Asset", "📋 Inventory & Status"])

    # --- TAB 1: REGISTER COLLATERAL ---
    with tab_reg:
        if loans_df.empty:
            st.warning("⚠️ No loans found. Issue a loan before adding collateral.")
        else:
            # Filter for active loans requiring security
            active_loan_mask = loans_df["Status"].isin(["Active", "Overdue", "Rolled/Overdue"])
            available_loans = loans_df[active_loan_mask].copy()

            if available_loans.empty:
                st.info("✅ All current loans are cleared. No assets need to be held.")
            else:
                with st.form("collateral_form", clear_on_submit=True):
                    st.markdown("<h4 style='color: #2B3F87;'>🔒 Secure New Asset</h4>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    
                    # Safe Dropdown Creation
                    available_loans['Loan_ID'] = available_loans['Loan_ID'].astype(str).str.replace(".0", "", regex=False)
                    loan_options = available_loans.apply(lambda x: f"ID: {x['Loan_ID']} - {x.get('Borrower', 'Unknown')}", axis=1).tolist()
                    
                    selected_loan = c1.selectbox("Link to Active Loan", loan_options)
                    
                    # Parse Selection to extract IDs
                    sel_id = selected_loan.split(" - ")[0].replace("ID: ", "")
                    sel_borrower = selected_loan.split(" - ")[1]

                    asset_type = c2.selectbox("Asset Type", ["Logbook (Car)", "Land Title", "Electronics", "House Deed", "Other"])
                    desc = st.text_input("Asset Description", placeholder="e.g. Toyota Prado UBA 123X Black")
                    est_value = st.number_input("Estimated Value (UGX)", min_value=0, step=100000)

                    if st.form_submit_button("💾 Save & Secure Asset", use_container_width=True):
                        if desc and est_value > 0:
                            # Unique ID Generation
                            new_c_id = int(pd.to_numeric(collateral_df["Collateral_ID"], errors='coerce').max() + 1) if not collateral_df.empty else 1
                            
                            new_asset = pd.DataFrame([{
                                "Collateral_ID": new_c_id,
                                "Borrower": sel_borrower,
                                "Loan_ID": sel_id,
                                "Type": asset_type,
                                "Description": desc,
                                "Value": float(est_value),
                                "Status": "Held",
                                "Date_Added": datetime.now().strftime("%Y-%m-%d"),
                                "Photo_Link": ""
                            }])
                            
                            # Standardize for save
                            save_ready_df = pd.concat([collateral_df, new_asset], ignore_index=True)
                            save_ready_df.columns = [c.replace("_", " ") for c in save_ready_df.columns]
                            
                            if save_data("Collateral", save_ready_df):
                                st.success(f"✅ Asset #{new_c_id} registered for {sel_borrower}!")
                                st.rerun()
                        else:
                            st.error("⚠️ Please provide both a description and an estimated value.")

    # --- TAB 2: VIEW & UPDATE ---
    with tab_view:
        if not collateral_df.empty:
            collateral_df["Value"] = pd.to_numeric(collateral_df["Value"], errors='coerce').fillna(0)
            
            # --- BRANDED METRICS ---
            total_val = collateral_df[collateral_df["Status"] != "Released"]["Value"].sum()
            in_custody = collateral_df[collateral_df["Status"].isin(["In Custody", "Held"])].shape[0]
            
            m1, m2 = st.columns(2)
            m1.markdown(f"""<div style="background-color: #F0F8FF; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL ASSET SECURITY</p><h2 style="margin:0; color:#2B3F87;">{total_val:,.0f} <span style="font-size:14px;">UGX</span></h2></div>""", unsafe_allow_html=True)
            m2.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">ACTIVE ASSETS</p><h2 style="margin:0; color:#2B3F87;">{in_custody}</h2></div>""", unsafe_allow_html=True)

            st.write("")

            # --- INVENTORY TABLE ---
            rows_html = ""
            for i, r in collateral_df.reset_index().iterrows():
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                rows_html += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                    <td style="padding:10px; color:#666; font-size:11px;">#{r['Collateral_ID']}</td>
                    <td style="padding:10px;"><b>{r['Borrower']}</b></td>
                    <td style="padding:10px;">{r['Type']}</td>
                    <td style="padding:10px; font-size:11px;">{r['Description']}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{float(r['Value']):,.0f}</td>
                    <td style="padding:10px; text-align:center;"><span style="background:#2B3F87; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r['Status']}</span></td>
                    <td style="padding:10px; text-align:right; font-size:11px; color:#666;">{r['Date_Added']}</td>
                </tr>"""

            st.markdown(f"""<div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;"><thead><tr style="background:#2B3F87; color:white; text-align:left;"><th style="padding:12px;">ID</th><th style="padding:12px;">Borrower</th><th style="padding:12px;">Type</th><th style="padding:12px;">Description</th><th style="padding:12px; text-align:right;">Value</th><th style="padding:12px; text-align:center;">Status</th><th style="padding:12px; text-align:right;">Date</th></tr></thead><tbody>{rows_html}</tbody></table></div>""", unsafe_allow_html=True)

            # --- DELETE & EDIT SECTION ---
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("⚙️ Manage Collateral Records"):
                manage_list = collateral_df.apply(lambda x: f"ID: {x['Collateral_ID']} | {x['Borrower']} - {x['Description']}", axis=1).tolist()
                selected_col = st.selectbox("Select Asset to Modify", manage_list)
                
                c_id_raw = selected_col.split(" | ")[0].replace("ID: ", "")
                c_row = collateral_df[collateral_df["Collateral_ID"].astype(str) == c_id_raw].iloc[0]

                ce1, ce2 = st.columns(2)
                upd_desc = ce1.text_input("Edit Description", value=str(c_row["Description"]))
                upd_val = ce1.number_input("Edit Value (UGX)", value=float(c_row["Value"]))
                
                status_opts = ["In Custody", "Released", "Disposed", "Held"]
                upd_stat = ce2.selectbox("Update Status", status_opts, index=status_opts.index(c_row["Status"]) if c_row["Status"] in status_opts else 0)
                new_link = ce2.text_input("Update Photo URL", value=str(c_row.get("Photo_Link", "")))
                
                btn_upd, btn_del = st.columns(2)
                
                if btn_upd.button("💾 Save Asset Changes", use_container_width=True):
                    collateral_df.loc[collateral_df["Collateral_ID"].astype(str) == c_id_raw, ["Description", "Value", "Status", "Photo_Link"]] = [upd_desc, upd_val, upd_stat, new_link]
                    final_df = collateral_df.copy()
                    final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                    if save_data("Collateral", final_df):
                        st.success("✅ Asset record updated successfully!"); st.rerun()

                if btn_del.button("🗑️ Delete Asset Record", use_container_width=True):
                    final_df = collateral_df[collateral_df["Collateral_ID"].astype(str) != c_id_raw]
                    final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                    if save_data("Collateral", final_df):
                        st.warning("⚠️ Asset record deleted from inventory."); st.rerun()
        else:
            st.info("💡 No collateral registered yet.")
# ==============================
# 16. COLLECTIONS & OVERDUE TRACKER (The Master Engine)
# ==============================
def show_overdue_tracker():
    st.markdown("### 🚨 Loan Overdue & Rollover Tracker")

    # 1. --- THE AUTO-REFILL GATEKEEPER ---
    if st.button("🔄 Refresh Data from Sheets", use_container_width=True):
        with st.spinner("🧹 Clearing cache and re-syncing..."):
            st.cache_data.clear() 
            st.session_state.loans = get_cached_data("Loans")
            st.session_state.ledger = get_cached_data("Ledger")
            st.rerun()

    loans_data = st.session_state.get("loans")
    
    if loans_data is None or loans_data.empty:
        st.info("💡 No active loan records found. The system is currently clear!")
        return

    # 2. --- PREP WORKING DATA ---
    loans = loans_data.copy()
    loans.columns = loans.columns.str.strip().str.replace(" ", "_")
    
    ledger = st.session_state.get("ledger", pd.DataFrame())
    if not ledger.empty:
        ledger.columns = ledger.columns.str.strip().str.replace(" ", "_")

    # 3. --- REQUIRED COLUMNS CHECK ---
    required_cols = ["End_Date", "Status", "Loan_ID", "Borrower", "Principal", "Interest"]
    missing = [col for col in required_cols if col not in loans.columns]
    if missing:
        st.error(f"❌ Missing columns in Google Sheet: {missing}")
        return

    # 4. --- DATE PREP ---
    loans['End_Date'] = pd.to_datetime(loans['End_Date'], errors='coerce')
    today = datetime.now()

    # 5. --- FILTER OVERDUE ACCOUNTS ---
    overdue_df = loans[
        (loans['Status'].isin(["Active", "Overdue", "Rolled/Overdue"])) &
        (loans['End_Date'] < today)
    ].copy()

    if overdue_df.empty:
        st.success("✨ Excellent! All accounts are currently up to date.")
    else:
        st.warning(f"Found {len(overdue_df)} accounts requiring monthly rollover.")

        # 6. --- BRANDED DISPLAY TABLE (Blue Zoe Theme) ---
        rows_html = ""
        for i, r in overdue_df.iterrows():
            p_val = float(r.get('Principal', 0))
            i_val = float(r.get('Interest', 0))
            preview_total = p_val + i_val
            
            rows_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding:10px;"><b>#{r['Loan_ID']}</b></td>
                <td style="padding:10px;">{r['Borrower']}</td>
                <td style="padding:10px; text-align:right;">{p_val:,.0f}</td>
                <td style="padding:10px; text-align:right; color:#D32F2F;">{i_val:,.0f}</td>
                <td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{preview_total:,.0f}</td>
                <td style="padding:10px; text-align:center; color:#666;">{pd.to_datetime(r['End_Date']).strftime('%d %b %y')}</td>
            </tr>"""

        branded_html = f"""
        <div style="border:2px solid #4A90E2; border-radius:10px; overflow:hidden; font-family:sans-serif; font-size:13px; background:white;">
            <table style="width:100%; border-collapse:collapse;">
                <tr style="background:#4A90E2; color:white; text-align:left;">
                    <th style="padding:12px;">ID</th>
                    <th style="padding:12px;">Borrower</th>
                    <th style="padding:12px; text-align:right;">Old Principal</th>
                    <th style="padding:12px; text-align:right;">+ Interest</th>
                    <th style="padding:12px; text-align:right;">New Principal (P+I)</th>
                    <th style="padding:12px; text-align:center;">Missed Date</th>
                </tr>
                {rows_html}
            </table>
        </div>"""
        st.components.v1.html(branded_html, height=350, scrolling=True)

    # 7. --- PREP LEDGER BALANCES ---
    latest_ledger = pd.DataFrame()
    if not ledger.empty and "Loan_ID" in ledger.columns:
        ledger['Date'] = pd.to_datetime(ledger.get('Date'), errors='coerce')
        latest_ledger = ledger.sort_values('Date').groupby("Loan_ID").tail(1)

    # 8. --- ROLLOVER BUTTON (The History-Building Engine) ---
        st.markdown("---") 
        if st.button("🔄 Execute Monthly Rollover (Compound All)", use_container_width=True):
            updated_df = loans.copy() 
            new_rows_list = []
            count = 0
            
            try: 
                # Targets: Find active 'Pending' rows or Fallback to Overdue
                targets = updated_df[updated_df['Status'] == "Pending"].copy() if not updated_df.empty else pd.DataFrame()
                
                if targets.empty:
                    targets = overdue_df.copy()

                if targets.empty:
                    st.info("No loans currently require a rollover cycle.")
                else:
                    for i, r in targets.iterrows():
                        if i in updated_df.index:
                            # 1. ARCHIVE THE OLD ROW
                            updated_df.at[i, 'Status'] = "BCF"

                            # 2. CALCULATE NEW VALUES
                            old_pri = float(r.get('Principal', 0))
                            old_int = float(r.get('Interest', 0))
                            
                            # The New Principal is the total debt from the previous month
                            new_principal_basis = old_pri + old_int
                            
                            # Calculate the NEW month's interest (3%)
                            new_interest = new_principal_basis * 0.03
                            
                            # --- THE FIX: Balance must be Principal + Interest ---
                            new_total_balance = new_principal_basis + new_interest
                            
                            # Date Push
                            orig_end_date = pd.to_datetime(r['End_Date'], errors='coerce')
                            new_start = orig_end_date if pd.notna(orig_end_date) else datetime.now()
                            new_end = new_start + pd.DateOffset(months=1)

                            # 3. CREATE THE NEW ROW
                            new_row = r.copy()
                            new_row['Start_Date'] = new_start.strftime('%Y-%m-%d')
                            new_row['End_Date'] = new_end.strftime('%Y-%m-%d')
                            new_row['Principal'] = new_principal_basis
                            new_row['Interest'] = new_interest
                            new_row['Balance'] = new_total_balance # Now it increases! 🚀
                            new_row['Amount_Paid'] = 0
                            new_row['Status'] = "Pending" 
                            new_row['Balance_B/F'] = new_principal_basis 
                            
                            new_rows_list.append(new_row)
                            count += 1

                    # 4. APPEND AND SORT
                    if new_rows_list:
                        new_entries_df = pd.DataFrame(new_rows_list)
                        combined_df = pd.concat([updated_df, new_entries_df], ignore_index=True)
                        
                        id_col = 'Loan_ID' if 'Loan_ID' in combined_df.columns else 'Loan ID'
                        combined_df = combined_df.sort_values(by=[id_col, 'Start_Date'], ascending=[True, True])
                        updated_df = combined_df

                # 9. --- CLEAN DATA ---
                money_cols = ['Principal', 'Balance', 'Amount_Paid', 'Interest', 'Balance_B/F']
                for m_col in money_cols:
                    if m_col in updated_df.columns:
                        updated_df[m_col] = pd.to_numeric(updated_df[m_col], errors='coerce').fillna(0)

                # 10. --- FINAL SAVE & REFRESH ---
                save_ready_df = updated_df.copy()
                save_ready_df.columns = [col.replace("_", " ") for col in save_ready_df.columns]
                
                if save_data("Loans", save_ready_df):
                    st.success(f"✅ Compounding Successful! Added {count} rows.")
                    st.cache_data.clear() 
                    st.rerun()

            except Exception as e:
                st.error(f"🚨 Rollover Error: {str(e)}")

    # --- THE COLOR FIX: Ensure your display table uses these colors ---
    # Update this in your main table display code (usually where st.dataframe or your HTML table is)
    def style_status(val):
        if val == "BCF": return "background-color: #FFA500; color: white;" # Orange
        if val == "Pending": return "background-color: #D32F2F; color: white;" # Red
        if val == "Closed": return "background-color: #2E7D32; color: white;" # Green
        return ""
            


# ==============================
# 17. ACTIVITY CALENDAR PAGE
# ==============================
def show_calendar():
    st.markdown("## 🗓️ Loan Activity Calendar")
    st.markdown("<h2 style='color: #2B3F87;'>📅 Activity Calendar</h2>", unsafe_allow_html=True)

    loans_df = get_cached_data("Loans")

    if loans_df.empty:
        st.info("📅 Calendar is clear! No active loans to track.")
        return

    loans_df.columns = loans_df.columns.str.strip().str.replace(" ", "_")

    required_keys = ["End_Date", "Total_Repayable", "Status", "Borrower", "Loan_ID", "Principal", "Interest"]
    for col in required_keys:
        if col not in loans_df.columns:
            loans_df[col] = 0 if col in ["Total_Repayable", "Principal", "Interest"] else "Unknown"
    # Convert to proper types for logic
    loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
    loans_df["Total_Repayable"] = pd.to_numeric(loans_df["Total_Repayable"], errors="coerce").fillna(0)
    
    # Reference date (April 2026)
    today = pd.Timestamp.today().normalize()
    
    # Filter for loans that aren't closed
    active_loans = loans_df[loans_df["Status"].astype(str).str.lower() != "closed"].copy()

    # --- VISUAL CALENDAR WIDGET ---
    calendar_events = []
    for _, r in active_loans.iterrows():
        if pd.notna(r['End_Date']):
            # Color logic: Red for overdue, Blue for upcoming
            is_overdue = r['End_Date'].date() < today.date()
            ev_color = "#FF4B4B" if is_overdue else "#4A90E2"
            
            # Auto-Recovery for display amount if Total_Repayable is zero
            disp_amt = float(r['Total_Repayable']) if r['Total_Repayable'] > 0 else (float(r['Principal']) + float(r['Interest']))
            
            calendar_events.append({
                "title": f"UGX {disp_amt:,.0f} - {r['Borrower']}",
                "start": r['End_Date'].strftime("%Y-%m-%d"),
                "end": r['End_Date'].strftime("%Y-%m-%d"),
                "color": ev_color,
                "allDay": True,
            })

    calendar_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
        "initialView": "dayGridMonth",
        "selectable": True,
    }

    # Render the interactive calendar
    calendar(events=calendar_events, options=calendar_options, key="collection_cal")
    
    st.markdown("---")

    # 3. DAILY WORKLOAD METRICS (Zoe Branded Cards)
    # These counts help you see what's happening at a glance
    due_today_df = active_loans[active_loans["End_Date"].dt.date == today.date()]
    upcoming_df = active_loans[
        (active_loans["End_Date"] > today) & 
        (active_loans["End_Date"] <= today + pd.Timedelta(days=7))
    ]
    overdue_count = active_loans[active_loans["End_Date"] < today].shape[0]

    # Create the columns
    m1, m2, m3 = st.columns(3)
    
    # FIX: These must all start at the EXACT same indentation level as the 'm1, m2, m3' line
    m1.markdown(f"""
    <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
        <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">DUE TODAY |</p>
        <p style="margin:0; font-size:18px; color:#2B3F87; font-weight:bold;">{len(due_today_df)} Accounts</p>
    </div>
    """, unsafe_allow_html=True)

    m2.markdown(f"""
    <div style="background-color: #F0F8FF; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
        <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">UPCOMING (7 DAYS) |</p>
        <p style="margin:0; font-size:18px; color:#2B3F87; font-weight:bold;">{len(upcoming_df)} Accounts</p>
    </div>
    """, unsafe_allow_html=True)

    m3.markdown(f"""
    <div style="background-color: #FFF5F5; padding: 20px; border-radius: 15px; border-left: 5px solid #D32F2F; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
        <p style="margin:0; font-size:12px; color:#D32F2F; font-weight:bold;">TOTAL OVERDUE |</p>
        <p style="margin:0; font-size:18px; color:#D32F2F; font-weight:bold;">{overdue_count} Accounts</p>
    </div>
    """, unsafe_allow_html=True)

    # --- CALENDAR FOOTER: REVENUE PREVIEW ---
    st.markdown("---")
    st.markdown("<h4 style='color: #2B3F87;'>📊 Revenue Forecast (This Month)</h4>", unsafe_allow_html=True)
    
    current_month = today.month
    this_month_df = active_loans[active_loans["End_Date"].dt.month == current_month]
    total_expected = this_month_df["Total_Repayable"].sum()
    
    f1, f2 = st.columns(2)
    f1.metric("Expected Collections", f"{total_expected:,.0f} UGX")
    f2.metric("Remaining Appointments", len(this_month_df))
    
    st.write("💡 *Tip: Click any blue/red bar on the calendar above to see the specific borrower details.*")

    # --- SECTION: DUE TODAY ---
    st.markdown("<h4 style='color: #2B3F87;'>📌 Action Items for Today</h4>", unsafe_allow_html=True)
    if due_today_df.empty:
        st.success("✨ No deadlines for today. Focus on follow-ups!")
    else:
        today_rows = ""
        for i, r in due_today_df.iterrows():
            bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
            today_rows += f"""<tr style="background-color: {bg}; border-bottom: 1px solid #ddd;"><td style="padding:10px;"><b>#{r['Loan_ID']}</b></td><td style="padding:10px;">{r['Borrower']}</td><td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{r['Total_Repayable']:,.0f}</td><td style="padding:10px; text-align:center;"><span style="background:#2B3F87; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">💰 COLLECT NOW</span></td></tr>"""
        st.markdown(f"""<div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;"><tr style="background:#2B3F87; color:white;"><th style="padding:10px;">Loan ID</th><th style="padding:10px;">Borrower</th><th style="padding:10px; text-align:right;">Amount Due</th><th style="padding:10px; text-align:center;">Action</th></tr>{today_rows}</table></div>""", unsafe_allow_html=True)

    # --- SECTION: UPCOMING ---
    st.markdown("<br><h4 style='color: #2B3F87;'>⏳ Upcoming Deadlines (Next 7 Days)</h4>", unsafe_allow_html=True)
    if upcoming_df.empty:
        st.info("The next few days look quiet.")
    else:
        upcoming_display = upcoming_df.sort_values("End_Date").copy()
        up_rows = ""
        for i, r in upcoming_display.iterrows():
            bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
            display_amt = float(r.get('Total_Repayable', 0)) or (float(r.get('Principal', 0)) + float(r.get('Interest', 0)))
            up_rows += f"""<tr style="background-color: {bg};"><td style="padding:10px; color:#2B3F87; font-weight:bold;">{r['End_Date'].strftime('%d %b (%a)')}</td><td style="padding:10px;">{r.get('Borrower', 'Unknown')}</td><td style="padding:10px; text-align:right; font-weight:bold;">{display_amt:,.0f} UGX</td><td style="padding:10px; text-align:right; color:#666;">ID: #{r.get('Loan_ID', 'N/A')}</td></tr>"""
        st.markdown(f"""<div style="border:1px solid #2B3F87; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;"><tr style="background:#2B3F87; color:white;"><th style="padding:10px;">Due Date</th><th style="padding:10px;">Borrower</th><th style="padding:10px; text-align:right;">Amount</th><th style="padding:10px; text-align:right;">Ref</th></tr>{up_rows}</table></div>""", unsafe_allow_html=True)

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
            bg = "#FFF5F5"
            late_color = "#FF4B4B" if r['Days_Late'] > 7 else "#FFA500"
            od_rows += f"""<tr style="background-color: {bg}; border-bottom: 1px solid #FFDADA;"><td style="padding:10px;"><b>#{r['Loan_ID']}</b></td><td style="padding:10px;">{r['Borrower']}</td><td style="padding:10px; text-align:center; font-weight:bold; color:{late_color};">{r['Days_Late']} Days</td><td style="padding:10px; text-align:center;"><span style="background:{late_color}; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r['Status']}</span></td></tr>"""
        st.markdown(f"""<div style="border:2px solid #FF4B4B; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;"><tr style="background:#FF4B4B; color:white;"><th style="padding:10px;">Loan ID</th><th style="padding:10px;">Borrower</th><th style="padding:10px; text-align:center;">Late By</th><th style="padding:10px; text-align:center;">Status</th></tr>{od_rows}</table></div>""", unsafe_allow_html=True)
# ==============================
# 18. EXPENSE MANAGEMENT PAGE
# ==============================

def show_expenses():
    """
    Tracks business operational costs. Includes category-based logging,
    spending distribution analytics, and detailed log auditing.
    """
    st.markdown("<h2 style='color: #2B3F87;'>📁 Expense Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA
    df = get_cached_data("Expenses")

    # The Master Category List for Zoe Consults
    EXPENSE_CATS = ["Rent", "Insurance Account", "Utilities", "Salaries", "Marketing", "Office Expenses"]

    if df.empty:
        df = pd.DataFrame(columns=["Expense_ID", "Category", "Amount", "Date", "Description", "Payment_Date", "Receipt_No"])
    else:
        # Standardize headers for consistent logic
        df.columns = df.columns.str.strip().str.replace(" ", "_")

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
            
            category = col1.selectbox("Category", EXPENSE_CATS)
            amount = col2.number_input("Amount (UGX)", min_value=0, step=1000)
            
            desc = st.text_input("Description (e.g., Office Power Bill March)")
            
            c_date, c_receipt = st.columns(2)
            p_date = c_date.date_input("Actual Payment Date", value=datetime.now())
            receipt_no = c_receipt.text_input("Receipt / Invoice #", placeholder="e.g. RCP-101")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("🚀 Save Expense Record", use_container_width=True):
                if amount > 0 and desc:
                    # ID Math
                    new_id = int(pd.to_numeric(df["Expense_ID"], errors='coerce').max() + 1) if not df.empty else 1
                    
                    new_entry = pd.DataFrame([{
                        "Expense_ID": new_id,
                        "Category": category,
                        "Amount": float(amount),
                        "Date": datetime.now().strftime("%Y-%m-%d"), 
                        "Description": desc,
                        "Payment_Date": p_date.strftime("%Y-%m-%d"), 
                        "Receipt_No": receipt_no                    
                    }])
                    
                    # Save with space-restored headers
                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    save_ready = updated_df.copy()
                    save_ready.columns = [c.replace("_", " ") for c in save_ready.columns]
                    
                    if save_data("Expenses", save_ready):
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
            
            # Pie Chart Analysis
            cat_summary = df.groupby("Category")["Amount"].sum().reset_index()
            fig_exp = px.pie(cat_summary, names="Category", values="Amount", 
                             title="Spending Distribution",
                             hole=0.4, color_discrete_sequence=["#2B3F87", "#F0F8FF", "#FF4B4B", "#ADB5BD"])
            fig_exp.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="#2B3F87")
            st.plotly_chart(fig_exp, use_container_width=True)
            
            st.markdown("<h4 style='color: #2B3F87;'>📜 Detailed Expense Log</h4>", unsafe_allow_html=True)
            
            # Identify correct date column
            date_col = "Date" if "Date" in df.columns else df.columns[0] 
            sorted_df = df.sort_values(date_col, ascending=False)
            
            rows_html = ""
            for i, r in sorted_df.reset_index().iterrows():
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                
                rows_html += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                    <td style="padding:10px; color:#666; font-size:11px;">{r.get(date_col, "-")}</td>
                    <td style="padding:10px;"><b>{r.get('Category', 'Other')}</b></td>
                    <td style="padding:10px; font-size:11px;">{r.get('Description', '-')}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:#FF4B4B;">{float(r.get('Amount', 0)):,.0f}</td>
                    <td style="padding:10px; text-align:center; color:#666; font-size:10px;">{r.get('Receipt_No', '-')}</td>
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

    # --- TAB 3: MANAGE / EDIT LOANS ---
    with tab_manage:
        st.markdown("### 🛠️ Modify Loan Agreement")
        
        # 1. REFRESH & CLEAN DATA
        m_df = st.session_state.get("loans", pd.DataFrame()).copy()
        
        if m_df.empty:
            st.info("ℹ️ No loans found in the system.")
        else:
            m_df.columns = m_df.columns.str.strip().str.replace(" ", "_")
            m_df['Loan_ID'] = m_df['Loan_ID'].astype(str).str.replace(".0", "", regex=False).str.strip()
            
            m_options = [f"ID: {r['Loan_ID']} | {r['Borrower']}" for _, r in m_df.iterrows()]
            selected_m = st.selectbox("🔍 Select Loan to Manage/Edit", m_options, key="manage_final_v3")

            # Extract the ID safely
            m_id_to_find = selected_m.split("|")[0].replace("ID:", "").strip()
            target_loan = m_df[m_df["Loan_ID"] == m_id_to_find]

            if not target_loan.empty:
                loan_to_edit = target_loan.iloc[0]
                st.markdown(f"**Editing Record for:** {loan_to_edit['Borrower']} (Loan #{m_id_to_find})")
                
                with st.form("edit_loan_form_v3"):
                    c1, c2 = st.columns(2)
                    with c1:
                        up_name = st.text_input("Borrower Name", value=str(loan_to_edit.get('Borrower', '')))
                        up_p = st.number_input("Principal Amount (UGX)", value=float(loan_to_edit.get('Principal', 0)), step=1000.0)
                        up_rate = st.number_input("Interest Rate (%)", value=float(loan_to_edit.get('Interest_Rate', 0)), step=0.1)
                    
                    with c2:
                        status_opts = ["Active", "Overdue", "Rolled/Overdue", "Cleared", "Defaulted"]
                        curr_s = str(loan_to_edit.get('Status', 'Active'))
                        up_status = st.selectbox("Status", status_opts, index=status_opts.index(curr_s) if curr_s in status_opts else 0)
                        up_date = st.date_input("New Due Date", value=pd.to_datetime(loan_to_edit.get('End_Date', datetime.now())))

                    if st.form_submit_button("💾 Save Changes to Google Sheets", use_container_width=True):
                        full_df = st.session_state.loans.copy()
                        full_df.columns = full_df.columns.str.strip().str.replace(" ", "_")
                        full_df['Loan_ID'] = full_df['Loan_ID'].astype(str).str.replace(".0", "", regex=False).str.strip()
                        
                        idx_list = full_df[full_df["Loan_ID"] == m_id_to_find].index
                        if not idx_list.empty:
                            row_idx = idx_list[0]
                            full_df.at[row_idx, 'Borrower'] = up_name
                            full_df.at[row_idx, 'Principal'] = up_p
                            full_df.at[row_idx, 'Interest_Rate'] = up_rate
                            full_df.at[row_idx, 'Status'] = up_status
                            full_df.at[row_idx, 'End_Date'] = up_date.strftime('%Y-%m-%d')
                            
                            # Restore original headers
                            full_df.columns = [c.replace("_", " ") for c in full_df.columns]
                            
                            if save_data("Loans", full_df):
                                st.success(f"✅ Loan #{m_id_to_find} updated!")
                                st.session_state.loans = full_df
                                st.rerun()
                            else:
                                st.error("❌ Failed to save to Google Sheets.")
            else:
                st.error(f"⚠️ Search failed. Looking for ID '{m_id_to_find}' but it wasn't found.")
# ==============================
# 19. PETTY CASH MANAGEMENT PAGE
# ==============================

def show_petty_cash():
    """
    Manages daily office cash transactions. Tracks inflows, outflows,
    and provides real-time balance calculations with visual alerts.
    """
    st.markdown("<h2 style='color: #2B3F87;'>💵 Petty Cash Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA
    df = get_cached_data("PettyCash")

    if df.empty:
        df = pd.DataFrame(columns=["Transaction_ID", "Type", "Amount", "Date", "Description"])
    else:
        # Standardize headers and data types
        df.columns = df.columns.str.strip().str.replace(" ", "_")
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

    # Balance Card (Dynamic Color based on cash health)
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
                        "Amount": float(t_amount),
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Description": desc
                    }])
                    
                    # Merge and Restore spaces for Google Sheets
                    final_df = pd.concat([df, new_row], ignore_index=True)
                    final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                    
                    if save_data("PettyCash", final_df):
                        st.success(f"Successfully recorded {t_amount:,.0f} UGX!")
                        st.rerun()
                else:
                    st.error("Please provide amount and description.")

    # --- TAB 2: HISTORY ---
    with tab_history:
        if not df.empty:
            def color_type(val):
                return 'color: #10B981;' if val == 'In' else 'color: #FF4B4B;'
            
            # Formatted table display with color-coded In/Out labels
            st.dataframe(
                df.sort_values("Date", ascending=False)
                .style.map(color_type, subset=['Type']) # Updated to .map for Pandas compatibility
                .format({"Amount": "{:,.0f}"}),
                use_container_width=True, hide_index=True
            )

            # ADMIN ACTIONS: EDIT/DELETE
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("⚙️ Advanced: Edit or Delete Transaction"):
                options = [f"ID: {int(row['Transaction_ID'])} | {row['Type']} - {row['Description']}" for _, row in df.iterrows()]
                selected_task = st.selectbox("Select Entry to Modify", options)
                
                sel_id = int(selected_task.split(" | ")[0].replace("ID: ", ""))
                item = df[df["Transaction_ID"] == sel_id].iloc[0]

                up_type = st.selectbox("Update Type", ["In", "Out"], index=0 if item["Type"] == "In" else 1)
                up_amt = st.number_input("Update Amount", value=float(item["Amount"]), step=1000.0)
                up_desc = st.text_input("Update Description", value=str(item["Description"]))

                c_up, c_del = st.columns(2)
                if c_up.button("💾 Save Changes", use_container_width=True):
                    df.loc[df["Transaction_ID"] == sel_id, ["Type", "Amount", "Description"]] = [up_type, up_amt, up_desc]
                    save_ready = df.copy()
                    save_ready.columns = [c.replace("_", " ") for c in save_ready.columns]
                    if save_data("PettyCash", save_ready):
                        st.success("Updated Successfully!")
                        st.rerun()

                if c_del.button("🗑️ Delete Permanently", use_container_width=True):
                    df_new = df[df["Transaction_ID"] != sel_id]
                    save_ready = df_new.copy()
                    save_ready.columns = [c.replace("_", " ") for c in save_ready.columns]
                    if save_data("PettyCash", save_ready):
                        st.warning("Entry Deleted.")
                        st.rerun()
        else:
            st.info("No transaction history available.")
# ==============================
# 20. PAYROLL MANAGEMENT PAGE
# ==============================

def show_payroll():
    """
    Handles employee compensation, tax compliance (PAYE/LST), 
    and NSSF contributions. Includes a professional printable report.
    """
    if st.session_state.get("role") != "Admin":
        st.error("🔒 Restricted Access: Only Administrators can process payroll.")
        return

    st.markdown("<h2 style='color: #4A90E2;'>🧾 Payroll Management</h2>", unsafe_allow_html=True)

    # 1. SYNC COLUMNS TO MATCH REQUIREMENTS
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
        # Standardize headers and fill missing data
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        for col in required_columns:
            if col not in df.columns: df[col] = 0
        df = df.fillna(0)

    # 2. THE EXACT MATH ENGINE
    def run_manual_sync_calculations(basic, arrears, absent_deduct, advance, other):
        # Gross Calculation
        gross = (float(basic) + float(arrears)) - float(absent_deduct)
        
        # Local Service Tax (LST) Logic
        lst = 100000 / 12 if gross > 1000000 else 0
        
        # NSSF Logic (5% Employee, 10% Employer)
        n5 = gross * 0.05
        n10 = gross * 0.10
        n15 = n5 + n10
        
        # PAYE Tiered Logic
        taxable = gross - n5
        paye = 0
        if taxable > 410000: 
            paye = 25000 + (0.30 * (taxable - 410000))
        elif taxable > 282000: 
            paye = (taxable - 282000) * 0.20 + 4700
        elif taxable > 235000: 
            paye = (taxable - 235000) * 0.10
            
        total_deductions = paye + lst + n5 + float(advance) + float(other)
        net = gross - total_deductions
        
        return {
            "gross": round(gross), "lst": round(lst), "n5": round(n5), 
            "n10": round(n10), "n15": round(n15), "paye": round(paye), "net": round(net)
        }

    tab_process, tab_logs = st.tabs(["➕ Process Salary", "📜 Payroll History"])

    # --- TAB 1: PROCESS SALARY ---
    with tab_process:
        with st.form("new_payroll_form", clear_on_submit=True):
            st.markdown("<h4 style='color: #2B3F87;'>👤 Employee Details</h4>", unsafe_allow_html=True)
            name = st.text_input("Employee Name")
            c1, c2, c3 = st.columns(3)
            f_tin = c1.text_input("TIN")
            f_desig = c2.text_input("Designation")
            f_mob = c3.text_input("Mob No.")
            
            c4, c5 = st.columns(2)
            f_acc = c4.text_input("Account No.")
            f_nssf_no = c5.text_input("NSSF No.")
            
            st.write("---")
            st.markdown("<h4 style='color: #2B3F87;'>💰 Earnings & Deductions</h4>", unsafe_allow_html=True)
            c6, c7, c8 = st.columns(3)
            f_arrears = c6.number_input("ARREARS", min_value=0.0)
            f_basic = c7.number_input("SALARY (Basic)", min_value=0.0)
            f_absent = c8.number_input("Absenteeism Deduction", min_value=0.0)
            
            c9, c10 = st.columns(2)
            f_adv = c9.number_input("S.DRS / ADVANCE", min_value=0.0)
            f_other = c10.number_input("Other Deductions", min_value=0.0)

            if st.form_submit_button("💳 Confirm & Release Payment", use_container_width=True):
                if name and f_basic > 0:
                    calc = run_manual_sync_calculations(f_basic, f_arrears, f_absent, f_adv, f_other)
                    
                    new_row = pd.DataFrame([{
                        "Payroll_ID": int(df["Payroll_ID"].max() + 1) if not df.empty else 1,
                        "Employee": name, "TIN": f_tin, "Designation": f_desig, "Mob_No": f_mob,
                        "Account_No": f_acc, "NSSF_No": f_nssf_no, "Arrears": f_arrears,
                        "Basic_Salary": f_basic, "Absent_Deduction": f_absent,
                        "Gross_Salary": calc['gross'], "LST": calc['lst'], "PAYE": calc['paye'],
                        "NSSF_5": calc['n5'], "NSSF_10": calc['n10'], "NSSF_15": calc['n15'],
                        "Advance_DRS": f_adv, "Other_Deductions": f_other, "Net_Pay": calc['net'],
                        "Date": datetime.now().strftime("%Y-%m-%d")
                    }])
                    
                    # Restore spaces for Google Sheets
                    final_save_df = pd.concat([df, new_row], ignore_index=True)
                    final_save_df.columns = [c.replace("_", " ") for c in final_save_df.columns]
                    
                    if save_data("Payroll", final_save_df):
                        st.success(f"✅ Payroll for {name} saved successfully!")
                        st.rerun()

    # --- TAB 2: HISTORY & PRINTING ---
    with tab_logs:
        if not df.empty:
            p_col1, p_col2 = st.columns([4, 1])
            p_col1.markdown(f"<h3 style='color: #4A90E2;'>{datetime.now().strftime('%B %Y')} Summary</h3>", unsafe_allow_html=True)
            
            def fm(x): 
                try: return f"{int(float(x)):,}" 
                except: return "0"

            rows_html = ""
            for i, r in df.iterrows():
                n5 = float(r.get('NSSF_5', 0))
                n10 = float(r.get('NSSF_10', 0))
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

            printable_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: sans-serif; padding: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
                    th {{ background: #2B3F87; color: white; padding: 10px; border: 1px solid #ddd; }}
                    @media print {{ @page {{ size: landscape; margin: 1cm; }} }}
                </style>
            </head>
            <body>
                <div style="text-align:center; border-bottom:3px solid #2B3F87; margin-bottom:20px;">
                    <h1 style="color:#2B3F87;">ZOE CONSULTS SMC LTD</h1>
                    <p><b>PAYROLL REPORT - {datetime.now().strftime('%B %Y')}</b></p>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>S/N</th><th>Employee</th><th>Arrears</th><th>Basic</th><th>Gross</th>
                            <th>P.A.Y.E</th><th>NSSF(5%)</th><th>Net Pay</th><th>NSSF(10%)</th><th>NSSF(15%)</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
                <div style="margin-top:50px; display:flex; justify-content:space-around;">
                    <p>___________________<br>Prepared By</p>
                    <p>___________________<br>Approved By</p>
                </div>
            </body>
            </html>
            """

            if p_col2.button("📥 Print PDF", key="print_payroll_trigger"):
                # Injects the print script only when requested
                st.components.v1.html(printable_html + "<script>window.print();</script>", height=0)

            st.components.v1.html(printable_html, height=600, scrolling=True)

            csv_text = df.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Download CSV Backup", data=csv_text, file_name="Payroll_Zoe.csv", mime="text/csv")
            
            st.write("---")
            with st.expander("⚙️ Modify / Delete Record"):
                pay_opts = [f"{r['Employee']} (ID: {r['Payroll_ID']})" for _, r in df.iterrows()]
                if pay_opts:
                    sel_opt = st.selectbox("Select Record to Manage", pay_opts, key="payroll_edit_selectbox")
                    try:
                        sid = str(sel_opt.split("(ID: ")[1].replace(")", ""))
                        item = df[df['Payroll_ID'].astype(str) == sid].iloc[0]
                        st.text_input("Edit Name (Preview)", value=str(item['Employee']), disabled=True)
                        st.info("Direct modification of payroll math is locked. Delete and re-process for errors.")
                        if st.button("🗑️ Delete This Record", use_container_width=True):
                            df_new = df[df['Payroll_ID'].astype(str) != sid]
                            df_new.columns = [c.replace("_", " ") for c in df_new.columns]
                            if save_data("Payroll", df_new):
                                st.warning("Payroll record deleted.")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Selection error: {e}")
        else:
            st.info("No payroll records found for this period.")
        
    
 

# ==============================
# 21. ADVANCED ANALYTICS & REPORTS
# ==============================

def show_reports():
    """
    Consolidates data across all modules to provide high-level 
    financial health metrics, cash flow trends, and risk assessment.
    """
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
    if not isinstance(payroll, pd.DataFrame):
        payroll = pd.DataFrame()

    # Initializing tax/deduction totals to 0 to prevent local variable errors
    nssf_total, paye_total = 0, 0
    
    if not payroll.empty:
        # Standardize payroll headers for logic
        payroll.columns = payroll.columns.str.strip().str.replace(" ", "_")
        # Use a super-safe way to pull column totals
        n5 = pd.to_numeric(payroll.get("NSSF_5", 0), errors="coerce").fillna(0).sum()
        n10 = pd.to_numeric(payroll.get("NSSF_10", 0), errors="coerce").fillna(0).sum()
        nssf_total = n5 + n10
        paye_total = pd.to_numeric(payroll.get("PAYE", 0), errors="coerce").fillna(0).sum()

    # 3. OTHER DATA SUMS
    # Standardize column headers for math logic
    loans.columns = loans.columns.str.strip().str.replace(" ", "_")
    
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
    if not petty.empty:
        petty.columns = petty.columns.str.strip().str.replace(" ", "_")
        if "Type" in petty.columns:
            petty_out = pd.to_numeric(petty[petty["Type"]=="Out"].get("Amount", 0), errors="coerce").fillna(0).sum()
    
    # 💰 FINANCIAL LOGIC:
    # Total Outflow = Direct Expenses + Petty Cash Out + Taxes (PAYE/NSSF)
    total_outflow = exp_amt + petty_out + nssf_total + paye_total
    
    # Net Profit = Inflows (Payments) - Outflows (Expenses)
    net_profit = p_amt - total_outflow

    # 4. KPI DASHBOARD (Soft Blue Branded)
    st.subheader("🚀 Financial Performance")
    k1, k2, k3, k4 = st.columns(4)
    
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
            pay_copy.columns = pay_copy.columns.str.strip().str.replace(" ", "_")
            pay_copy["Date"] = pd.to_datetime(pay_copy.get("Date"), errors='coerce')
            inc_trend = pay_copy.groupby(pay_copy["Date"].dt.strftime('%Y-%m'))["Amount"].sum().reset_index()
            
            exp_copy = expenses.copy() if not expenses.empty else pd.DataFrame(columns=["Amount", "Date"])
            if not exp_copy.empty:
                exp_copy.columns = exp_copy.columns.str.strip().str.replace(" ", "_")
                exp_copy["Date"] = pd.to_datetime(exp_copy.get("Date"), errors='coerce')
                exp_trend = exp_copy.groupby(exp_copy["Date"].dt.strftime('%Y-%m'))["Amount"].sum().reset_index()
            else:
                exp_trend = pd.DataFrame(columns=["Date", "Amount"])

            # Merge trends for comparison bar chart
            merged = pd.merge(inc_trend, exp_trend, on="Date", how="outer").fillna(0)
            merged.columns = ["Month", "Income", "Expenses"]
            
            fig_bar = px.bar(merged, x="Month", y=["Income", "Expenses"], barmode="group",
                             color_discrete_map={"Income": "#00ffcc", "Expenses": "#FF4B4B"})
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No payment data to chart.")

    with col_right:
        st.write("**🛡️ Portfolio Weight (Top 5)**")
        if not loans.empty:
            # Safe Principal/Amount lookup based on normalized column names
            val_col = "Principal" if "Principal" in loans.columns else "Amount"
            top_borrowers = loans.groupby("Borrower")[val_col].sum().sort_values(ascending=False).head(5).reset_index()
            top_borrowers.columns = ["Borrower", "Total_Loaned"]
            
            fig_pie = px.pie(top_borrowers, names="Borrower", values="Total_Loaned", hole=0.5,
                             color_discrete_sequence=px.colors.sequential.GnBu_r)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No loan data for portfolio analysis.")

    # 6. RISK INDICATOR
    st.markdown("---")
    st.subheader("🚨 Risk Assessment")
    
    val_col = "Principal" if "Principal" in loans.columns else "Amount"
    overdue_mask = loans["Status"].isin(["Overdue", "Rolled/Overdue"])
    overdue_val = pd.to_numeric(loans.loc[overdue_mask, val_col], errors="coerce").fillna(0).sum()
    
    risk_percent = (overdue_val / l_amt * 100) if l_amt > 0 else 0
    
    r1, r2 = st.columns([2, 1])
    
    with r1:
        st.write(f"Your Portfolio at Risk (PAR) is **{risk_percent:.1f}%**.")
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
    """
    Detailed transaction audit for individual loans.
    Generates a consolidated HTML statement with automated running balances
    and compounding interest trails.
    """
    st.markdown("<h2 style='color: #2B3F87;'>📘 Master Ledger</h2>", unsafe_allow_html=True)
    
    # 1. LOAD DATA & NORMALIZE
    loans_df = get_cached_data("Loans")
    payments_df = get_cached_data("Payments")

    if loans_df is None or loans_df.empty:
        st.info("💡 Your system is clear! No active loans found to generate a statement.")
        return

    # Normalize headers
    loans_df.columns = loans_df.columns.str.strip().str.replace(" ", "_")
    if not payments_df.empty:
        payments_df.columns = payments_df.columns.str.strip().str.replace(" ", "_")

    # --- THE CRITICAL FIX: VALIDITY CHECK ---
    # We only care about payments for loans that ACTUALLY exist in loans_df
    active_ids = set(loans_df['Loan_ID'].astype(str).str.replace(".0", "", regex=False).tolist())
    
    if not payments_df.empty:
        # Clean the Payment IDs to match the Loan IDs
        payments_df['Loan_ID_Clean'] = payments_df['Loan_ID'].astype(str).str.replace(".0", "", regex=False)
        
        # WE ONLY KEEP PAYMENTS BELONGING TO ACTIVE LOANS
        payments_df = payments_df[payments_df['Loan_ID_Clean'].isin(active_ids)].copy()

    # 2. SELECTION LOGIC
    # Ensure ID is string for matching logic
    loans_df['Loan_ID'] = loans_df['Loan_ID'].fillna("0").astype(str).str.replace(".0", "", regex=False)
    loan_options = [f"ID: {r.get('Loan_ID', '0')} - {r.get('Borrower', 'Unknown')}" for _, r in loans_df.iterrows()]
    
    selected_loan = st.selectbox("Select Loan to View Full Statement", loan_options, key="ledger_main_select")
    
    # Extract ID safely
    try:
        raw_id = selected_loan.split(" - ")[0].replace("ID: ", "")
        l_id_str = str(raw_id).strip()
    except Exception:
        st.error("❌ Invalid Loan ID selected.")
        return
    
    # Fetch specific loan record
    loan_info = loans_df[loans_df["Loan_ID"] == l_id_str].iloc[0]
    
    # 3. TREND MATH & BALANCE CALCULATION
    current_p = float(loan_info.get("Principal", 0))
    interest_amt = float(loan_info.get("Interest", 0))
    rate = float(loan_info.get("Interest_Rate", 0))
    
    # Reverse logic to find Opening Balance
    if interest_amt == 0 and rate > 0:
        old_p = current_p / (1 + (rate/100))
        interest_amt = current_p - old_p
    else:
        old_p = current_p - interest_amt

    # --- TOP CARD DISPLAY ---
    t_repay = current_p + (interest_amt if interest_amt > 0 else 0)
    a_paid = float(loan_info.get("Amount_Paid", 0))
    display_bal = float(loan_info.get("Balance", t_repay - a_paid))

    st.markdown(f"""
        <div style="background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px;">
            <p style="margin:0; font-size:14px; color:#666; font-weight:bold;">CURRENT OUTSTANDING BALANCE (INC. INTEREST)</p>
            <h1 style="margin:0; color:#2B3F87;">{display_bal:,.0f} <span style="font-size:18px;">UGX</span></h1>
        </div>
    """, unsafe_allow_html=True)

    # 4. BUILD THE LEDGER TABLE DATA
    ledger_data = []
    status_str = str(loan_info.get('Status', ''))
    is_rolled = "Rolled" in status_str or "Overdue" in status_str

    if is_rolled:
        ledger_data.append({"Date": "Prev Month", "Description": "Opening Balance (Brought Forward)", "Debit": old_p, "Credit": 0, "Balance": old_p})
        ledger_data.append({"Date": loan_info.get('Rollover_Date', 'Rollover'), "Description": f"➕ Monthly Interest ({rate}% Compounded)", "Debit": interest_amt, "Credit": 0, "Balance": current_p})
    else:
        ledger_data.append({"Date": loan_info.get("Start_Date", "-"), "Description": "Initial Loan Disbursement", "Debit": current_p, "Credit": 0, "Balance": current_p})

    # Integrate Payments into the running balance
    if not payments_df.empty:
        rel_pay = payments_df[payments_df["Loan_ID"].astype(str).str.replace(".0", "", regex=False) == l_id_str].sort_values("Date")
        curr_run_bal = current_p
        for _, pay in rel_pay.iterrows():
            p_amt = float(pay.get("Amount", 0))
            curr_run_bal -= p_amt
            ledger_data.append({
                "Date": pay.get("Date", "-"),
                "Description": f"✅ Repayment ({pay.get('Method', 'Cash')})",
                "Debit": 0, "Credit": p_amt, "Balance": curr_run_bal
            })

    # Render interactive audit table
    st.dataframe(pd.DataFrame(ledger_data).style.format({"Debit": "{:,.0f}", "Credit": "{:,.0f}", "Balance": "{:,.0f}"}), use_container_width=True, hide_index=True)
    # 5. PRINTABLE STATEMENT SECTION
    st.markdown("---")
    if st.button("✨ Preview Consolidated Statement", use_container_width=True):
        st.info("Generating professional statement...")
        borrowers_df = get_cached_data("Borrowers")
        current_b_name = loan_info['Borrower'] 
        
        # Get all loans for this specific client
        client_loans = loans_df[loans_df["Borrower"] == current_b_name]
        b_data = borrowers_df[borrowers_df["Name"] == current_b_name] if not borrowers_df.empty else pd.DataFrame()
        b_details = b_data.iloc[0] if not b_data.empty else {}

        # Branded HTML Header
        navy_blue = "#000080"
        baby_blue = "#E1F5FE"
        
        html_statement = f"""
        <div id="printable-area" style="font-family: 'Arial', sans-serif; padding: 25px; border: 1px solid #eee; max-width: 850px; margin: auto; background-color: white; color: #333;">
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

        grand_total_balance = 0.0 
        
        # ... (Inside the loop for client_loans) ...
        for _, l_row in client_loans.iterrows():
            this_loan_id = str(l_row['Loan_ID'])
            l_ledger = []
            
            c_p = float(l_row.get('Principal', 0))
            i_a = float(l_row.get('Interest', 0))
            
            # 1. ADD THE PRINCIPAL DEBIT
            l_ledger.append({
                "Date": l_row.get('Start_Date', 'N/A'), 
                "Description": "Loan Disbursement (Principal)", 
                "Debit": c_p, 
                "Credit": 0
            })

            # 2. ADD THE INTEREST DEBIT (THE FIX!)
            # This ensures the total "Debt" matches the total "Payment"
            if i_a > 0:
                l_ledger.append({
                    "Date": l_row.get('Start_Date', 'N/A'), 
                    "Description": "Interest Charged", 
                    "Debit": i_a, 
                    "Credit": 0
                })

            # --- FETCH PAYMENTS FOR THIS SPECIFIC LOAN ID ---
            # We force everything to strings to make sure "7" matches "7"
            p_loan_id_col = "Loan_ID" if "Loan_ID" in payments_df.columns else "Loan ID"
            
            # This is the "Magic Filter" that finds the missing payment
            l_payments = payments_df[
                payments_df[p_loan_id_col].astype(str).str.replace(".0", "", regex=False).str.strip() == str(this_loan_id).strip()
            ] if not payments_df.empty else pd.DataFrame()

            for _, p_row in l_payments.iterrows():
                l_ledger.append({
                    "Date": p_row.get('Date', '-'), 
                    "Description": f"Payment (Ref: {p_row.get('Payment_ID', 'N/A')})", 
                    "Debit": 0, 
                    "Credit": float(p_row.get('Amount', 0))
                })
            
            # 4. CALCULATE RUNNING BALANCE
            temp_df = pd.DataFrame(l_ledger)
            loan_bal = 0.0
            if not temp_df.empty:
                # Math: (All Debits) - (All Credits)
                temp_df['Balance'] = temp_df['Debit'].cumsum() - temp_df['Credit'].cumsum()
                # We round to 0 to avoid tiny decimal leftovers (like 0.0000001)
                loan_bal = round(float(temp_df.iloc[-1]['Balance']))
            
            grand_total_balance += loan_bal
            
            # ... (Rest of the HTML generation remains the same) ...

            # Add Individual Loan Table to HTML
            html_statement += f"""
            <div style="margin-top: 20px; padding: 10px; background-color: {baby_blue}; border-radius: 5px;">
                <span style="font-weight: bold; color: {navy_blue};">LOAN ID: {this_loan_id}</span> | 
                <span>Status: {l_row.get('Status', 'Active')}</span> | 
                <span style="float: right;">Balance: <strong>{loan_bal:,.0f} UGX</strong></span>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 20px;">
                <tr style="border-bottom: 1px solid {navy_blue}; color: {navy_blue}; font-weight: bold;">
                    <th style="padding: 8px; text-align: left;">Date</th>
                    <th style="padding: 8px; text-align: left;">Description</th>
                    <th style="padding: 8px; text-align: right;">Debit</th>
                    <th style="padding: 8px; text-align: right;">Credit</th>
                    <th style="padding: 8px; text-align: right;">Balance</th>
                </tr>"""
            
            for _, row in temp_df.iterrows():
                html_statement += f"""
                <tr>
                    <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['Date']}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['Description']}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['Debit']:,.0f}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['Credit']:,.0f}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{row['Balance']:,.0f}</td>
                </tr>"""
            html_statement += "</table>"

        # Footer & Grand Total
        html_statement += f"""
            <div style="margin-top: 30px; padding: 20px; border: 2px solid {navy_blue}; border-radius: 8px; text-align: right; background-color: #f0f4ff;">
                <h2 style="margin: 0; color: {navy_blue};">GRAND TOTAL OUTSTANDING</h2>
                <h1 style="margin: 5px 0 0 0; color: #FF4B4B;">{grand_total_balance:,.0f} UGX</h1>
            </div>
        </div>"""
        
        st.components.v1.html(html_statement, height=800, scrolling=True)

        # Print Trigger
        print_btn = f"""
            <script>
                function printStmt() {{
                    var divContents = document.getElementById("printable-area").innerHTML;
                    var a = window.open('', '', 'height=800, width=1000');
                    a.document.write('<html><body >');
                    a.document.write(divContents);
                    a.document.write('</body></html>');
                    a.document.close();
                    a.print();
                }}
            </script>
            <button onclick="printStmt()" style="background-color: {navy_blue}; color: white; border: none; padding: 15px; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer;">
                📥 Download / Print Consolidated Statement
            </button>
        """
        st.components.v1.html(print_btn, height=100)
    


# ==============================
# 23. SYSTEM SETTINGS (Admin Only)
# ==============================

def show_settings():
    """
    Administrative control panel for business branding, system defaults,
    and cache maintenance. Restricted to 'Admin' role users.
    """
    # 1. Access Control Safety Check
    if st.session_state.get("role") != "Admin":
        st.error("🔒 Access Denied: System Settings are restricted to Administrators.")
        return

    st.markdown("<h2 style='color: #2B3F87;'>⚙️ System Settings</h2>", unsafe_allow_html=True)

    # --- BRANDING SECTION ---
    st.subheader("🖼️ Business Branding")
    
    # Retrieve current logo via the Section 2 cached loader
    current_logo = get_logo()
    
    col_logo, col_upload = st.columns([1, 2])
    
    with col_logo:
        if current_logo:
            st.image(f"data:image/png;base64,{current_logo}", width=120)
            st.caption("Active System Logo")
        else:
            st.info("No logo currently set.")

    with col_upload:
        uploaded_logo = st.file_uploader("Upload New Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if st.button("🚀 Apply New Branding", use_container_width=True):
            if uploaded_logo:
                # Optimized save logic from Section 6
                if save_logo_to_sheet(uploaded_logo):
                    st.success("Logo updated and cache cleared! ✅")
                    st.rerun()
            else:
                st.warning("Please select a file first.")

    st.markdown("---")

    # --- GENERAL CONFIGURATION ---
    settings_df = get_cached_data("Settings")
    
    def get_setting_value(key, default):
        """Helper to safely extract key-value pairs from the Settings sheet."""
        if not settings_df.empty and "Key" in settings_df.columns:
            match = settings_df[settings_df["Key"] == key]
            if not match.empty:
                return match.iloc[0]["Value"]
        return default

    st.subheader("🛠️ Regional & Loan Defaults")
    c1, c2 = st.columns(2)
    
    biz_name = c1.text_input("Business Name", value=str(get_setting_value("biz_name", "Zoe Consults")))
    currency = c2.selectbox("System Currency", ["UGX", "USD", "KES"], index=0)
    
    # Slider for global interest rate defaults
    try:
        def_int_val = int(float(get_setting_value("def_interest", 15)))
    except:
        def_int_val = 15
        
    def_interest = st.slider("Default Interest Rate (%)", 1, 50, def_int_val)

    if st.button("💾 Save Global Configuration", use_container_width=True):
        # Package settings for overwrite
        new_settings = pd.DataFrame([
            {"Key": "biz_name", "Value": biz_name},
            {"Key": "currency", "Value": currency},
            {"Key": "def_interest", "Value": str(def_interest)},
            {"Key": "logo", "Value": current_logo if current_logo else ""} # Preserve logo
        ])
        
        if save_data("Settings", new_settings):
            st.success("System configurations updated! ✅")
            st.rerun()

    st.markdown("---")

    # --- SYSTEM MAINTENANCE ---
    st.subheader("⚠️ System Maintenance")
    st.write("Use these tools to force a re-sync if data appears outdated.")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button("🧹 Clear App Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache wiped. Re-syncing with Google Sheets...")
            st.rerun()
            
    with col_b:
        if st.button("🚪 Hard Reset Session", use_container_width=True):
            # Clears local browser session and force logs out
            st.session_state.clear()
            st.rerun()


# ==============================
# THE MASTER MAIN LOOP
# ==============================

def main():
    """
    The orchestrator of the Zoe Admin system. 
    Handles authentication gates, session security, and page routing.
    """
    
    # 1. APPLY GLOBAL BRANDING IMMEDIATELY
    # This ensures Navy sidebar and Baby Blue backgrounds are always active
    apply_custom_styles()

    # 2. AUTHENTICATION GATEKEEPER
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_page()  # Show ONLY the login interface
        st.stop()     # Kill execution here so no other UI elements load
    
    # 3. SESSION SECURITY
    # If the user is logged in, check if they have been inactive for >15 mins
    check_session_timeout()

    # 4. UI INITIALIZATION
    # Call the Sidebar now that we are authorized.
    # This renders the logo, user info, and navigation buttons.
    sidebar()

    # 5. PAGE ROUTING ENGINE
    # Reads the selection from st.session_state.page set by the sidebar buttons
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

# ==============================
# THE IGNITION SWITCH
# ==============================
if __name__ == "__main__":
    main()




