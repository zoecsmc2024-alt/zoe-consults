import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
LOGO_URL = "logo.jpg" 
st.set_page_config(page_title="ZoeLend IQ Pro", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: white !important; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] .stButton > button { background-color: transparent; color: white !important; border: 2px solid white !important; font-weight: bold; width: 100%; }
    
    /* Professional Report Styling */
    .report-box { 
        background-color: white; 
        padding: 30px; 
        border: 1px solid #e2e8f0; 
        border-radius: 10px;
        font-family: 'Arial', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. ENGINES ---
def load_data():
    if os.path.exists(FILE_NAME):
        try:
            df = pd.read_csv(FILE_NAME)
            df['Start_Date'] = pd.to_datetime(df['Start_Date'])
            df['Last_Payment_Date'] = pd.to_datetime(df['Last_Payment_Date'])
            return df
        except: return create_empty_df()
    return create_empty_df()

def create_empty_df():
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Phone', 'NIN', 'Address', 'Next_of_Kin', 'Employer', 'Principal_UGX', 'Annual_Rate', 'Duration_Months', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def generate_schedule(principal, rate, months):
    # Adjust rate: if boss typed '3', treat as 3.0 (300%). 
    # Usually in financial code, 0.15 = 15%.
    monthly_rate = rate / 12
    if monthly_rate > 0:
        installment = (principal * monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    else: installment = principal / months
    
    data = []
    rem = principal
    for i in range(1, int(months) + 1):
        interest = rem * monthly_rate
        princ_rep = installment - interest
        rem -= princ_rep
        data.append({"Month": i, "Installment": round(installment, 0), "Principal": round(princ_rep, 0), "Interest": round(interest, 0), "Balance": max(0, round(rem, 0))})
    return pd.DataFrame(data)

# --- 3. LOGIN ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "zoe2026":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Denied")
    st.stop()

# --- 4. DATA PROCESSING ---
df = load_data()
with st.sidebar:
    if os.path.exists(LOGO_URL): st.image(LOGO_URL, width=120)
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Client Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if st.button("🔓 LOGOUT"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 5. PAGES ---
if choice == "📊 Daily Report":
    st.title("📊 Financial Portfolio")
    if df.empty: st.info("No data.")
    else:
        # Style logic
        def color_status(val):
            color = '#10b981' if val == 'Active' else '#ef4444'
            return f'color: {color}; font-weight: bold'

        st.table(df[['Customer_ID', 'Name', 'Principal_UGX', 'Status']].style \
            .set_properties(**{'background-color': '#e0f2fe'}, subset=['Customer_ID', 'Name']) \
            .applymap(color_status, subset=['Status']) \
            .format({"Principal_UGX": "UGX {:,.0f}"}))

        with st.expander("🛠️ Edit Client Record"):
            edit_id = st.number_input("ID to Edit", min_value=101)
            if edit_id in df['Customer_ID'].values:
                idx = df[df['Customer_ID'] == edit_id].index[0]
                with st.form("edit"):
                    n_name = st.text_input("Name", value=df.at[idx, 'Name'])
                    n_prin = st.number_input("Principal", value=float(df.at[idx, 'Principal_UGX']))
                    n_rate = st.number_input("Rate (e.g. 0.15 for 15%)", value=float(df.at[idx, 'Annual_Rate']))
                    if st.form_submit_button("Save Changes"):
                        df.at[idx, 'Name'], df.at[idx, 'Principal_UGX'], df.at[idx, 'Annual_Rate'] = n_name, n_prin, n_rate
                        save_data(df); st.success("Updated!"); st.rerun()

elif choice == "👤 Client Onboarding":
    st.title("👤 New Registration")
    with st.form("kyc"):
        c1, c2 = st.columns(2)
        with c1:
            n = st.text_input("Name"); ph = st.text_input("Phone"); ni = st.text_input("NIN")
        with c2:
            ad = st.text_input("Address"); nk = st.text_input("Next of Kin"); em = st.text_input("Employer")
        a = st.number_input("UGX", min_value=1000)
        r = st.number_input("Rate (e.g. 0.15)", value=0.15)
        d = st.number_input("Months", min_value=1, value=6)
        if st.form_submit_button("✅ Register"):
            new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
            new_row = pd.DataFrame([{'Customer_ID': int(new_id), 'Name': n, 'Phone': ph, 'NIN': ni, 'Address': ad, 'Next_of_Kin': nk, 'Employer': em, 'Principal_UGX': float(a), 'Annual_Rate': float(r), 'Duration_Months': int(d), 'Start_Date': datetime.datetime.now(), 'Last_Payment_Date': datetime.datetime.now(), 'Status': 'Active'}])
            save_data(pd.concat([df, new_row], ignore_index=True)); st.success("Added!"); st.balloons()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    cid = st.number_input("Client ID", min_value=101)
    if st.button("Confirm Payment"):
        idx = df[df['Customer_ID'] == cid].index
        if not idx.empty:
            df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
            save_data(df); st.success("Updated!"); st.rerun()

elif choice == "📄 Client Report":
    st.title("📄 Professional Client Statement")
    if not df.empty:
        client = st.selectbox("Select Client", df['Name'].unique())
        c = df[df['Name'] == client].iloc[0]
        
        # BEAUTIFIED REPORT BOX
        st.markdown(f"""
        <div class="report-box">
            <h2 style="color: #1e293b; text-align: center;">ZOE CONSULTS LIMITED</h2>
            <p style="text-align: center; border-bottom: 2px solid #1e293b; padding-bottom: 10px;">Official Loan Statement</p>
            <table style="width:100%">
                <tr><td><b>Client Name:</b> {c['Name']}</td><td><b>Client ID:</b> {c['Customer_ID']}</td></tr>
                <tr><td><b>Phone:</b> {c['Phone']}</td><td><b>NIN:</b> {c['NIN']}</td></tr>
                <tr><td><b>Address:</b> {c['Address']}</td><td><b>Next of Kin:</b> {c['Next_of_Kin']}</td></tr>
            </table>
            <hr>
            <h4>LOAN SUMMARY</h4>
            <p><b>Original Principal:</b> UGX {c['Principal_UGX']:,.0f}</p>
            <p><b>Annual Interest Rate:</b> {c['Annual_Rate']*100}%</p>
            <p><b>Loan Duration:</b> {c['Duration_Months']} Months</p>
            <p><b>Disbursement Date:</b> {c['Start_Date'].strftime('%d %B %Y')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Repayment Schedule")
        sched = generate_schedule(c['Principal_UGX'], c['Annual_Rate'], c['Duration_Months'])
        st.table(sched.style.format("{:,.0f}"))
