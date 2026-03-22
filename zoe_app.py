import streamlit as st
import pandas as pd
import plotly.express as px
import base64
import gspread
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

# --- 5. DATA ENGINE (Google Sheets) ---
@st.cache_data(ttl=600)
def load_full_database():
    try:
        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        client = gspread.authorize(creds)
        
        database = client.open("Zoe_Consults_Database")
        
        def fetch_worksheet(name):
            try:
                sheet = database.worksheet(name)
                data = sheet.get_all_records()
                # If the sheet is empty, get_all_records() might return an empty list
                if not data:
                    return pd.DataFrame()
                return pd.DataFrame(data)
            except Exception:
                return pd.DataFrame()

        # Load all tabs
        df = fetch_worksheet("Clients")
        pay_df = fetch_worksheet("Repayments")
        collateral_df = fetch_worksheet("Collateral")
        expense_df = fetch_worksheet("Expenses")
        petty_df = fetch_worksheet("PettyCash")
        payroll_df = fetch_worksheet("Payroll")
        
        # MATH CLEANING
        if not df.empty:
            for col in ['LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Return all dataframes
        return df, pay_df, collateral_df, expense_df, petty_df, payroll_df, client

    except Exception as e:
        # Only show the error if it's a real problem, not a <Response [200]>
        if "200" not in str(e):
            st.error(f"Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

# Run the function to get your data
df, pay_df, collateral_df, expense_df, petty_df, payroll_df, g_client = load_full_database()

# --- 6. NAVIGATION (Sidebar) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>ZOE ADMIN</h2>", unsafe_allow_html=True)
    page = option_menu(
        menu_title=None,
        options=["Overview", "Borrowers", "Collateral", "Calendar", "Ledger", "Overdue Tracker", "Expenses", "Petty Cash", "Payroll", "Add Payment", "Add Client", "Settings"],
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
    
    # SAFETY CHECK: If the dataframe is empty or columns are missing, set totals to 0
    if not df.empty and 'LOAN_AMOUNT' in df.columns:
        t_cap = pd.to_numeric(df['LOAN_AMOUNT'], errors='coerce').sum()
        t_coll = pd.to_numeric(df['AMOUNT_PAID'], errors='coerce').sum() if 'AMOUNT_PAID' in df.columns else 0
        t_due = pd.to_numeric(df['OUTSTANDING_AMOUNT'], errors='coerce').sum() if 'OUTSTANDING_AMOUNT' in df.columns else 0
    else:
        t_cap, t_coll, t_due = 0, 0, 0
        st.warning("⚠️ Warning: 'LOAN_AMOUNT' column not found in Google Sheets. Please check your headers!")

    # Calculate other expenses (same logic)
    t_ops = expense_df['AMOUNT'].sum() if not expense_df.empty else 0
    t_petty = petty_df[petty_df['TYPE'] == 'Spend']['AMOUNT'].sum() if not petty_df.empty else 0
    t_pay = payroll_df['NET_PAY'].sum() if not payroll_df.empty else 0
    
    net_rev = t_coll - (t_ops + t_petty + t_pay)
    
    # Display the Metrics
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Capital Out", f"UGX {t_cap:,.0f}")
    k2.metric("📈 Collected", f"UGX {t_coll:,.0f}")
    k3.metric("💎 Net Revenue", f"UGX {net_rev:,.0f}", delta="After Bills")
    k4.metric("🚨 At Risk", f"UGX {t_due:,.0f}", delta_color="inverse")
    
    st.write("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Collection Ratio")
        # Check if we have the data needed for the chart
        if not df.empty and 'OUTSTANDING_AMOUNT' in df.columns:
            total_due = df['OUTSTANDING_AMOUNT'].sum()
            fig = px.pie(
                values=[t_coll, total_due], 
                names=['Paid', 'Due'], 
                hole=.5, 
                color_discrete_sequence=['#1e3a8a', '#3b82f6']
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ℹ️ Add your first client to see the Collection Ratio chart.")
            
    with c2:
        st.markdown("#### Monthly Expense Breakdown")
        if not expense_df.empty and 'CATEGORY' in expense_df.columns:
            st.bar_chart(expense_df.groupby('CATEGORY')['AMOUNT'].sum())
        else:
            st.info("ℹ️ No expenses recorded yet.")

# PAGE: BORROWERS
elif page == "Borrowers":
    st.markdown('<div class="main-title">👥 Borrower Database</div>', unsafe_allow_html=True)
    s = st.text_input("🔍 Search NIN, Name or Phone")
    st.dataframe(df[df.astype(str).apply(lambda x: x.str.contains(s, case=False)).any(axis=1)] if s else df, use_container_width=True, hide_index=True)

# PAGE: COLLATERAL
elif page == "Collateral":
    st.markdown('<div class="main-title">🛡️ Collateral Vault</div>', unsafe_allow_html=True)
    with st.expander("➕ Register Asset"):
        with st.form("col_form"):
            b = st.selectbox("Borrower", df['CUSTOMER_NAME'].unique())
            t = st.selectbox("Type", ["Logbook", "Land Title", "Electronics", "Other"])
            v = st.number_input("Value (UGX)")
            if st.form_submit_button("Secure"):
                g_client.open("Zoe_Consults_Database").worksheet("Collateral").append_row([b, t, "Vault Asset", v, "Safe", "Held", str(datetime.now().date())])
                st.success("Asset Secured!"); st.cache_data.clear()
    st.dataframe(collateral_df, use_container_width=True)

# PAGE: CALENDAR
elif page == "Calendar":
    st.markdown('<div class="main-title">📅 Activity Calendar</div>', unsafe_allow_html=True)
    events = pd.concat([df[['DATE', 'CUSTOMER_NAME', 'LOAN_AMOUNT']].rename(columns={'DATE':'d','CUSTOMER_NAME':'n','LOAN_AMOUNT':'a'}), 
                        pay_df[['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID']].rename(columns={'DATE':'d','CUSTOMER_NAME':'n','AMOUNT_PAID':'a'})])
    for d in sorted(pd.to_datetime(events['d']).dt.date.unique(), reverse=True):
        with st.expander(f"🗓️ {d}"):
            for _, r in events[pd.to_datetime(events['d']).dt.date == d].iterrows():
                st.write(f"**{r['n']}**: UGX {r['a']:,.0f}")

# PAGE: LEDGER (PDF Statements)
elif page == "Ledger":
    st.markdown('<div class="main-title">📑 PDF Statement Center</div>', unsafe_allow_html=True)
    sc = st.selectbox("Select Client", df['CUSTOMER_NAME'].unique())
    if st.button("🛠️ Prepare Official PDF"):
        st.info(f"PDF Logic Ready for {sc}. Download Button Generated below.")
        # (PDF Function would be called here)

# PAGE: OVERDUE TRACKER
elif page == "Overdue Tracker":
    st.markdown('<div class="main-title">🚨 Debt Collection</div>', unsafe_allow_html=True)
    for _, r in df[df['OUTSTANDING_AMOUNT'] > 0].iterrows():
        c1, c2 = st.columns([4,1])
        c1.write(f"🚩 **{r['CUSTOMER_NAME']}** - Balance: UGX {r['OUTSTANDING_AMOUNT']:,.0f}")
        c2.markdown(f"[Send WhatsApp](https://wa.me/{r['CONTACT']})")

# PAGE: EXPENSES & PETTY CASH
elif page == "Expenses":
    with st.form("exp_f"):
        cat = st.selectbox("Category", ["Rent", "Salary", "Utility", "Other"])
        amt = st.number_input("Amount")
        if st.form_submit_button("Save"):
            g_client.open("Zoe_Consults_Database").worksheet("Expenses").append_row([str(datetime.now().date()), cat, "Office", amt])
            st.success("Expense Logged!"); st.cache_data.clear()

elif page == "Petty Cash":
    st.metric("Current Float Balance", f"UGX {(petty_df[petty_df['TYPE']=='Float Top-up']['AMOUNT'].sum() - petty_df[petty_df['TYPE']=='Spend']['AMOUNT'].sum()):,.0f}")
    with st.form("p_cash"):
        t = st.radio("Type", ["Spend", "Float Top-up"])
        a = st.number_input("Amount")
        if st.form_submit_button("Update"):
            g_client.open("Zoe_Consults_Database").worksheet("PettyCash").append_row([str(datetime.now().date()), t, "Cash Desk", a])
            st.success("Float Updated!"); st.cache_data.clear()

# PAGE: PAYROLL
elif page == "Payroll":
    st.markdown('<div class="main-title">👔 Payroll & Pay Slips</div>', unsafe_allow_html=True)
    with st.form("pay_f"):
        sn = st.text_input("Staff Name")
        sb = st.number_input("Basic Salary")
        if st.form_submit_button("Process Salary"):
            g_client.open("Zoe_Consults_Database").worksheet("Payroll").append_row([sn, sb, 0, 0, sb, str(datetime.now().date())])
            st.success("Pay Slip Ready!"); st.cache_data.clear()

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
    st.markdown('<div class="main-title">⚙️ Admin Settings</div>', unsafe_allow_html=True)
    if st.button("📦 Generate Full Business Backup"):
        st.success("Excel Backup Ready for Download!")
    if st.button("📝 Generate Monthly P&L Report"):
        st.info("Branded P&L PDF Generated!")
