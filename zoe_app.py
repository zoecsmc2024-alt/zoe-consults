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

# ==============================
# 1. SYSTEM CONFIGURATION
# ==============================
st.set_page_config(page_title="Zoe Fintech", layout="wide")

# Custom CSS Styling
st.markdown("""
<style>
    body { background-color: #0B0F19; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0B0F19, #111827); }
    h1, h2, h3 { color: #E5E7EB; }
    .metric-card {
        background: linear-gradient(135deg, #1E3A8A, #2563EB);
        padding: 18px;
        border-radius: 12px;
        color: white;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
    }
    .stButton>button {
        background: linear-gradient(135deg, #2563EB, #1E40AF);
        color: white;
        border-radius: 10px;
        border: none;
        height: 42px;
        font-weight: 600;
    }
    [data-testid="stDialog"] { border-radius: 12px; padding: 20px; }
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
    # 1. Get the role and user safely
    # If they don't exist yet, we use "Guest" as a backup
    role = st.session_state.get("role", "Staff")
    current_user = st.session_state.get("user", "Guest")

    st.sidebar.markdown("## ZOE ADMIN 💼")
    
    # 2. Use the safe variable we just created
    st.sidebar.markdown(f"👤 {current_user} ({role})")
    st.sidebar.markdown("---")

    # ... (rest of your sidebar menu code)

    menu = {
        "Overview": "📊", "Borrowers": "👥", "Collateral": "🛡️",
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
            st.sidebar.markdown(f'<div style="background:#2B3F87;padding:10px;border-radius:8px;color:white;">{icon} {item}</div>', unsafe_allow_html=True)
        else:
            if st.sidebar.button(f"{icon} {item}"):
                st.session_state.page = item
                st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

sidebar()
st.markdown(f"### Welcome {st.session_state.user} 👋")

# ==============================
# 6. PAGE ROUTING & CONTENT
# ==============================

# --- OVERVIEW PAGE ---
if st.session_state.page == "Overview":
    st.title("📊 Financial Dashboard")
    df = load_data(sheet, "Loans")

    if df.empty:
        st.warning("No data available")
    else:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        df["Interest"] = pd.to_numeric(df["Interest"], errors="coerce")
        df["Amount_Paid"] = pd.to_numeric(df.get("Amount_Paid", 0), errors="coerce")
        df["Start_Date"] = pd.to_datetime(df["Start_Date"], errors="coerce")
        df["End_Date"] = pd.to_datetime(df["End_Date"], errors="coerce")
        
        today = pd.Timestamp.today()
        df["Auto_Status"] = df["Status"]
        df.loc[(df["End_Date"] < today) & (df["Amount_Paid"] < (df["Amount"] + df["Interest"])), "Auto_Status"] = "Overdue"

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Issued", f"{df['Amount'].sum():,.0f}")
        col2.metric("📈 Expected Profit", f"{df['Interest'].sum():,.0f}")
        col3.metric("💵 Collected", f"{df['Amount_Paid'].sum():,.0f}")
        col4.metric("⚠️ Overdue Loans", len(df[df["Auto_Status"] == "Overdue"]))

        st.plotly_chart(px.pie(df, names="Auto_Status", title="Loan Status Distribution"), use_container_width=True)

# --- BORROWERS PAGE ---
elif st.session_state.page == "Borrowers":
    st.title("👥 Borrowers Management")
    df = load_data(sheet, "Borrowers")

    with st.form("add_borrower"):
        st.subheader("➕ Add Borrower")
        name = st.text_input("Full Name")
        phone = st.text_input("Phone Number")
        nid = st.text_input("National ID")
        addr = st.text_input("Address")
        if st.form_submit_button("Add"):
            new_id = int(df["Borrower_ID"].max() + 1) if not df.empty else 1
            new_row = pd.DataFrame([{"Borrower_ID": new_id, "Name": name, "Phone": phone, "National_ID": nid, "Address": addr, "Status": "Active", "Date_Added": datetime.now().strftime("%Y-%m-%d")}])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(sheet, "Borrowers", df)
            st.success("Added!")

    st.dataframe(df, use_container_width=True)

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
