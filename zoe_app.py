import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import base64
import urllib.parse

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
<style>
    /* 1. THE ULTIMATE TOP RESET */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        margin-top: 0rem !important;
    }

    /* 2. REMOVE THE HEADER GAP */
    header {
        visibility: hidden;
        height: 0% !important;
    }

    /* 3. THE MAIN VIEWPORT */
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
    }

    /* 4. FIX TITLE POSITION */
    .main-title {
        color: #0f172a !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        margin-top: -20px !important;
        margin-bottom: 20px !important;
        letter-spacing: -1px;
    }
</style>
""", unsafe_allow_html=True)
# --- 2. PERMANENT DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Fetching both tables from Google Sheets
    borrowers = conn.read(worksheet="Borrowers", ttl="0")
    payments = conn.read(worksheet="Payments", ttl="0")
    return borrowers.dropna(how="all"), payments.dropna(how="all")

df, pay_df = get_data()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown('<div style="margin-top: -30px;"></div>', unsafe_allow_html=True)
    
    # Logo Logic
    if 'custom_logo_b64' in st.session_state and st.session_state['custom_logo_b64']:
        st.markdown(f'<img src="data:image/png;base64,{st.session_state["custom_logo_b64"]}">', unsafe_allow_html=True)
    else:
        st.markdown('<div style="width:80px;height:80px;border-radius:50%;background-color:#1e293b;border:2px solid #00a8b5;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:30px;">💰</div>', unsafe_allow_html=True)
    
    st.markdown(f'<p class="admin-text"><b>Admin:</b> Evans Ahuura</p>', unsafe_allow_html=True)
    
    page = st.radio("Menu", ["📊 Overview", "👥 Borrowers", "💰 Repayments", "📅 Calendar", "📑 Collateral", "📄 Client Ledger", "⚙️ Settings"])
    
    st.write("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# --- 4. PAGE LOGIC ---

if page == "📊 Overview":
    # 1. The Title (Already working, keep this!)
    st.markdown('<div class="main-title">🛡️ Zoe Consults Executive Summary</div>', unsafe_allow_html=True)
    
    # 2. Add some "Air" (Spacing)
    st.write("") 

    if not df.empty:
        # Calculate the money
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        balance = total_p - total_c
        
        # 3. PREMIUM KPI CARDS (Styled to look like Glass)
        c1, c2, c3 = st.columns(3)
        
        card_style = """
            background: #ffffff;
            padding: 25px;
            border-radius: 15px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
            text-align: center;
        """

        with c1:
            st.markdown(f'''<div style="{card_style} border-top: 5px solid #0ea5e9;">
                <p style="color: #64748b; font-size: 0.9rem; font-weight: 600; margin:0;">TOTAL CAPITAL ISSUED</p>
                <h1 style="color: #0f172a; margin: 10px 0; font-size: 2rem;">UGX {total_p:,.0f}</h1>
            </div>''', unsafe_allow_html=True)
            
        with c2:
            st.markdown(f'''<div style="{card_style} border-top: 5px solid #10b981;">
                <p style="color: #64748b; font-size: 0.9rem; font-weight: 600; margin:0;">TOTAL RECOVERED</p>
                <h1 style="color: #10b981; margin: 10px 0; font-size: 2rem;">UGX {total_c:,.0f}</h1>
            </div>''', unsafe_allow_html=True)
            
        with c3:
            st.markdown(f'''<div style="{card_style} border-top: 5px solid #ef4444;">
                <p style="color: #64748b; font-size: 0.9rem; font-weight: 600; margin:0;">OUTSTANDING RISK</p>
                <h1 style="color: #ef4444; margin: 10px 0; font-size: 2rem;">UGX {balance:,.0f}</h1>
            </div>''', unsafe_allow_html=True)

        st.write("---")
        
        # 4. RECOVERY PROGRESS CHART
        st.subheader("📈 Recovery Progress by Client")
        st.bar_chart(df.set_index('CUSTOMER_NAME')[['LOAN_AMOUNT', 'AMOUNT_PAID']], color=["#0ea5e9", "#10b981"])

    else:
        st.info("👋 Welcome, Admin! Add your first loan to see the magic happen.")
        
       # --- 4. THE PRO RECOVERY CHART ---
st.markdown('<h3 style="color: #0f172a; margin-top: 30px;">📈 Recovery Progress</h3>', unsafe_allow_html=True)

# This adds a nice background and rounded corners to the chart area
with st.container():
    st.bar_chart(
        df.set_index('CUSTOMER_NAME')[['LOAN_AMOUNT', 'AMOUNT_PAID']], 
        color=["#0ea5e9", "#10b981"], # Teal for Principal, Green for Recovered
        use_container_width=True
    )
    st.caption("🔵 Principal Issued (Investment) vs 🟢 Total Collected (Recovery)")
    
    # 2. THE WHITE WRAPPER END
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.popover("➕ New Loan"):
        with st.form("new_loan"):
            name = st.text_input("Client Name")
            amt = st.number_input("Principal Amount", min_value=0)
            rate = st.number_input("Interest Rate (%)", value=10.0)
            if st.form_submit_button("✅ Save to Cloud"):
                new_id = int(df['SN'].max() + 1) if not df.empty else 1
                new_row = pd.DataFrame([[new_id, name, amt, 0, amt, rate, str(datetime.now().date())]], columns=df.columns)
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Borrowers", data=updated_df)
                st.success("Saved to Google Sheets!")
                st.rerun()

elif page == "💰 Repayments":
    st.markdown('<div class="main-title">💰 Record a Payment</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # We wrap the form in a nice white container
        with st.container():
            with st.form("repayment_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
                    p_amt = st.number_input("Amount Received (UGX)", min_value=0, step=1000)
                with col2:
                    p_ref = st.text_input("Receipt / Reference Number")
                    p_date = st.date_input("Date of Payment", datetime.now())
                
                if st.form_submit_button("✅ Log Payment", use_container_width=True):
                    # 1. Update Payments Worksheet
                    new_p = pd.DataFrame([[str(p_date), p_name, p_amt, p_ref]], 
                                       columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                    updated_pay = pd.concat([pay_df, new_p], ignore_index=True)
                    conn.update(worksheet="Payments", data=updated_pay)
                    
                    # 2. Update Borrowers Worksheet (Reducing the balance)
                    df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                    df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amt
                    conn.update(worksheet="Borrowers", data=df)
                    
                    st.success(f"Success! UGX {p_amt:,} recorded for {p_name}.")
                    st.rerun()
    else:
        st.warning("⚠️ No active borrowers found. Please add a loan first.")

elif page == "📅 Calendar":
    st.title("📅 Calendar Schedule")
    if not df.empty:
        df['DUE_DATE'] = pd.to_datetime(df['DATE_ISSUED']) + pd.Timedelta(days=30)
        df['DAYS_LEFT'] = (df['DUE_DATE'] - pd.Timestamp(datetime.now().date())).dt.days
        st.dataframe(df[df['OUTSTANDING_AMOUNT'] > 0][['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT', 'DUE_DATE', 'DAYS_LEFT']], use_container_width=True)

elif page == "📄 Client Ledger":
    st.title("📄 Individual Client Ledger")
    if not df.empty:
        target = st.selectbox("Select Client", options=df['CUSTOMER_NAME'].unique())
        client_history = pay_df[pay_df['CUSTOMER_NAME'] == target]
        st.subheader(f"Payment History: {target}")
        st.dataframe(client_history, use_container_width=True)
        
        # WhatsApp Integration
        bal = df[df['CUSTOMER_NAME'] == target]['OUTSTANDING_AMOUNT'].values[0]
        msg = urllib.parse.quote(f"Zoe Consults: Hello {target}, your current balance is UGX {bal:,.0f}.")
        st.link_button(f"📲 Send WhatsApp to {target}", f"https://wa.me/?text={msg}")

elif page == "⚙️ Settings":
    st.title("⚙️ Branding & Settings")
    logo_file = st.file_uploader("Upload Sidebar Logo", type=["png", "jpg"])
    if logo_file:
        st.session_state['custom_logo_b64'] = base64.b64encode(logo_file.getvalue()).decode()
        st.rerun()
    if st.button("Reset Logo"):
        st.session_state['custom_logo_b64'] = None
        st.rerun()
