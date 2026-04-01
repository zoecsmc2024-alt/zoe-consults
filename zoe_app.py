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
from streamlit_calendar import calendar
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
@st.cache_data(ttl=300) 
def get_cached_data(sheet_name):
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
    try:
        sheet = open_main_sheet()
        data = sheet.worksheet(worksheet_name).get_all_records()
        df = pd.DataFrame(data)
        
        # --- THE MASTER FIX ---
        # Identify and remove duplicate columns immediately
        df = df.loc[:, ~df.columns.duplicated()].copy()
        
        # Clean up any purely empty rows Google Sheets might include
        df = df.dropna(how='all').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"⚠️ Error loading {worksheet_name}: {e}")
        return pd.DataFrame()

def save_data(worksheet_name, dataframe):
    try:
        sheet = open_main_sheet()
        worksheet = sheet.worksheet(worksheet_name)
        worksheet.clear()
        
        # Ensure dates are strings to prevent JSON errors
        df_save = dataframe.copy()
        for col in df_save.columns:
            if pd.api.types.is_datetime64_any_dtype(df_save[col]):
                df_save[col] = df_save[col].dt.strftime('%Y-%m-%d')
        
        # Restore spaces for Google Sheets aesthetic
        df_save.columns = [str(c).replace("_", " ") for c in df_save.columns]
        
        data_to_upload = [df_save.columns.values.tolist()] + df_save.values.tolist()
        worksheet.update(data_to_upload)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"❌ Save Error: {e}")
        return False

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

# 1. DEFINE THE COLOR PALETTE
BRANDING = {
    "navy": "#1A285E",      # Deeper, richer Navy
    "soft_blue": "#F0F8FF", # Crisp Baby Blue
    "white": "#FFFFFF",
    "hover_blue": "#D1E9FF" # Slightly darker blue for button hover
}

def apply_custom_styles():
    st.markdown(f"""
        <style>
            /* --- 1. MAIN APP BACKGROUND --- */
            .stApp {{
                background-color: {BRANDING['soft_blue']} !important;
            }}

            /* --- 2. SIDEBAR NAVIGATION --- */
            [data-testid="stSidebar"] {{
                background-color: {BRANDING['navy']} !important;
                border-right: 1px solid rgba(255,255,255,0.1);
            }}

            /* Sidebar text and icons */
            [data-testid="stSidebar"] * {{
                color: {BRANDING['soft_blue']} !important;
            }}

            /* --- 3. BEAUTIFIED SIDEBAR BUTTONS --- */
            section[data-testid="stSidebar"] .stButton > button {{
                background-color: transparent !important;
                color: {BRANDING['soft_blue']} !important;
                border: 1px solid rgba(240, 248, 255, 0.2) !important;
                width: 100% !important;
                text-align: left !important;
                padding: 8px 15px !important;
                margin-bottom: 5px !important;
                border-radius: 10px !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                transition: all 0.3s ease-in-out !important;
                box-shadow: none !important;
            }}

            /* Hover Effect */
            section[data-testid="stSidebar"] .stButton > button:hover {{
                background-color: rgba(240, 248, 255, 0.1) !important;
                border: 1px solid {BRANDING['soft_blue']} !important;
                transform: translateX(5px) !important; /* Subtle slide-in effect */
            }}

            /* Active/Selected Button Logic */
            /* Streamlit uses focus to keep the 'current' button highlighted */
            section[data-testid="stSidebar"] .stButton > button:focus,
            section[data-testid="stSidebar"] .stButton > button:active {{
                background-color: {BRANDING['soft_blue']} !important;
                color: {BRANDING['navy']} !important;
                border: 1px solid {BRANDING['soft_blue']} !important;
                font-weight: bold !important;
            }}

            /* --- 4. DASHBOARD METRIC CARDS --- */
            div[data-testid="stMetric"] {{
                background-color: #FFFFFF !important;
                border: none !important;
                border-left: 5px solid {BRANDING['navy']} !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
                padding: 15px !important;
            }}

            /* --- 5. TABS STYLING --- */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 10px;
            }}

            .stTabs [data-baseweb="tab"] {{
                height: 45px;
                background-color: white !important;
                border-radius: 8px 8px 0 0 !important;
                padding: 10px 20px !important;
                border: 1px solid #ddd !important;
            }}

            .stTabs [aria-selected="true"] {{
                background-color: {BRANDING['navy']} !important;
                color: white !important;
                border: 1px solid {BRANDING['navy']} !important;
            }}

            /* --- 6. HIDE DEFAULT STREAMLIT ELEMENTS --- */
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            header {{visibility: hidden;}}

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

def show_overview():
    st.markdown("## 📊 Financial Dashboard")
    
    # 1. LOAD DATA
    df_raw = get_cached_data("Loans")
    pay_df = get_cached_data("Payments")

    if df_raw.empty:
        st.info("No loan records found.")
        return

    # 2. NORMALIZE
    df = df_raw.copy()
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]

    # 3. SAFE NUMERIC CLEANING (Prevents math crashes)
    for col in ["Interest", "Amount_Paid", "Principal"]:
        # If col doesn't exist, we use a Series of 0s to keep pd.to_numeric happy
        target = df[col] if col in df.columns else pd.Series([0] * len(df))
        df[col] = pd.to_numeric(target, errors="coerce").fillna(0)

    df["End_Date"] = pd.to_datetime(df.get("End_Date"), errors="coerce")
    today = pd.Timestamp.today().normalize()
    
    # Filter Active Portfolio
    active_statuses = ["Active", "Overdue", "Rolled/Overdue"]
    active_df = df[df["Status"].isin(active_statuses)].copy()

    # 4. METRICS ROW
    total_issued = active_df["Principal"].sum()
    total_interest = active_df["Interest"].sum()
    total_collected = df["Amount_Paid"].sum() 
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 ACTIVE PRINCIPAL", f"{total_issued:,.0f} UGX")
    m2.metric("📈 EXPECTED INTEREST", f"{total_interest:,.0f} UGX")
    m3.metric("✅ TOTAL COLLECTED", f"{total_collected:,.0f} UGX")
    
    overdue_count = active_df[active_df["End_Date"] < today].shape[0]
    m4.metric("🚨 OVERDUE FILES", overdue_count)

    # ... Keep your charts logic, but ensure they use these cleaned dataframes!
    
    # ... rest of charts logic ...
    # ... (Keep the rest of your Chart/Table logic as is)
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
        # Combined Cashflow Chart
        if not pay_df.empty and not exp_df.empty:
            pay_df["Date"] = pd.to_datetime(pay_df["Date"], errors='coerce')
            exp_df["Date"] = pd.to_datetime(exp_df["Date"], errors='coerce')
            
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
    st.markdown("<h2 style='color: #2B3F87;'>👥 Borrowers Management</h2>", unsafe_allow_html=True)
    
    borrowers_df = get_cached_data("Borrowers")
    loans_df = get_cached_data("Loans") 
    
    if borrowers_df.empty:
        df = pd.DataFrame(columns=["Borrower_ID", "Name", "Phone", "National_ID", "Address", "Email", "Next_of_Kin", "Status", "Date_Added"])
    else:
        df = borrowers_df.copy()
        df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
        df = df.fillna("")

    tab_view, tab_add, tab_audit = st.tabs(["📑 View All", "➕ Add New", "⚙️ Audit & Manage"])

    with tab_view:
        search = st.text_input("🔍 Search Name, Phone, or ID", key="bor_search").lower()
        v_df = df[df["Name"].str.lower().str.contains(search) | df["Phone"].astype(str).str.contains(search)].copy()
        
        # Original Table Design Restored
        rows_html = ""
        for i, r in v_df.iterrows():
            bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
            rows_html += f"""
            <tr style="background-color: {bg}; border-bottom: 1px solid #eee; font-size: 12px;">
                <td style="padding:12px;"><b>{r['Name']}</b><br><small>ID: {r['Borrower_ID']}</small></td>
                <td style="padding:12px;">📞 {r['Phone']}<br><span style='font-size:10px;'>{r.get('Email', '')}</span></td>
                <td style="padding:12px;">{r.get('National_ID', 'N/A')}</td>
                <td style="padding:12px;">📍 {r.get('Address', 'N/A')}</td>
                <td style="padding:12px; text-align:center;">
                    <span style="background:#2B3F87; color:white; padding:4px 10px; border-radius:12px; font-size:10px;">{r['Status']}</span>
                </td>
            </tr>"""
        st.markdown(f"""<table style="width:100%; border-collapse:collapse; border:1px solid #ddd;">
            <thead style="background:#2B3F87; color:white;"><tr><th>Borrower</th><th>Contact</th><th>NIN</th><th>Address</th><th>Status</th></tr></thead>
            <tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)

    with tab_add:
        with st.form("add_bor_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Name*")
            phone = c2.text_input("Phone*")
            nid = c1.text_input("National ID")
            addr = c2.text_input("Address")
            if st.form_submit_button("🚀 Register Borrower"):
                if name and phone:
                    last_id = pd.to_numeric(df["Borrower_ID"], errors='coerce').max()
                    new_id = int(last_id + 1) if pd.notna(last_id) else 1
                    new_entry = pd.DataFrame([{"Borrower_ID": new_id, "Name": name, "Phone": phone, "National_ID": nid, "Address": addr, "Status": "Active", "Date_Added": datetime.now().strftime("%Y-%m-%d")}])
                    if save_data("Borrowers", pd.concat([df, new_entry], ignore_index=True)):
                        st.success("Registered!"); st.rerun()
    # ==============================
    # TAB 3: AUDIT & MANAGE (Restored Loan History Check)
    # ==============================
    with tab_audit:
        if not df.empty:
            target_name = st.selectbox("Select Borrower to Manage", df["Name"].tolist(), key="audit_m_sel")
            bor_idx = df[df["Name"] == target_name].index[0]
            b_data = df.loc[bor_idx]
            
            # Restored Loan History Check Logic
            if not loans_df.empty:
                l_check = loans_df.copy()
                l_check.columns = [str(c).strip() for c in l_check.columns]
                user_loans = l_check[l_check.get("Borrower") == target_name]
                
                if not user_loans.empty:
                    st.metric("Total Loans Found", len(user_loans))
                    st.markdown(f"#### 📜 Loan History: {target_name}")
                    st.table(user_loans.head(5)) # Shows the recent loans
                else:
                    st.info("ℹ️ No loans recorded for this borrower yet.")
            
            st.divider()
            
            # Edit Section (Restored all fields)
            with st.expander(f"⚙️ Edit Profile: {target_name}"):
                with st.form(f"edit_bor_{target_name}"):
                    ec1, ec2 = st.columns(2)
                    e_name = ec1.text_input("Name", value=str(b_data['Name']))
                    e_phone = ec1.text_input("Phone", value=str(b_data['Phone']))
                    e_nid = ec1.text_input("NIN", value=str(b_data.get('National_ID', '')))
                    e_mail = ec2.text_input("Email", value=str(b_data.get('Email', '')))
                    e_kin = ec2.text_input("Kin", value=str(b_data.get('Next_of_Kin', '')))
                    e_stat = ec2.selectbox("Status", ["Active", "Inactive"], index=0 if b_data['Status'] == "Active" else 1)
                    e_adr = st.text_input("Address", value=str(b_data.get('Address', '')))
                    
                    if st.form_submit_button("💾 Update Profile", use_container_width=True):
                        df.at[bor_idx, 'Name'] = e_name
                        df.at[bor_idx, 'Phone'] = e_phone
                        df.at[bor_idx, 'National_ID'] = e_nid
                        df.at[bor_idx, 'Email'] = e_mail
                        df.at[bor_idx, 'Next_of_Kin'] = e_kin
                        df.at[bor_idx, 'Status'] = e_stat
                        df.at[bor_idx, 'Address'] = e_adr
                        
                        save_ready = df.copy()
                        save_ready.columns = [c.replace("_", " ") for c in save_ready.columns]
                        if save_data("Borrowers", save_ready):
                            st.success("✅ Profile Updated!"); st.rerun()

            st.markdown("### ⚠️ Danger Zone")
            if st.button(f"🗑️ Delete {target_name} Permanently"):
                # Safety check against breaking existing loan records
                if not loans_df.empty and not loans_df[loans_df.iloc[:, 1] == target_name].empty:
                    st.error("❌ Cannot delete borrower with active or past loan history.")
                else:
                    new_df = df.drop(bor_idx)
                    new_df.columns = [c.replace("_", " ") for c in new_df.columns]
                    if save_data("Borrowers", new_df):
                        st.warning("⚠️ Borrower removed."); st.rerun()
# ==============================
# 13. LOANS MANAGEMENT PAGE
# ==============================

import pandas as pd
import re
from datetime import datetime, timedelta
import streamlit as st

def show_loans():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Loans Management</h2>", unsafe_allow_html=True)
    
    # 1. LOAD DATA
    borrowers_df = get_cached_data("Borrowers")
    loans_raw = get_cached_data("Loans")

    if borrowers_df.empty:
        st.warning("⚠️ No borrowers found. Register a client in the Borrowers tab first!")
        return
        
    # --- THE SAFETY SHIELD (Deduplicate & Normalize) ---
    if loans_raw.empty:
        loans_df = pd.DataFrame(columns=[
            "Loan_ID", "Borrower", "Type", "Principal", "Interest_Rate", 
            "Interest", "Total_Repayable", "Amount_Paid", "Start_Date", 
            "End_Date", "Status", "Rollover_Date"
        ])
    else:
        # identify and drop duplicate headers immediately
        loans_df = loans_raw.loc[:, ~loans_raw.columns.duplicated()].copy()
        loans_df.columns = [str(c).strip().replace(" ", "_") for c in loans_df.columns]
        
        # Clean numeric columns immediately to prevent pd.to_numeric crashes
        num_cols = ["Principal", "Interest", "Amount_Paid", "Total_Repayable", "Interest_Rate"]
        for col in num_cols:
            if col in loans_df.columns:
                loans_df[col] = pd.to_numeric(loans_df[col], errors='coerce').fillna(0)

    active_borrowers = borrowers_df[borrowers_df["Status"] == "Active"]
    tab_issue, tab_view, tab_manage = st.tabs(["➕ Issue Loan", "📊 Portfolio", "⚙️ Manage Loans"])

    # ==============================
    # TAB 1: ISSUE LOAN (Restored Design)
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

                if st.form_submit_button("🚀 Confirm & Issue Loan", use_container_width=True):
                    if amount > 0:
                        last_id = pd.to_numeric(loans_df["Loan_ID"], errors='coerce').max()
                        new_id = int(last_id + 1) if pd.notna(last_id) else 1
                        
                        new_loan = pd.DataFrame([{
                            "Loan_ID": new_id, 
                            "Borrower": selected_borrower, 
                            "Type": l_type,
                            "Principal": float(amount), 
                            "Interest_Rate": float(interest_rate),
                            "Interest": float(interest),
                            "Total_Repayable": float(total_due), 
                            "Amount_Paid": 0.0,
                            "Start_Date": date_issued.strftime("%Y-%m-%d"),
                            "End_Date": date_due.strftime("%Y-%m-%d"),
                            "Status": "Active",
                            "Rollover_Date": "-"
                        }])
                        
                        final_save = pd.concat([loans_df, new_loan], ignore_index=True).fillna(0)
                        final_save.columns = [c.replace("_", " ") for c in final_save.columns]
                        
                        if save_data("Loans", final_save):
                            st.success(f"✅ Loan #{new_id} issued!"); st.rerun()

    # ==============================
    # TAB 2: PORTFOLIO (Zoe Soft Blue)
    # ==============================
    with tab_view:
        if not loans_df.empty:
            # Re-calculate balance
            loans_df["Outstanding_Balance"] = loans_df["Total_Repayable"] - loans_df["Amount_Paid"]
            
            relevant_statuses = ["Active", "Overdue", "Rolled/Overdue"]
            display_df = loans_df[loans_df["Status"].isin(relevant_statuses)].copy()

            if display_df.empty:
                st.info("ℹ️ No active loans found.")
            else:
                sel_id = st.selectbox("🔍 Select Loan to Inspect", display_df["Loan_ID"].unique())
                loan_info = display_df[display_df["Loan_ID"].astype(str) == str(sel_id)].iloc[0]
                
                # --- METRIC CARDS ---
                p1, p2, p3 = st.columns(3)
                p1.markdown(f"""<div style="background-color:#F0F8FF;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">RECEIVED</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{loan_info['Amount_Paid']:,.0f} UGX</h3></div>""", unsafe_allow_html=True)
                p2.markdown(f"""<div style="background-color:#ffffff;padding:20px;border-radius:15px;border-left:5px solid #4A90E2;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">OUTSTANDING</p><h3 style="margin:0;color:#4A90E2;font-size:18px;">{loan_info['Outstanding_Balance']:,.0f} UGX</h3></div>""", unsafe_allow_html=True)
                s_color = "#4A90E2" if loan_info['Status'] != "Overdue" else "#FF4B4B"
                p3.markdown(f"""<div style="background-color:#ffffff;padding:20px;border-radius:15px;border-left:5px solid {s_color};box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">STATUS</p><h3 style="margin:0;color:{s_color};font-size:18px;">{str(loan_info['Status']).upper()}</h3></div>""", unsafe_allow_html=True)

                # --- ZOE TABLE ---
                rows_html = ""
                for i, r in display_df.iterrows():
                    bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                    stat_bg = "#4A90E2" if r['Status'] == "Active" else "#FF4B4B" if r['Status'] == "Overdue" else "#FFA500"
                    
                    rows_html += f"""
                    <tr style="background-color: {bg}; border-bottom: 1px solid #ddd; font-size: 12px;">
                        <td style="padding:10px;"><b>#{str(r['Loan_ID']).replace('.0','')}</b></td>
                        <td style="padding:10px;">{r['Borrower']}</td>
                        <td style="padding:10px; text-align:center;">{r.get('Start_Date', '-')}</td>
                        <td style="padding:10px; text-align:right; font-weight:bold; color:#4A90E2;">{r['Principal']:,.0f}</td>
                        <td style="padding:10px; text-align:center;">{r['Interest_Rate']:.1f}%</td>
                        <td style="padding:10px; text-align:right; color:#D32F2F;">{r['Outstanding_Balance']:,.0f}</td>
                        <td style="padding:10px; text-align:center;"><span style="background:{stat_bg}; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r['Status']}</span></td>
                        <td style="padding:10px; text-align:center; font-weight:bold; color:#2B3F87;">{r.get('End_Date', '-')}</td>
                    </tr>"""

                final_html = f"""<div style="border:2px solid #4A90E2; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif;">
                    <thead><tr style="background:#4A90E2; color:white; text-align:left;"><th style="padding:12px;">ID</th><th style="padding:12px;">Borrower</th><th style="padding:12px; text-align:center;">Issued</th><th style="padding:12px; text-align:right;">Principal</th><th style="padding:12px; text-align:center;">Rate</th><th style="padding:12px; text-align:right;">Balance</th><th style="padding:12px; text-align:center;">Status</th><th style="padding:12px; text-align:center;">Due Date</th></tr></thead>
                    <tbody>{rows_html}</tbody></table></div>"""
                st.components.v1.html(final_html, height=500, scrolling=True)

    # ==============================
    # TAB 3: MANAGE LOANS (Fixing NameError)
    # ==============================
    with tab_manage:
        if not loans_df.empty:
            m_options = [f"ID: {str(r['Loan_ID']).replace('.0','')} | {r['Borrower']}" for _, r in loans_df.iterrows()]
            selected_m = st.selectbox("🔍 Select Loan to Edit", m_options)
            
            clean_id = re.search(r'ID:\s*(\d+)', selected_m).group(1)
            idx = loans_df[loans_df["Loan_ID"].astype(str).str.replace(".0","") == clean_id].index[0]
            row = loans_df.loc[idx]

            c1, c2 = st.columns(2)
            with c1:
                up_name = st.text_input("Edit Borrower Name", value=str(row['Borrower']))
                up_p = st.number_input("Adjust Principal", value=float(row['Principal']))
                up_paid = st.number_input("Adjust Amount Paid", value=float(row['Amount_Paid']))
            with c2:
                up_status = st.selectbox("Update Status", ["Active", "Overdue", "Rolled/Overdue", "Closed"], index=0)
                up_end = st.date_input("Adjust End Date", value=pd.to_datetime(row['End_Date']).date())

            # ACTION BUTTONS DEFINED CLEARLY
            b_save, b_del = st.columns(2)
            
            if b_save.button("💾 Save Changes", use_container_width=True):
                loans_df.at[idx, 'Borrower'] = up_name
                loans_df.at[idx, 'Principal'] = up_p
                loans_df.at[idx, 'Amount_Paid'] = up_paid
                loans_df.at[idx, 'Status'] = up_status
                loans_df.at[idx, 'End_Date'] = up_end.strftime('%Y-%m-%d')
                
                final_save = loans_df.copy()
                final_save.columns = [c.replace("_", " ") for c in final_save.columns]
                if save_data("Loans", final_save):
                    st.success("✅ Loan Updated!"); st.rerun()

            if b_del.button("🗑️ Delete Permanently", use_container_width=True):
                final_save = loans_df.drop(idx)
                final_save.columns = [c.replace("_", " ") for c in final_save.columns]
                if save_data("Loans", final_save):
                    st.warning("⚠️ Loan Deleted."); st.rerun()
# ==============================
# 14. PAYMENTS & COLLECTIONS PAGE (Upgraded)
# ==============================

def show_payments():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Payments Management</h2>", unsafe_allow_html=True)
    
    # 1. FETCH DATA
    loans_raw = get_cached_data("Loans")
    payments_raw = get_cached_data("Payments")

    if loans_raw.empty:
        st.info("ℹ️ No loans found in the system.")
        return

    # --- THE SAFETY SHIELD ---
    # Standardize columns for both dataframes
    loans_df = loans_raw.loc[:, ~loans_raw.columns.duplicated()].copy()
    loans_df.columns = [str(c).strip().replace(" ", "_") for c in loans_df.columns]
    
    if payments_raw.empty:
        payments_df = pd.DataFrame(columns=["Payment_ID", "Loan_ID", "Borrower", "Amount", "Date", "Method", "Recorded_By"])
    else:
        payments_df = payments_raw.loc[:, ~payments_raw.columns.duplicated()].copy()
        payments_df.columns = [str(c).strip().replace(" ", "_") for c in payments_df.columns]

    # TABBED INTERFACE (Restored your exact tab structure)
    tab_new, tab_history, tab_manage = st.tabs(["➕ Record Payment", "📜 History & Trends", "⚙️ Edit/Delete"])

    # ==============================
    # TAB 1: RECORD NEW PAYMENT
    # ==============================
    with tab_new:
        # Filter for non-closed loans
        active_loans = loans_df[loans_df["Status"].astype(str).str.lower() != "closed"].copy()
        
        if active_loans.empty:
            st.success("🎉 All loans are currently cleared!")
        else:
            # Selection logic: Create readable labels
            active_loans['Loan_ID_Str'] = active_loans['Loan_ID'].astype(str).str.replace(".0", "", regex=False)
            loan_options = [f"ID: {r['Loan_ID_Str']} - {r['Borrower']}" for _, r in active_loans.iterrows()]
            selected_option = st.selectbox("Select Loan to Credit", loan_options, key="pay_sel_new")
            
            # Extract ID safely
            sel_id_str = selected_option.split(" - ")[0].replace("ID: ", "").strip()
            loan = active_loans[active_loans["Loan_ID_Str"] == sel_id_str].iloc[0]

            # Calculations (Restored logic)
            total_rep = pd.to_numeric(loan.get("Total_Repayable", 0), errors='coerce') or 0.0
            paid_so_far = pd.to_numeric(loan.get("Amount_Paid", 0), errors='coerce') or 0.0
            outstanding = total_rep - paid_so_far

            # Styled Cards (Zoe Green/Navy/Red)
            c1, c2, c3 = st.columns(3)
            status_val = str(loan.get('Status', 'Active')).strip()
            s_color = "#2E7D32" if status_val == "Active" else "#FF4B4B"
            
            c1.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #2B3F87;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">CLIENT</p><h3 style="margin:0;color:#2B3F87;font-size:18px;">{loan['Borrower']}</h3></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid #FF4B4B;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">BALANCE DUE</p><h3 style="margin:0;color:#FF4B4B;font-size:18px;">{outstanding:,.0f} UGX</h3></div>""", unsafe_allow_html=True)
            c3.markdown(f"""<div style="background-color:#fff;padding:20px;border-radius:15px;border-left:5px solid {s_color};box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">STATUS</p><h3 style="margin:0;color:{s_color};font-size:18px;">{status_val}</h3></div>""", unsafe_allow_html=True)

            with st.form("payment_form", clear_on_submit=True):
                col_a, col_b, col_c = st.columns(3)
                pay_amount = col_a.number_input("Amount Received (UGX)", min_value=0, step=10000)
                pay_method = col_b.selectbox("Method", ["Mobile Money", "Cash", "Bank Transfer", "Cheque"])
                pay_date = col_c.date_input("Payment Date", value=datetime.now())
                
                if st.form_submit_button("✅ Post Payment", use_container_width=True):
                    if pay_amount > 0:
                        # 1. Update Payments DF
                        new_p_id = int(pd.to_numeric(payments_df["Payment_ID"], errors='coerce').max() + 1) if not payments_df.empty else 1
                        new_payment = pd.DataFrame([{
                            "Payment_ID": new_p_id, "Loan_ID": sel_id_str, "Borrower": loan["Borrower"], 
                            "Amount": float(pay_amount), "Date": pay_date.strftime("%Y-%m-%d"), 
                            "Method": pay_method, "Recorded_By": st.session_state.get("user", "Zoe Admin")
                        }])

                        # 2. Update Loans DF (Find exact index in original df)
                        idx = loans_df[loans_df["Loan_ID"].astype(str).str.replace(".0", "", regex=False) == sel_id_str].index[0]
                        new_total_paid = paid_so_far + pay_amount
                        loans_df.at[idx, "Amount_Paid"] = new_total_paid
                        
                        if new_total_paid >= (total_rep - 10): # Small margin for rounding
                            loans_df.at[idx, "Status"] = "Closed"

                        # 3. Save Both
                        save_pay = pd.concat([payments_df, new_payment], ignore_index=True)
                        save_pay.columns = [c.replace("_", " ") for c in save_pay.columns]
                        
                        save_loans = loans_df.copy()
                        save_loans.columns = [c.replace("_", " ") for c in save_loans.columns]
                        
                        if save_data("Payments", save_pay) and save_data("Loans", save_loans):
                            st.success(f"✅ Payment of {pay_amount:,.0f} recorded!"); st.rerun()

    # ==============================
    # TAB 2: HISTORY (Restored Level Emojis)
    # ==============================
    with tab_history:
        if not payments_df.empty:
            df_display = payments_df.copy()
            df_display["Amount"] = pd.to_numeric(df_display["Amount"], errors="coerce").fillna(0)
            
            def get_level(amt):
                if amt >= 5000000: return "🟢 Large"
                if amt >= 1000000: return "🔵 Medium"
                return "⚪ Small"
            
            df_display["Level"] = df_display["Amount"].apply(get_level)
            df_display = df_display.sort_values("Date", ascending=False)
            
            st.dataframe(
                df_display[["Level", "Payment_ID", "Loan_ID", "Borrower", "Amount", "Date", "Method"]], 
                use_container_width=True, hide_index=True
            )

    # ==============================
    # TAB 3: EDIT/DELETE
    # ==============================
    with tab_manage:
        if not payments_df.empty:
            # Dropdown for management
            p_df = payments_df.copy()
            p_df['Payment_ID'] = p_df['Payment_ID'].astype(str).str.replace(".0", "", regex=False)
            p_options = [f"PayID: {r['Payment_ID']} | {r['Borrower']} ({r['Amount']:,.0f})" for _, r in p_df.iterrows()]
            
            selected_p = st.selectbox("🔍 Select Payment to Manage", p_options)
            clean_pay_id = re.search(r'PayID:\s*(\d+)', selected_p).group(1)
            
            p_idx = payments_df[payments_df["Payment_ID"].astype(str).str.replace(".0", "", regex=False) == clean_pay_id].index[0]
            p_row = payments_df.loc[p_idx]

            st.divider()
            c_edit1, c_edit2 = st.columns(2)
            new_amt = c_edit1.number_input("Update Amount", value=float(p_row['Amount']))
            new_meth = c_edit1.selectbox("Update Method", ["Mobile Money", "Cash", "Bank Transfer", "Cheque"], index=0)
            
            try: p_date_val = pd.to_datetime(p_row['Date']).date()
            except: p_date_val = datetime.now().date()
            new_date = c_edit2.date_input("Update Date", value=p_date_val)

            b1, b2 = st.columns(2)
            if b1.button("💾 Save Payment Edits", use_container_width=True):
                payments_df.at[p_idx, 'Amount'] = new_amt
                payments_df.at[p_idx, 'Method'] = new_meth
                payments_df.at[p_idx, 'Date'] = new_date.strftime('%Y-%m-%d')
                
                final_p = payments_df.copy()
                final_p.columns = [c.replace("_", " ") for c in final_p.columns]
                if save_data("Payments", final_p):
                    st.success("✅ Payment updated!"); st.rerun()

            if b2.button(f"🗑️ Delete Payment #{clean_pay_id}", use_container_width=True):
                final_p = payments_df.drop(p_idx)
                final_p.columns = [c.replace("_", " ") for c in final_p.columns]
                if save_data("Payments", final_p):
                    st.warning("⚠️ Payment deleted."); st.rerun()
    
# ==============================
# 15. COLLATERAL MANAGEMENT PAGE
# ==============================

def show_collateral():
    st.markdown("<h2 style='color: #2B3F87;'>🛡️ Collateral Management</h2>", unsafe_allow_html=True)
    
    # 1. FETCH ALL DATA
    collateral_raw = get_cached_data("Collateral")
    loans_raw = get_cached_data("Loans") 
    
    # 2. THE SAFETY SHIELD (Deduplicate & Normalize)
    if collateral_raw.empty:
        collateral_df = pd.DataFrame(columns=[
            "Collateral_ID", "Borrower", "Loan_ID", "Type", 
            "Description", "Value", "Status", "Date_Added", "Photo_Link"
        ])
    else:
        collateral_df = collateral_raw.loc[:, ~collateral_raw.columns.duplicated()].copy()
        collateral_df.columns = [str(c).strip().replace(" ", "_") for c in collateral_df.columns]

    if not loans_raw.empty:
        loans_df = loans_raw.loc[:, ~loans_raw.columns.duplicated()].copy()
        loans_df.columns = [str(c).strip().replace(" ", "_") for c in loans_df.columns]
    else:
        loans_df = pd.DataFrame()

    # ==============================
    # TABBED INTERFACE
    # ==============================
    tab_reg, tab_view, tab_manage = st.tabs(["➕ Register Asset", "📋 Inventory & Status", "⚙️ Manage Records"])

    # --- TAB 1: REGISTER COLLATERAL ---
    with tab_reg:
        if loans_df.empty:
            st.warning("⚠️ No loans found. Issue a loan before adding collateral.")
        else:
            # Only show Active/Overdue loans for linking
            available_loans = loans_df[loans_df["Status"].isin(["Active", "Overdue", "Rolled/Overdue"])].copy()

            if available_loans.empty:
                st.info("✅ All current loans are cleared. No new assets need to be secured.")
            else:
                with st.form("collateral_form", clear_on_submit=True):
                    st.markdown("<h4 style='color: #2B3F87;'>🔒 Secure New Asset</h4>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    
                    available_loans['Display'] = available_loans.apply(lambda x: f"ID: {str(x['Loan_ID']).replace('.0','')} - {x['Borrower']}", axis=1)
                    selected_loan = c1.selectbox("Link to Active Loan", available_loans['Display'].unique())
                    
                    # Parse Selection
                    sel_id = selected_loan.split(" - ")[0].replace("ID: ", "").strip()
                    sel_borrower = selected_loan.split(" - ")[1].strip()

                    asset_type = c2.selectbox("Asset Type", ["Logbook (Car)", "Land Title", "Electronics", "House Deed", "Other"])
                    desc = st.text_input("Asset Description", placeholder="e.g. Toyota Prado UBA 123X Black")
                    est_value = st.number_input("Estimated Value (UGX)", min_value=0, step=100000)
                    photo_url = st.text_input("Document/Photo Link (Optional)", placeholder="URL to Google Drive/Photo")

                    if st.form_submit_button("💾 Save & Secure Asset", use_container_width=True):
                        if desc and est_value > 0:
                            new_c_id = int(pd.to_numeric(collateral_df["Collateral_ID"], errors='coerce').max() + 1) if not collateral_df.empty else 1
                            
                            new_asset = pd.DataFrame([{
                                "Collateral_ID": new_c_id, "Borrower": sel_borrower, "Loan_ID": sel_id,
                                "Type": asset_type, "Description": desc, "Value": float(est_value),
                                "Status": "Held", "Date_Added": datetime.now().strftime("%Y-%m-%d"),
                                "Photo_Link": photo_url
                            }])
                            
                            final_df = pd.concat([collateral_df, new_asset], ignore_index=True)
                            final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                            
                            if save_data("Collateral", final_df):
                                st.success(f"✅ Asset #{new_c_id} secured!"); st.rerun()

    # --- TAB 2: VIEW INVENTORY ---
    with tab_view:
        if not collateral_df.empty:
            collateral_df["Value"] = pd.to_numeric(collateral_df["Value"], errors='coerce').fillna(0)
            
            # Branded Metrics
            total_val = collateral_df[collateral_df["Status"] != "Released"]["Value"].sum()
            held_count = collateral_df[collateral_df["Status"].isin(["Held", "In Custody"])].shape[0]
            
            m1, m2 = st.columns(2)
            m1.markdown(f"""<div style="background-color:#F0F8FF;padding:20px;border-radius:15px;border-left:5px solid #2B3F87;"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">TOTAL ASSET SECURITY</p><h2 style="margin:0;color:#2B3F87;">{total_val:,.0f} <span style="font-size:14px;">UGX</span></h2></div>""", unsafe_allow_html=True)
            m2.markdown(f"""<div style="background-color:#ffffff;padding:20px;border-radius:15px;border-left:5px solid #2B3F87;box-shadow:2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0;font-size:12px;color:#666;font-weight:bold;">ACTIVE ASSETS</p><h2 style="margin:0;color:#2B3F87;">{held_count}</h2></div>""", unsafe_allow_html=True)

            # Branded Zoe Table
            rows_html = ""
            for i, r in collateral_df.iterrows():
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                rows_html += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd; font-size:12px;">
                    <td style="padding:10px; color:#666;">#{r['Collateral_ID']}</td>
                    <td style="padding:10px;"><b>{r['Borrower']}</b></td>
                    <td style="padding:10px;">{r['Type']}</td>
                    <td style="padding:10px;">{r['Description']}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{r['Value']:,.0f}</td>
                    <td style="padding:10px; text-align:center;"><span style="background:#2B3F87; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r['Status']}</span></td>
                </tr>"""

            table_html = f"""<div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif;">
                <thead><tr style="background:#2B3F87; color:white; text-align:left;"><th style="padding:12px;">ID</th><th style="padding:12px;">Borrower</th><th style="padding:12px;">Type</th><th style="padding:12px;">Description</th><th style="padding:12px; text-align:right;">Value</th><th style="padding:12px; text-align:center;">Status</th></tr></thead>
                <tbody>{rows_html}</tbody></table></div>"""
            st.components.v1.html(table_html, height=400, scrolling=True)

    # --- TAB 3: MANAGE RECORDS ---
    with tab_manage:
        if not collateral_df.empty:
            m_list = [f"ID: {str(r['Collateral_ID']).replace('.0','')} | {r['Borrower']} - {r['Description']}" for _, r in collateral_df.iterrows()]
            selected_asset = st.selectbox("Select Asset to Modify", m_list)
            
            c_id = selected_asset.split(" | ")[0].replace("ID: ", "").strip()
            idx = collateral_df[collateral_df["Collateral_ID"].astype(str).str.replace(".0","") == c_id].index[0]
            c_row = collateral_df.loc[idx]

            ce1, ce2 = st.columns(2)
            up_desc = ce1.text_input("Edit Description", value=str(c_row["Description"]))
            up_val = ce1.number_input("Edit Value", value=float(c_row["Value"]))
            up_stat = ce2.selectbox("Update Status", ["Held", "Released", "Disposed", "In Custody"], index=0)
            up_link = ce2.text_input("Update Photo URL", value=str(c_row.get("Photo_Link", "")))

            b1, b2 = st.columns(2)
            if b1.button("💾 Save Asset Changes", use_container_width=True):
                collateral_df.at[idx, "Description"] = up_desc
                collateral_df.at[idx, "Value"] = up_val
                collateral_df.at[idx, "Status"] = up_stat
                collateral_df.at[idx, "Photo_Link"] = up_link
                
                final_c = collateral_df.copy()
                final_c.columns = [c.replace("_", " ") for c in final_c.columns]
                if save_data("Collateral", final_c):
                    st.success("✅ Asset record updated!"); st.rerun()

            if b2.button("🗑️ Delete Asset Record", use_container_width=True):
                final_c = collateral_df.drop(idx)
                final_c.columns = [c.replace("_", " ") for c in final_c.columns]
                if save_data("Collateral", final_c):
                    st.warning("⚠️ Asset record deleted."); st.rerun()

import pandas as pd
from datetime import datetime
import streamlit as st

def show_overdue_tracker():
    st.markdown("### 🚨 Loan Overdue & Rollover Tracker")

    try:
        # 1. --- THE DATA FETCH & DEDUPLICATOR ---
        # We fetch fresh to ensure we aren't compounding old data from session memory
        loans_raw = get_cached_data("Loans") 
        ledger_raw = get_cached_data("Ledger")
        
        if loans_raw.empty:
            st.info("💡 No loan records found in the system.")
            return

        # CRITICAL FIX: Kill duplicate columns immediately so math doesn't return a "Table"
        loans = loans_raw.loc[:, ~loans_raw.columns.duplicated()].copy()
        
        # 2. --- NORMALIZE HEADERS (Logic Use Only) ---
        original_headers = list(loans.columns)
        loans.columns = [str(col).strip().replace(" ", "_") for col in loans.columns]
        
        if not ledger_raw.empty:
            ledger = ledger_raw.loc[:, ~ledger_raw.columns.duplicated()].copy()
            ledger.columns = [str(col).strip().replace(" ", "_") for col in ledger.columns]
        else:
            ledger = pd.DataFrame()

        # 3. --- REQUIRED COLUMNS CHECK ---
        required = ["End_Date", "Status", "Loan_ID", "Borrower", "Principal", "Interest"]
        missing = [col for col in required if col not in loans.columns]
        if missing:
            st.error(f"❌ Sheet structure error. Missing: {missing}")
            return

        # 4. --- DATE & NUMERIC PREP ---
        loans['End_Date'] = pd.to_datetime(loans['End_Date'], errors='coerce')
        today = datetime.now()

        # 5. --- FILTER OVERDUE ACCOUNTS ---
        # Logic: Only Active/Overdue loans where the clock has run out
        overdue_df = loans[
            (loans['Status'].isin(["Active", "Overdue", "Rolled/Overdue"])) &
            (loans['End_Date'] < today)
        ].copy()

        if overdue_df.empty:
            st.success("✨ Excellent! All accounts are currently up to date.")
            return

        st.warning(f"Found {len(overdue_df)} accounts requiring monthly rollover.")

        # 6. --- BRANDED PREVIEW TABLE (Blue Zoe Theme) ---
        rows_html = ""
        for i, r in overdue_df.iterrows():
            # Force numeric for preview math
            p_val = pd.to_numeric(r.get('Principal', 0), errors='coerce') or 0
            i_val = pd.to_numeric(r.get('Interest', 0), errors='coerce') or 0
            preview_total = p_val + i_val
            
            rows_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding:10px;"><b>#{str(r['Loan_ID']).replace('.0','')}</b></td>
                <td style="padding:10px;">{r['Borrower']}</td>
                <td style="padding:10px; text-align:right;">{p_val:,.0f}</td>
                <td style="padding:10px; text-align:right; color:#D32F2F;">{i_val:,.0f}</td>
                <td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{preview_total:,.0f}</td>
                <td style="padding:10px; text-align:center; color:#666;">{pd.to_datetime(r['End_Date']).strftime('%d %b %y')}</td>
            </tr>"""

        st.components.v1.html(f"""
        <div style="border:2px solid #4A90E2; border-radius:10px; overflow:hidden; font-family:sans-serif; font-size:13px; background:white;">
            <table style="width:100%; border-collapse:collapse;">
                <tr style="background:#4A90E2; color:white; text-align:left;">
                    <th style="padding:12px;">ID</th><th style="padding:12px;">Borrower</th>
                    <th style="padding:12px; text-align:right;">Old Principal</th>
                    <th style="padding:12px; text-align:right;">+ Interest</th>
                    <th style="padding:12px; text-align:right;">New Principal (P+I)</th>
                    <th style="padding:12px; text-align:center;">Missed Date</th>
                </tr>
                {rows_html}
            </table>
        </div>""", height=300, scrolling=True)

        # 7. --- PREP LEDGER BALANCES ---
        latest_ledger = pd.DataFrame()
        if not ledger.empty and "Loan_ID" in ledger.columns:
            ledger['Date'] = pd.to_datetime(ledger.get('Date'), errors='coerce')
            latest_ledger = ledger.sort_values('Date').groupby("Loan_ID").tail(1)

        # 8. --- THE ROLLOVER ENGINE ---
        if st.button("🔄 Execute Monthly Rollover (Compound All)", use_container_width=True):
            updated_df = loans.copy()
            count = 0

            for i, r in overdue_df.iterrows():
                l_id = str(r.get('Loan_ID')).replace(".0", "")
                
                # A. Get compounding amount from Ledger Balance (The most accurate source)
                final_amt = 0
                if not latest_ledger.empty:
                    match = latest_ledger[latest_ledger["Loan_ID"].astype(str).str.replace(".0","") == l_id]
                    if not match.empty and "Balance" in match.columns:
                        final_amt = float(match['Balance'].values[0])

                # B. Fallback: If Ledger is empty, use the math from the Loan record
                if final_amt <= 0:
                    final_amt = float(r.get('Principal', 0)) + float(r.get('Interest', 0))

                # C. The logic shift: Principal = New Amount, Date = Date + 30 days
                new_due_date = r['End_Date'] + pd.DateOffset(months=1)

                updated_df.at[i, 'Principal'] = final_amt
                updated_df.at[i, 'End_Date'] = new_due_date
                updated_df.at[i, 'Status'] = "Rolled/Overdue"
                updated_df.at[i, 'Rollover_Date'] = datetime.now().strftime('%Y-%m-%d')
                count += 1

            # 9. --- DATE STRINGIFICATION ---
            # Google Sheets hates Python Datetime objects
            for col in ["Start_Date", "End_Date", "Rollover_Date", "Due_Date"]:
                if col in updated_df.columns:
                    updated_df[col] = pd.to_datetime(updated_df[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")

            # 10. --- SAFE HEADER RESTORE ---
            # We map back to the EXACT original headers from the sheet to avoid name drifts
            updated_df.columns = original_headers
            
            if save_data("Loans", updated_df):
                st.session_state.loans = updated_df # Update local memory
                st.success(f"✅ Mission Accomplished! {count} loans compounded and rolled over.")
                st.rerun()
            else:
                st.error("❌ Save failed. Connection to Google Sheets was interrupted.")

    except Exception as e:
        st.error(f"🚨 Logic Error: {str(e)}")
# ==============================
# 17. ACTIVITY CALENDAR PAGE
# ==============================

def show_calendar():
    st.markdown("<h2 style='color: #2B3F87;'>📅 Activity Calendar</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA
    loans_raw = get_cached_data("Loans")

    if loans_raw.empty:
        st.info("📅 Calendar is clear! No active loans to track.")
        return

    # 2. DATA PREPARATION (The Safety Shield)
    # Standardize headers and remove duplicates
    loans_df = loans_raw.loc[:, ~loans_raw.columns.duplicated()].copy()
    loans_df.columns = [str(c).strip().replace(" ", "_") for c in loans_df.columns]

    # Force proper data types for date and math
    loans_df["End_Date"] = pd.to_datetime(loans_df["End_Date"], errors="coerce")
    for col in ["Total_Repayable", "Principal", "Interest"]:
        if col in loans_df.columns:
            loans_df[col] = pd.to_numeric(loans_df[col], errors="coerce").fillna(0)

    # Reference Date: Today
    today = pd.Timestamp.today().normalize()
    
    # Filter for active/overdue only
    active_loans = loans_df[loans_df["Status"].isin(["Active", "Overdue", "Rolled/Overdue"])].copy()

    # ==============================
    # THE VISUAL CALENDAR WIDGET
    # ==============================
    from streamlit_calendar import calendar
    
    calendar_events = []
    for _, r in active_loans.iterrows():
        if pd.notna(r['End_Date']):
            # Red for overdue, Blue for upcoming
            is_overdue = r['End_Date'].date() < today.date()
            ev_color = "#FF4B4B" if is_overdue else "#4A90E2"
            
            # Amount fallback logic
            disp_amt = r['Total_Repayable'] if r['Total_Repayable'] > 0 else (r['Principal'] + r['Interest'])
            
            calendar_events.append({
                "title": f"UGX {disp_amt:,.0f} - {r['Borrower']}",
                "start": r['End_Date'].strftime("%Y-%m-%d"),
                "end": r['End_Date'].strftime("%Y-%m-%d"),
                "color": ev_color,
                "allDay": True,
            })

    calendar_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"},
        "initialView": "dayGridMonth",
        "selectable": True,
    }

    # Render widget
    calendar(events=calendar_events, options=calendar_options, key="collection_cal")
    
    st.markdown("---")

    # ==============================
    # DAILY OPERATIONAL METRICS
    # ==============================
    due_today_df = active_loans[active_loans["End_Date"].dt.date == today.date()]
    upcoming_df = active_loans[
        (active_loans["End_Date"] > today) & 
        (active_loans["End_Date"] <= today + pd.Timedelta(days=7))
    ]
    overdue_df = active_loans[active_loans["End_Date"] < today].copy()

    m1, m2, m3 = st.columns(3)
    m1.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">📌 DUE TODAY</p><h3 style="margin:0; color:#2B3F87;">{len(due_today_df)} <span style="font-size:14px;">TASKS</span></h3></div>""", unsafe_allow_html=True)
    m2.markdown(f"""<div style="background-color: #F0F8FF; padding: 20px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">⏳ NEXT 7 DAYS</p><h3 style="margin:0; color:#2B3F87;">{len(upcoming_df)} <span style="font-size:14px;">PENDING</span></h3></div>""", unsafe_allow_html=True)
    m3.markdown(f"""<div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);"><p style="margin:0; font-size:12px; color:#666; font-weight:bold;">🔴 OVERDUE CASES</p><h3 style="margin:0; color:#FF4B4B;">{len(overdue_df)} <span style="font-size:14px;">URGENT</span></h3></div>""", unsafe_allow_html=True)

    # ==============================
    # ACTION TABLES
    # ==============================
    st.write("")
    
    # 1. DUE TODAY
    st.markdown("<h4 style='color: #2B3F87;'>📌 Action Items for Today</h4>", unsafe_allow_html=True)
    if due_today_df.empty:
        st.success("✨ No deadlines for today. Focus on follow-ups!")
    else:
        today_rows = ""
        for i, r in due_today_df.iterrows():
            bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
            amt = r['Total_Repayable'] if r['Total_Repayable'] > 0 else (r['Principal'] + r['Interest'])
            today_rows += f"""<tr style="background-color: {bg}; border-bottom: 1px solid #ddd;">
                <td style="padding:10px;"><b>#{str(r['Loan_ID']).replace('.0','')}</b></td>
                <td style="padding:10px;">{r['Borrower']}</td>
                <td style="padding:10px; text-align:right; font-weight:bold; color:#2B3F87;">{amt:,.0f}</td>
                <td style="padding:10px; text-align:center;"><span style="background:#2B3F87; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">💰 COLLECT</span></td>
            </tr>"""
        st.markdown(f"""<div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
            <tr style="background:#2B3F87; color:white;"><th style="padding:10px;">Loan ID</th><th style="padding:10px;">Borrower</th><th style="padding:10px; text-align:right;">Amount Due</th><th style="padding:10px; text-align:center;">Action</th></tr>{today_rows}</table></div>""", unsafe_allow_html=True)

    # 2. IMMEDIATE FOLLOW-UP
    st.markdown("<br><h4 style='color: #FF4B4B;'>🔴 Past Due (Requires Attention)</h4>", unsafe_allow_html=True)
    if overdue_df.empty:
        st.success("Clean Sheet! No overdue loans found. 🎉")
    else:
        overdue_df["Days_Late"] = (today - overdue_df["End_Date"]).dt.days
        overdue_df = overdue_df.sort_values("Days_Late", ascending=False)
        od_rows = ""
        for i, r in overdue_df.iterrows():
            late_color = "#FF4B4B" if r['Days_Late'] > 7 else "#FFA500"
            od_rows += f"""<tr style="background-color: #FFF5F5; border-bottom: 1px solid #FFDADA;">
                <td style="padding:10px;"><b>#{str(r['Loan_ID']).replace('.0','')}</b></td>
                <td style="padding:10px;">{r['Borrower']}</td>
                <td style="padding:10px; text-align:center; font-weight:bold; color:{late_color};">{r['Days_Late']} Days</td>
                <td style="padding:10px; text-align:center;"><span style="background:{late_color}; color:white; padding:2px 8px; border-radius:10px; font-size:10px;">{r['Status']}</span></td>
            </tr>"""
        st.markdown(f"""<div style="border:2px solid #FF4B4B; border-radius:10px; overflow:hidden;"><table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px;">
            <tr style="background:#FF4B4B; color:white;"><th style="padding:10px;">Loan ID</th><th style="padding:10px;">Borrower</th><th style="padding:10px; text-align:center;">Late By</th><th style="padding:10px; text-align:center;">Status</th></tr>{od_rows}</table></div>""", unsafe_allow_html=True)
# ==============================
# 18. EXPENSE MANAGEMENT PAGE
# ==============================

def show_expenses():
    st.markdown("<h2 style='color: #2B3F87;'>📁 Expense Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA & DEDUPLICATE
    raw_df = get_cached_data("Expenses")
    
    # Pre-defined Master Categories for Zoe Consults
    EXPENSE_CATS = ["Rent", "Insurance Account", "Utilities", "Salaries", "Marketing", "Office Expenses", "Other"]

    if raw_df.empty:
        df = pd.DataFrame(columns=["Expense_ID", "Category", "Amount", "Date", "Description", "Payment_Date", "Receipt_No"])
    else:
        # Standardize headers (Logic uses underscores, Sheet uses spaces)
        df = raw_df.loc[:, ~raw_df.columns.duplicated()].copy()
        df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
        # Cast numeric for analytics
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # --- TABS ---
    tab_add, tab_view, tab_manage = st.tabs(["➕ Record Expense", "📊 Spending Analysis", "⚙️ Manage Records"])

    # ==============================
    # TAB 1: ADD NEW EXPENSE
    # ==============================
    with tab_add:
        with st.form("add_expense_form", clear_on_submit=True):
            st.markdown("<h4 style='color: #2B3F87;'>📝 Log Business Outflow</h4>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            category = col1.selectbox("Expense Category", EXPENSE_CATS)
            amount = col2.number_input("Amount (UGX)", min_value=0, step=5000)
            
            desc = st.text_input("Description", placeholder="e.g. Office Electricity March 2026")
            
            c_date, c_receipt = st.columns(2)
            p_date = c_date.date_input("Payment Date", value=datetime.now())
            receipt_no = c_receipt.text_input("Receipt / Invoice #", placeholder="Optional")

            if st.form_submit_button("🚀 Save Expense Record", use_container_width=True):
                if amount > 0 and desc:
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
                    
                    final_df = pd.concat([df, new_entry], ignore_index=True)
                    # Restore spaces for Google Sheets
                    final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                    
                    if save_data("Expenses", final_df):
                        st.success(f"✅ Logged {amount:,.0f} UGX for {category}!"); st.rerun()
                else:
                    st.error("⚠️ Amount and Description are required.")

    # ==============================
    # TAB 2: ANALYSIS & LOG (Original Zoe Styling)
    # ==============================
    with tab_view:
        if not df.empty:
            total_spent = df["Amount"].sum()
            
            # Metric Box
            st.markdown(f"""
                <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL BUSINESS OUTFLOW</p>
                    <h2 style="margin:0; color:#FF4B4B;">{total_spent:,.0f} <span style="font-size:14px;">UGX</span></h2>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            
            # Pie Chart
            cat_summary = df.groupby("Category")["Amount"].sum().reset_index()
            fig_exp = px.pie(cat_summary, names="Category", values="Amount", 
                             hole=0.4, title="Spending Distribution",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_exp.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="#2B3F87")
            st.plotly_chart(fig_exp, use_container_width=True)
            
            # Detailed Log Table
            st.markdown("<h4 style='color: #2B3F87;'>📜 Detailed Expense Log</h4>", unsafe_allow_html=True)
            rows_html = ""
            sorted_df = df.sort_values("Payment_Date", ascending=False)
            
            for i, r in sorted_df.iterrows():
                bg = "#F0F8FF" if i % 2 == 0 else "#FFFFFF"
                rows_html += f"""
                <tr style="background-color: {bg}; border-bottom: 1px solid #ddd; font-size: 12px;">
                    <td style="padding:10px; color:#666;">{r.get('Payment_Date', '-')}</td>
                    <td style="padding:10px;"><b>{r['Category']}</b></td>
                    <td style="padding:10px;">{r['Description']}</td>
                    <td style="padding:10px; text-align:right; font-weight:bold; color:#FF4B4B;">{r['Amount']:,.0f}</td>
                    <td style="padding:10px; text-align:center; font-size:10px;">{r.get('Receipt_No', '-')}</td>
                </tr>"""

            st.markdown(f"""
                <div style="border:2px solid #2B3F87; border-radius:10px; overflow:hidden;">
                    <table style="width:100%; border-collapse:collapse; font-family:sans-serif;">
                        <thead><tr style="background:#2B3F87; color:white; text-align:left;">
                            <th style="padding:12px;">Date</th><th style="padding:12px;">Category</th><th style="padding:12px;">Description</th>
                            <th style="padding:12px; text-align:right;">Amount (UGX)</th><th style="padding:12px; text-align:center;">Receipt</th>
                        </tr></thead><tbody>{rows_html}</tbody>
                    </table>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("💡 No expense data recorded yet.")

    # ==============================
    # TAB 3: MANAGE RECORDS
    # ==============================
    with tab_manage:
        if not df.empty:
            m_list = [f"ID: {str(r['Expense_ID']).replace('.0','')} | {r['Category']} - {r['Amount']:,.0f}" for _, r in df.iterrows()]
            selected = st.selectbox("Select Record to Modify/Delete", m_list)
            
            e_id = selected.split(" | ")[0].replace("ID: ", "").strip()
            idx = df[df["Expense_ID"].astype(str).str.replace(".0","") == e_id].index[0]
            e_row = df.loc[idx]

            st.write(f"Modifying record for: **{e_row['Category']}**")
            up_amt = st.number_input("Update Amount", value=float(e_row["Amount"]))
            up_desc = st.text_input("Update Description", value=str(e_row["Description"]))

            b1, b2 = st.columns(2)
            if b1.button("💾 Save Changes", use_container_width=True):
                df.at[idx, "Amount"] = up_amt
                df.at[idx, "Description"] = up_desc
                final_e = df.copy()
                final_e.columns = [c.replace("_", " ") for c in final_e.columns]
                if save_data("Expenses", final_e):
                    st.success("✅ Record updated!"); st.rerun()

            if b2.button("🗑️ Delete Permanently", use_container_width=True):
                final_e = df.drop(idx)
                final_e.columns = [c.replace("_", " ") for c in final_e.columns]
                if save_data("Expenses", final_e):
                    st.warning("⚠️ Record deleted."); st.rerun()
# ==============================
# 19. PETTY CASH MANAGEMENT PAGE
# ==============================

def show_petty_cash():
    st.markdown("<h2 style='color: #2B3F87;'>💵 Petty Cash Management</h2>", unsafe_allow_html=True)

    # 1. FETCH DATA & DEDUPLICATE
    raw_df = get_cached_data("PettyCash")

    if raw_df.empty:
        df = pd.DataFrame(columns=["Transaction_ID", "Type", "Amount", "Date", "Description"])
    else:
        # Standardize headers (Spaces -> Underscores)
        df = raw_df.loc[:, ~raw_df.columns.duplicated()].copy()
        df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
        
        # Clean numeric data for math
        df["Transaction_ID"] = pd.to_numeric(df["Transaction_ID"], errors='coerce').fillna(0).astype(int)
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # 2. SMART BALANCE METRICS
    inflow = df[df["Type"] == "In"]["Amount"].sum()
    outflow = df[df["Type"] == "Out"]["Amount"].sum()
    balance = inflow - outflow

    # --- STYLED NEON CARDS (Restored) ---
    c1, c2, c3 = st.columns(3)
    
    # Inflow Card
    c1.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #10B981; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL CASH IN</p>
            <h3 style="margin:0; color:#10B981;">{inflow:,.0f} <span style="font-size:14px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # Outflow Card
    c2.markdown(f"""
        <div style="background-color: #ffffff; padding: 20px; border-radius: 15px; border-left: 5px solid #FF4B4B; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <p style="margin:0; font-size:12px; color:#666; font-weight:bold;">TOTAL CASH OUT</p>
            <h3 style="margin:0; color:#FF4B4B;">{outflow:,.0f} <span style="font-size:14px;">UGX</span></h3>
        </div>
    """, unsafe_allow_html=True)

    # Balance Card (Dynamic Color Logic)
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
    tab_record, tab_history, tab_manage = st.tabs(["➕ Record Entry", "📜 Transaction History", "⚙️ Manage Records"])

    # --- TAB 1: RECORD ENTRY ---
    with tab_record:
        with st.form("petty_cash_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            ttype = col_a.selectbox("Transaction Type", ["Out", "In"])
            t_amount = col_b.number_input("Amount (UGX)", min_value=0, step=1000)
            desc = st.text_input("Purpose / Description", placeholder="e.g., Office Water Refill")

            if st.form_submit_button("💾 Save to Cashbook", use_container_width=True):
                if t_amount > 0 and desc:
                    new_id = int(df["Transaction_ID"].max() + 1) if not df.empty else 1
                    new_row = pd.DataFrame([{
                        "Transaction_ID": new_id,
                        "Type": ttype,
                        "Amount": float(t_amount),
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Description": desc
                    }])
                    
                    final_df = pd.concat([df, new_row], ignore_index=True)
                    # Restore spaces for Google Sheets
                    final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                    
                    if save_data("PettyCash", final_df):
                        st.success(f"✅ Successfully recorded {t_amount:,.0f} UGX!"); st.rerun()
                else:
                    st.error("⚠️ Please provide amount and description.")

    # --- TAB 2: HISTORY (Styled Table) ---
    with tab_history:
        if not df.empty:
            def color_type(val):
                return 'color: #10B981; font-weight:bold;' if val == 'In' else 'color: #FF4B4B; font-weight:bold;'
            
            # Show Styled Dataframe
            st.dataframe(
                df.sort_values("Date", ascending=False)
                .style.applymap(color_type, subset=['Type'])
                .format({"Amount": "{:,.0f}"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("💡 No transaction history available.")

    # --- TAB 3: MANAGE RECORDS ---
    with tab_manage:
        if not df.empty:
            options = [f"ID: {int(row['Transaction_ID'])} | {row['Type']} - {row['Description']}" for _, row in df.iterrows()]
            selected_task = st.selectbox("Select Entry to Modify", options)
            
            sel_id = int(selected_task.split(" | ")[0].replace("ID: ", ""))
            idx = df[df["Transaction_ID"] == sel_id].index[0]
            item = df.loc[idx]

            st.divider()
            c_up_type = st.selectbox("Update Type", ["In", "Out"], index=0 if item["Type"] == "In" else 1)
            c_up_amt = st.number_input("Update Amount", value=float(item["Amount"]))
            c_up_desc = st.text_input("Update Description", value=str(item["Description"]))

            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("💾 Save Changes", use_container_width=True):
                df.at[idx, "Type"] = c_up_type
                df.at[idx, "Amount"] = c_up_amt
                df.at[idx, "Description"] = c_up_desc
                
                final_df = df.copy()
                final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                if save_data("PettyCash", final_df):
                    st.success("✅ Updated!"); st.rerun()

            if c_btn2.button("🗑️ Delete Permanently", use_container_width=True):
                final_df = df.drop(idx)
                final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                if save_data("PettyCash", final_df):
                    st.warning("⚠️ Entry deleted."); st.rerun()

# ==============================
# 20. PAYROLL MANAGEMENT PAGE
# ==============================

def show_payroll():
    if st.session_state.get("role") != "Admin":
        st.error("🔒 Restricted Access: Only Administrators can process payroll.")
        return

    st.markdown("<h2 style='color: #2B3F87;'>🧾 Payroll Management</h2>", unsafe_allow_html=True)

    # 1. FETCH & REPAIR DATA
    raw_df = get_cached_data("Payroll")
    # All columns you requested must stay. No drops.
    required_columns = [
        "Payroll_ID", "Employee", "TIN", "Designation", "Mob_No", "Account_No", "NSSF_No",
        "Arrears", "Basic_Salary", "Absent_Deduction", "LST", "Gross_Salary", 
        "PAYE", "NSSF_5", "Advance_DRS", "Other_Deductions", "Net_Pay", 
        "NSSF_10", "NSSF_15", "Date"
    ]
    
    if raw_df.empty:
        df = pd.DataFrame(columns=required_columns)
    else:
        # Standardize headers while keeping original names
        df = raw_df.loc[:, ~raw_df.columns.duplicated()].copy()
        df.columns = [str(col).strip().replace(" ", "_") for col in df.columns]
        for col in required_columns:
            if col not in df.columns: df[col] = 0
        df = df.fillna(0)

    # 2. UGANDA TAX ENGINE (The Math You Requested)
    def calculate_uganda_payroll(basic, arrears, absent, advance, other):
        gross = (float(basic) + float(arrears)) - float(absent)
        # LST: Simplified rule for Ug 
        lst = 100000 / 12 if gross > 1000000 else 0
        n5 = gross * 0.05
        n10 = gross * 0.10
        n15 = n5 + n10
        taxable = gross - n5
        
        # PAYE Brackets
        paye = 0
        if taxable > 410000: paye = 25000 + (0.30 * (taxable - 410000))
        elif taxable > 282000: paye = (taxable - 282000) * 0.20 + 4700
        elif taxable > 235000: paye = (taxable - 235000) * 0.10
        
        total_deductions = paye + lst + n5 + float(advance) + float(other)
        net = gross - total_deductions
        return {
            "gross": round(gross), "lst": round(lst), "n5": round(n5), 
            "n10": round(n10), "n15": round(n15), "paye": round(paye), "net": round(net)
        }

    tab_process, tab_logs = st.tabs(["➕ Process Salary", "📜 Payroll History"])

    # ==============================
    # TAB 1: PROCESS SALARY
    # ==============================
    with tab_process:
        with st.form("new_payroll_form", clear_on_submit=True):
            st.markdown("<h4 style='color: #2B3F87;'>📝 Employee Information</h4>", unsafe_allow_html=True)
            name = st.text_input("Employee Full Name*")
            c1, c2, c3 = st.columns(3)
            f_tin = c1.text_input("TIN Number")
            f_desig = c2.text_input("Designation")
            f_mob = c3.text_input("Mob No.")
            
            c4, c5 = st.columns(2)
            f_acc = c4.text_input("Account No.")
            f_nssf_no = c5.text_input("NSSF No.")
            
            st.write("---")
            st.markdown("<h4 style='color: #2B3F87;'>💰 Earnings & Deductions</h4>", unsafe_allow_html=True)
            c6, c7, c8 = st.columns(3)
            f_basic = c6.number_input("BASIC SALARY", min_value=0.0, step=50000.0)
            f_arrears = c7.number_input("ARREARS", min_value=0.0)
            f_absent = c8.number_input("ABSENTEEISM DEDUCTION", min_value=0.0)
            
            c9, c10 = st.columns(2)
            f_adv = c9.number_input("ADVANCE / S.DRS", min_value=0.0)
            f_other = c10.number_input("OTHER DEDUCTIONS", min_value=0.0)

            if st.form_submit_button("💳 Confirm & Release Payment", use_container_width=True):
                if name and f_basic > 0:
                    calc = calculate_uganda_payroll(f_basic, f_arrears, f_absent, f_adv, f_other)
                    
                    new_id = int(pd.to_numeric(df["Payroll_ID"], errors='coerce').max() + 1) if not df.empty else 1
                    new_row = pd.DataFrame([{
                        "Payroll_ID": new_id, "Employee": name, "TIN": f_tin, "Designation": f_desig, 
                        "Mob_No": f_mob, "Account_No": f_acc, "NSSF_No": f_nssf_no, "Arrears": f_arrears,
                        "Basic_Salary": f_basic, "Absent_Deduction": f_absent, "Gross_Salary": calc['gross'],
                        "LST": calc['lst'], "PAYE": calc['paye'], "NSSF_5": calc['n5'], "NSSF_10": calc['n10'], 
                        "NSSF_15": calc['n15'], "Advance_DRS": f_adv, "Other_Deductions": f_other, 
                        "Net_Pay": calc['net'], "Date": datetime.now().strftime("%Y-%m-%d")
                    }])
                    
                    # Merge & Restore Spaced Headers for Sheets
                    final_df = pd.concat([df, new_row], ignore_index=True)
                    final_df.columns = [c.replace("_", " ") for c in final_df.columns]
                    
                    if save_data("Payroll", final_df):
                        st.success(f"✅ Payroll processed for {name}!"); st.rerun()
                else:
                    st.error("⚠️ Employee Name and Basic Salary are required.")

    # ==============================
    # TAB 2: HISTORY & PDF DOWNLOAD
    # ==============================
    with tab_logs:
        if not df.empty:
            p_col1, p_col2 = st.columns([4, 1])
            p_col1.markdown(f"<h3 style='color: #2B3F87;'>{datetime.now().strftime('%B %Y')} Payroll Summary</h3>", unsafe_allow_html=True)
            
            # Formatting for display
            def fm(x): 
                try: return f"{int(float(x)):,}" 
                except: return "0"

            # Build rows for the Print View
            rows_html = ""
            for i, r in df.iterrows():
                rows_html += f"""
                <tr style="font-size:10px; border-bottom:1px solid #ddd;">
                    <td style='text-align:center; padding:10px;'>{i+1}</td>
                    <td style='padding:10px;'><b>{r['Employee']}</b><br><small>{r.get('Designation', '-')}</small></td>
                    <td style='text-align:right; padding:10px;'>{fm(r['Arrears'])}</td>
                    <td style='text-align:right; padding:10px;'>{fm(r['Basic_Salary'])}</td>
                    <td style='text-align:right; padding:10px; font-weight:bold;'>{fm(r['Gross_Salary'])}</td>
                    <td style='text-align:right; padding:10px;'>{fm(r['PAYE'])}</td>
                    <td style='text-align:right; padding:10px;'>{fm(r['NSSF_5'])}</td>
                    <td style='text-align:right; padding:10px; background:#E3F2FD; font-weight:bold;'>{fm(r['Net_Pay'])}</td>
                    <td style='text-align:right; padding:10px; background:#FFF9C4;'>{fm(r['NSSF_10'])}</td>
                    <td style='text-align:right; padding:10px; background:#FFF9C4; font-weight:bold;'>{fm(r['NSSF_15'])}</td>
                </tr>"""

            printable_html = f"""
            <html><head><style>
                body {{ font-family: sans-serif; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background: #2B3F87; color: white; padding: 10px; font-size:11px; }}
                @media print {{ @page {{ size: landscape; margin: 1cm; }} }}
            </style></head><body>
                <div style="text-align:center; border-bottom:2px solid #2B3F87; margin-bottom:15px;">
                    <h2 style="margin:0; color:#2B3F87;">ZOE CONSULTS SMC LTD</h2>
                    <p><b>MONTHLY PAYROLL REPORT - {datetime.now().strftime('%B %Y')}</b></p>
                </div>
                <table border="1">
                    <thead><tr><th>S/N</th><th>Employee</th><th>Arrears</th><th>Basic</th><th>Gross</th><th>PAYE</th><th>NSSF(5)</th><th>Net Pay</th><th>NSSF(10)</th><th>NSSF(15)</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </body></html>"""

            # PDF Print Trigger
            if p_col2.button("📥 Download/Print PDF", use_container_width=True):
                # Trigger window.print() via hidden component
                st.components.v1.html(printable_html + "<script>window.print();</script>", height=0)

            # Scrollable Screen Preview
            st.components.v1.html(printable_html, height=500, scrolling=True)

            # CSV Backup
            csv_data = raw_df.to_csv(index=False).encode('utf-8')
            st.download_button("📄 Export to CSV", data=csv_data, file_name=f"Payroll_{datetime.now().strftime('%b_%Y')}.csv", mime="text/csv")
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
# 22. MASTER LEDGER & STATEMENTS (Cleaned & De-duplicated)
# ==============================
def show_ledger():
    st.markdown("<h2 style='color: #2B3F87;'>📘 Master Ledger</h2>", unsafe_allow_html=True)
    
    # 1. LOAD DATA
    loans_raw = get_cached_data("Loans")
    payments_raw = get_cached_data("Payments")
    borrowers_df = get_cached_data("Borrowers")

    if loans_raw.empty:
        st.info("No loan records found to generate a ledger.")
        return

    # 2. DEDUPLICATE & NORMALIZE
    loans_df = loans_raw.loc[:, ~loans_raw.columns.duplicated()].copy()
    loans_df.columns = [str(c).strip().replace(" ", "_") for c in loans_df.columns]
    
    if not payments_raw.empty:
        payments_df = payments_raw.loc[:, ~payments_raw.columns.duplicated()].copy()
        payments_df.columns = [str(c).strip().replace(" ", "_") for c in payments_df.columns]
    else:
        payments_df = pd.DataFrame()

    # 3. CLIENT SELECTION
    # We group by borrower name so we can pull ALL loans for one person
    client_list = sorted(loans_df["Borrower"].unique().tolist())
    selected_client = st.selectbox("🔍 Select Client for Consolidated Statement", client_list)
    
    # Filter for this specific client
    client_loans = loans_df[loans_df["Borrower"] == selected_client].copy()
    
    # 4. CALCULATE GRAND TOTAL FOR TOP CARD
    # Grand Total = Sum of (Total Repayable - Amount Paid) for all client loans
    grand_outstanding = 0
    for _, l_row in client_loans.iterrows():
        # Fallback if Total_Repayable isn't explicitly calculated in the sheet
        p_val = pd.to_numeric(l_row.get('Principal', 0), errors='coerce') or 0
        i_val = pd.to_numeric(l_row.get('Interest', 0), errors='coerce') or 0
        paid_val = pd.to_numeric(l_row.get('Amount_Paid', 0), errors='coerce') or 0
        
        t_repay = pd.to_numeric(l_row.get('Total_Repayable', 0), errors='coerce') or (p_val + i_val)
        grand_outstanding += (t_repay - paid_val)

    # TOP METRIC CARD
    st.markdown(f"""
        <div style="background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 5px solid #2B3F87; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); margin-bottom: 25px;">
            <p style="margin:0; font-size:13px; color:#666; font-weight:bold;">TOTAL CONSOLIDATED BALANCE</p>
            <h1 style="margin:0; color:#2B3F87;">{grand_outstanding:,.0f} <span style="font-size:18px;">UGX</span></h1>
            <p style="margin:0; font-size:11px; color:#4A90E2;">Active Accounts: {len(client_loans)}</p>
        </div>
    """, unsafe_allow_html=True)

    # 5. GENERATE THE VISUAL TABLES FOR EACH LOAN
    html_sections = ""
    for _, l_row in client_loans.iterrows():
        l_id = str(l_row['Loan_ID']).replace(".0", "")
        l_ledger = []
        
        # --- THE TREND MATH (Principal Recovery) ---
        curr_p = float(l_row.get('Principal', 0))
        curr_i = float(l_row.get('Interest', 0))
        rate = float(l_row.get('Interest_Rate', 0))
        
        # Determine the "Opening" state
        if "Rolled" in str(l_row.get('Status', '')):
            old_p = curr_p / (1 + (rate/100)) if rate > 0 else curr_p
            interest_added = curr_p - old_p
            l_ledger.append({"Date": "Prev Month", "Description": "Balance Brought Forward", "Debit": old_p, "Credit": 0, "Balance": old_p})
            l_ledger.append({"Date": l_row.get('Rollover_Date', '-'), "Description": f"🔄 Monthly Rollover ({rate}% Int.)", "Debit": interest_added, "Credit": 0, "Balance": curr_p})
        else:
            l_ledger.append({"Date": l_row.get('Start_Date', '-'), "Description": "Loan Disbursement", "Debit": curr_p, "Credit": 0, "Balance": curr_p})
            if curr_i > 0:
                l_ledger.append({"Date": l_row.get('Start_Date', '-'), "Description": "Initial Interest Charged", "Debit": curr_i, "Credit": 0, "Balance": curr_p + curr_i})

        # FETCH PAYMENTS FOR THIS SPECIFIC LOAN
        if not payments_df.empty:
            rel_pay = payments_df[payments_df["Loan_ID"].astype(str).str.replace(".0","") == l_id].sort_values("Date")
            running_bal = l_ledger[-1]["Balance"]
            for _, p in rel_pay.iterrows():
                p_amt = float(p.get("Amount", 0))
                running_bal -= p_amt
                l_ledger.append({
                    "Date": p.get("Date", "-"),
                    "Description": f"✅ Repayment ({p.get('Method', 'Cash')})",
                    "Debit": 0, "Credit": p_amt, "Balance": running_bal
                })

        # Build individual table for Screen Preview
        st.markdown(f"#### 🏷️ Loan ID: {l_id} ({l_row.get('Type', 'Personal')})")
        st.table(pd.DataFrame(l_ledger).style.format({"Debit": "{:,.0f}", "Credit": "{:,.0f}", "Balance": "{:,.0f}"}))

        # PREP HTML FOR THE PDF (Styled Consolidation)
        rows_html = ""
        for item in l_ledger:
            rows_html += f"<tr><td>{item['Date']}</td><td>{item['Description']}</td><td align='right'>{item['Debit']:,.0f}</td><td align='right'>{item['Credit']:,.0f}</td><td align='right'><b>{item['Balance']:,.0f}</b></td></tr>"
        
        html_sections += f"""
            <div style="margin-top:20px; padding:10px; background:#F0F8FF; border-radius:5px; font-weight:bold; color:#2B3F87;">
                LOAN REFERENCE: #{l_id} | Status: {l_row['Status']}
            </div>
            <table width="100%" border="1" cellpadding="5" style="border-collapse:collapse; font-size:12px; margin-bottom:20px;">
                <tr style="background:#4A90E2; color:white;"><th>Date</th><th>Description</th><th>Debit</th><th>Credit</th><th>Balance</th></tr>
                {rows_html}
            </table>
        """

    # 6. CONSOLIDATED PRINT TRIGGER
    st.divider()
    if st.button("📥 Download Full Consolidated Statement (PDF)", use_container_width=True):
        b_info = borrowers_df[borrowers_df["Name"] == selected_client].iloc[0] if not borrowers_df.empty else {}
        
        full_html = f"""
        <html><head><style>body {{ font-family: sans-serif; }} th {{ background: #2B3F87; color: white; }}</style></head>
        <body>
            <div style="text-align:center; border-bottom:3px solid #2B3F87;">
                <h1 style="color:#2B3F87; margin:0;">ZOE CONSULTS SMC LTD</h1>
                <p>Consolidated Statement of Accounts</p>
            </div>
            <div style="margin:20px 0;">
                <p><b>Client:</b> {selected_client} <br>
                <b>NIN:</b> {b_info.get('National_ID', '-')} | <b>Phone:</b> {b_info.get('Phone', '-')} <br>
                <b>Generated:</b> {datetime.now().strftime('%d %b %Y %H:%M')}</p>
            </div>
            {html_sections}
            <div style="margin-top:30px; padding:20px; border:2px solid #2B3F87; text-align:right; background:#f9f9f9;">
                <h3 style="margin:0; color:#2B3F87;">GRAND TOTAL OUTSTANDING</h3>
                <h1 style="margin:0; color:#FF4B4B;">{grand_outstanding:,.0f} UGX</h1>
            </div>
        </body></html>
        """
        st.components.v1.html(full_html + "<script>window.print();</script>", height=0)
        st.success("Print dialog opened.")
    


# ==============================
# 23. SYSTEM SETTINGS (Admin Only)
# ==============================

def show_settings():
    # 1. Access Control (Restored Admin-only check)
    if st.session_state.get("role") != "Admin":
        st.error("🔒 Access Denied: System Settings are restricted to Administrators.")
        return

    st.markdown("<h2 style='color: #2B3F87;'>⚙️ System Settings</h2>", unsafe_allow_html=True)

    # ==============================
    # SECTION 1: BUSINESS BRANDING
    # ==============================
    st.subheader("🖼️ Business Branding")
    
    # Use our cached get_logo for performance
    current_logo = get_logo()
    
    col_logo, col_upload = st.columns([1, 2])
    
    with col_logo:
        if current_logo:
            st.image(f"data:image/png;base64,{current_logo}", width=120)
            st.caption("Currently Active Logo")
        else:
            st.info("No logo currently set.")

    with col_upload:
        uploaded_logo = st.file_uploader("Upload New Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if st.button("🚀 Apply New Branding", use_container_width=True):
            if uploaded_logo:
                # Use our optimized save_logo_to_sheet logic
                if save_logo_to_sheet(uploaded_logo):
                    st.success("Branding updated successfully! ✅")
                    st.rerun()
            else:
                st.warning("Please select a file before applying.")

    st.markdown("---")

    # ==============================
    # SECTION 2: REGIONAL DEFAULTS
    # ==============================
    # Fetch settings from sheet to pre-fill
    settings_df = get_cached_data("Settings")
    
    def get_setting_val(key, default):
        if not settings_df.empty and key in settings_df["Key"].values:
            return settings_df[settings_df["Key"] == key].iloc[0]["Value"]
        return default

    st.subheader("🛠️ Regional & Loan Defaults")
    c1, c2 = st.columns(2)
    
    biz_name = c1.text_input("Business Name", value=get_setting_val("biz_name", "Zoe Consults"))
    currency = c2.selectbox("System Currency", ["UGX", "USD", "KES"], index=0)
    
    # Restored the slider for default interest rates
    try: 
        def_int_val = int(get_setting_val("def_interest", 15))
    except: 
        def_int_val = 15
        
    def_interest = st.slider("Default Interest Rate (%)", 1, 50, def_int_val)

    if st.button("💾 Save Global Configuration", use_container_width=True):
        # Package settings for update
        new_settings = pd.DataFrame([
            {"Key": "biz_name", "Value": biz_name},
            {"Key": "currency", "Value": currency},
            {"Key": "def_interest", "Value": str(def_interest)},
            {"Key": "logo", "Value": current_logo} # Preserve existing logo if not changed
        ])
        
        if save_data("Settings", new_settings):
            st.success("Global configurations updated! ✅")
            st.rerun()

    st.markdown("---")

    # ==============================
    # SECTION 3: SYSTEM MAINTENANCE
    # ==============================
    st.subheader("⚠️ System Maintenance")
    st.write("Use these tools if the dashboard shows old data or if the system feels 'stuck'.")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Essential for force-refreshing Google Sheets data
        if st.button("🧹 Clear App Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache wiped. Re-syncing with Google Sheets...")
            st.rerun()
            
    with col_b:
        # Emergency Log out for all sessions
        if st.button("🚪 Hard Reset Session", use_container_width=True):
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





