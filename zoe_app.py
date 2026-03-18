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
    /* 1. FORCE THE MAIN BOARD TO WHITE */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #ffffff !important;
    }

    /* 2. FORCE MAIN TEXT TO DARK NAVY (So you can see the titles) */
    h1, h2, h3, p, span, div, label {
        color: #0f172a !important;
    }

    /* 3. KEEP THE SIDEBAR DARK NAVY */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #0b1425 !important;
        border-right: 3px solid #00a8b5 !important;
    }

    /* 4. FORCE SIDEBAR TEXT TO STAY WHITE */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
    }

    /* 5. STYLE THE KPI TILES FOR THE WHITE BACKGROUND */
    .metric-card {
        background-color: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 15px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
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
    # 1. THE WHITE WRAPPER START
    st.markdown('<div style="background-color: white; padding: 30px; border-radius: 15px; min-height: 100vh;">', unsafe_allow_html=True)
    
    st.markdown('<h1 style="color: #0f172a; margin-top: 0;">🛡️ Zoe Consults Executive Summary</h1>', unsafe_allow_html=True)
    
    if not df.empty:
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        balance = total_p - total_c
        
        # --- TILES IN THE WRAPPER ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f'''<div class="metric-card" style="background-color: #f1f5f9;">
                <p style="color: #475569; font-size: 0.8rem; margin:0;">TOTAL CAPITAL ISSUED</p>
                <h2 style="color: #0f172a; margin:0;">UGX {total_p:,.0f}</h2>
            </div>''', unsafe_allow_html=True)
            
        with c2:
            st.markdown(f'''<div class="metric-card" style="background-color: #f1f5f9;">
                <p style="color: #475569; font-size: 0.8rem; margin:0;">TOTAL RECOVERED</p>
                <h2 style="color: #10b981; margin:0;">UGX {total_c:,.0f}</h2>
            </div>''', unsafe_allow_html=True)
            
        with c3:
            st.markdown(f'''<div class="metric-card" style="background-color: #f1f5f9;">
                <p style="color: #475569; font-size: 0.8rem; margin:0;">OUTSTANDING RISK</p>
                <h2 style="color: #ef4444; margin:0;">UGX {balance:,.0f}</h2>
            </div>''', unsafe_allow_html=True)

        st.markdown('<hr style="border-top: 1px solid #e2e8f0;">', unsafe_allow_html=True)
        
        # --- THE CHART ---
        st.markdown('<h3 style="color: #0f172a;">📈 Recovery Progress</h3>', unsafe_allow_html=True)
        st.bar_chart(df.set_index('CUSTOMER_NAME')[['LOAN_AMOUNT', 'AMOUNT_PAID']], color=["#0ea5e9", "#10b981"])
    
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
    st.title("💰 Record a Payment")
    if not df.empty:
        with st.form("pay_form"):
            p_name = st.selectbox("Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount (UGX)", min_value=0)
            p_ref = st.text_input("Receipt No.")
            if st.form_submit_button("Submit"):
                # 1. Update Payments Sheet
                new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                updated_pay = pd.concat([pay_df, new_p], ignore_index=True)
                conn.update(worksheet="Payments", data=updated_pay)
                
                # 2. Update Borrowers Sheet Balance
                df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amt
                conn.update(worksheet="Borrowers", data=df)
                st.rerun()
    st.dataframe(pay_df.iloc[::-1], use_container_width=True)

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
