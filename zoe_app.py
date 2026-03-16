import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. SETTINGS & THEMING ---
LOGO_URL = "logo.jpg" 
st.set_page_config(page_title="ZoeLend IQ Pro", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { 
        color: #ffffff !important; opacity: 1 !important;
    }
    th { background-color: #00acee !important; color: white !important; text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINES ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'])
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
            # Force SN to be string to prevent leading zero issues
            df['SN'] = df['SN'].astype(str).str.strip()
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['SN','OFFER_NO','NAME','CONTACT','DATE_OF_ISSUE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS','DURATION_MONTHS','Last_Payment_Date'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def get_loan_status(last_payment_date):
    days = (datetime.datetime.now() - pd.to_datetime(last_payment_date)).days
    if days <= 30: return "Active"
    elif 31 <= days <= 60: return "Risky"
    else: return "Dormant"

# --- 3. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
    st.stop()

df = load_data()
if not df.empty:
    df['STATUS'] = df['Last_Payment_Date'].apply(get_loan_status)

# --- 4. SIDEBAR ---
with st.sidebar:
    if os.path.exists(LOGO_URL): st.image(LOGO_URL, width=120)
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Portfolio Registry")
    if df.empty: st.info("Registry is empty.")
    else:
        def style_rows(res):
            return ['background-color: #f1f5f9' if i % 2 == 0 else 'background-color: #ffffff' for i in range(len(res))]

        def color_status(val):
            if val == 'Active': color = '#10b981'
            elif val == 'Risky': color = '#f59e0b'
            else: color = '#ef4444'
            return f'color: {color}; font-weight: bold'

        display_cols = ['SN', 'OFFER_NO', 'NAME', 'DATE_OF_ISSUE', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']
        temp_df = df[display_cols].copy()
        temp_df['DATE_OF_ISSUE'] = temp_df['DATE_OF_ISSUE'].dt.strftime('%d-%b-%Y')

        st.table(temp_df.style.apply(style_rows, axis=0).applymap(color_status, subset=['STATUS']).format({"LOAN_AMOUNT": "{:,.0f}", "OUTSTANDING_AMOUNT": "{:,.0f}"}))
        
        st.markdown("---")
        # 🛠️ EDIT CLIENT INFO ACTION
        with st.expander("🛠️ Edit Client Information (Fix Errors)"):
            edit_sn = st.text_input("Enter SN to Edit (e.g. 00001)").strip()
            if edit_sn in df['SN'].values:
                idx = df[df['SN'] == edit_sn].index[0]
                with st.form("edit_form"):
                    st.write(f"Editing Record for: **{df.at[idx, 'NAME']}**")
                    new_name = st.text_input("Full Name", value=df.at[idx, 'NAME'])
                    new_contact = st.text_input("Contact Number", value=df.at[idx, 'CONTACT'])
                    new_amt = st.number_input("Loan Amount (UGX)", value=float(df.at[idx, 'LOAN_AMOUNT']))
                    
                    if st.form_submit_button("💾 Save Changes"):
                        df.at[idx, 'NAME'] = new_name
                        df.at[idx, 'CONTACT'] = new_contact
                        df.at[idx, 'LOAN_AMOUNT'] = new_amt
                        # Recalculate Outstanding if Amount changed
                        rate = float(df.at[idx, 'INTEREST_RATE'])
                        dur = int(df.at[idx, 'DURATION_MONTHS'])
                        df.at[idx, 'OUTSTANDING_AMOUNT'] = new_amt + (new_amt * (rate/100) * dur) - float(df.at[idx, 'AMOUNT_PAID'])
                        
                        save_data(df)
                        st.success("Information updated successfully!")
                        st.rerun()
            elif edit_sn != "":
                st.error("SN not found.")

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Issue")
    with st.form("new_loan"):
        c1, c2 = st.columns(2)
        with c1:
            sn = st.text_input("SN", value=f"{len(df)+1:05d}")
            off_no = st.text_input("OFFER NO")
            name = st.text_input("NAME")
        with c2:
            contact = st.text_input("CONTACT")
            doi = st.date_input("DATE OF ISSUE")
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("MONTHLY RATE (%)", value=3)
            dur = st.number_input("DURATION (MONTHS)", min_value=1, value=6)
        
        if st.form_submit_button("✅ Save & Disburse"):
            to_pay = amt + (amt * (rate/100) * dur)
            new_row = pd.DataFrame([{'SN': str(sn).strip(), 'OFFER_NO': off_no, 'NAME': name, 'CONTACT': contact, 'DATE_OF_ISSUE': doi, 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': to_pay, 'STATUS': 'Active', 'DURATION_MONTHS': dur, 'Last_Payment_Date': doi}])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Recorded!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        cid = st.text_input("Enter SN (e.g. 00001)").strip()
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Submit"):
            idx = df[df['SN'] == cid].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
                save_data(df); st.success("Updated!"); st.rerun()
            else: st.error("SN not found.")

elif choice == "📄 Client Report":
    st.title("📄 Client Statement & Schedule")
    if not df.empty:
        # Create a search list that shows both Name and SN for clarity
        client_options = df.apply(lambda x: f"{x['NAME']} (SN: {x['SN']})", axis=1).tolist()
        selected_option = st.selectbox("Select Client", client_options)
        
        # Extract the SN from the selection to find the right data
        selected_sn = selected_option.split("(SN: ")[1].replace(")", "")
        c = df[df['SN'] == selected_sn].iloc[0]
        
        st.markdown(f"""
        <div style="padding:30px; border:1px solid #e2e8f0; border-radius:10px; background-color: white; color: black;">
            <h2 style="text-align:center; color: #1e293b;">ZOE CONSULTS LIMITED</h2>
            <p style="text-align:center; border-bottom: 2px solid #00acee; padding-bottom:10px;">OFFICIAL LOAN STATEMENT</p>
            
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <p><b>Client Name:</b> {c['NAME']}</p>
                    <p><b>Contact:</b> {c['CONTACT']}</p>
                    <p><b>Status:</b> <span style="color: {'#10b981' if c['STATUS'] == 'Active' else '#ef4444'}; font-weight: bold;">{c['STATUS']}</span></p>
                </div>
                <div style="text-align: right;">
                    <p><b>SN:</b> {c['SN']}</p>
                    <p><b>Issue Date:</b> {pd.to_datetime(c['DATE_OF_ISSUE']).strftime('%d-%b-%Y')}</p>
                    <p><b>Offer No:</b> {c['OFFER_NO']}</p>
                </div>
            </div>
            
            <hr style="border: 0.5px solid #eee;">
            
            <div style="display: flex; justify-content: space-around; background-color: #f8fafc; padding: 15px; border-radius: 5px;">
                <div style="text-align: center;">
                    <small>PRINCIPAL</small><br><b>UGX {c['LOAN_AMOUNT']:,.0f}</b>
                </div>
                <div style="text-align: center;">
                    <small>TOTAL PAID</small><br><b style="color: #10b981;">UGX {c['AMOUNT_PAID']:,.0f}</b>
                </div>
                <div style="text-align: center;">
                    <small>OUTSTANDING</small><br><b style="color: #ef4444;">UGX {c['OUTSTANDING_AMOUNT']:,.0f}</b>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📅 Repayment Schedule")
        # Reuse the schedule engine
        try:
            sched = generate_schedule(c['LOAN_AMOUNT'], c['INTEREST_RATE'], c['DURATION_MONTHS'])
            st.table(sched.style.format("{:,.0f}").set_properties(**{'text-align': 'center'}))
        except Exception as e:
            st.warning("Could not generate schedule. Please check if 'Duration' and 'Rate' are set correctly for this client.")
    else:
        st.info("Registry is empty. Onboard a client first.")
