import streamlit as st
import pandas as pd
import datetime
import os
import base64
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    .stTable td, .stTable th { color: #1e293b !important; }
    thead tr th { background-color: #00acc1 !important; color: white !important; }
    .report-card { background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; color: #1e293b; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .stDownloadButton button { background-color: #00acc1 !important; color: white !important; border: none !important; width: 100%; }
    .stButton button { background-color: transparent !important; color: #ef4444 !important; border: 1px solid #ef4444 !important; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def load_data():
    # These are the "Must-Have" columns for your app to work
    required_cols = ['SN','NAME','NIN','CONTACT','LOCATION','EMPLOYER','DATE_OF_ISSUE','EXPECTED_DUE_DATE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS']
    
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Check if any required columns are missing and add them if necessary
        for col in required_cols:
            if col not in df.columns:
                df[col] = "" # Create the column with empty values if it's missing
        
        # Clean up the numbers
        df['OUTSTANDING_AMOUNT'] = pd.to_numeric(df['OUTSTANDING_AMOUNT'], errors='coerce').fillna(0)
        df['SN'] = df['SN'].astype(str).str.zfill(5)
        return df[required_cols] # Ensure they are in the right order
    
    return pd.DataFrame(columns=required_cols)
# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    # Circular Logo Logic
    logo_content = ""
    if os.path.exists("logo.jpg"):
        with open("logo.jpg", "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        logo_content = f'<img src="data:image/jpeg;base64,{data}" style="width:120px;">'
    else:
        logo_content = '<h1 style="color: #00acc1; margin:0;">Z</h1>'

    st.markdown(f"""
        <div style="text-align: center; padding: 10px;">
            <div style="background-color: white; border-radius: 15px; padding: 15px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <div style="width: 120px; height: 120px; border-radius: 50%; overflow: hidden; display: flex; justify-content: center; align-items: center; border: 2px solid #e2e8f0;">
                    {logo_content}
                </div>
            </div>
            <h3 style="color: white; margin-top: 15px; font-family: 'Segoe UI';">ZOE LEND IQ <span style="color:#00acc1; font-weight:bold;">PRO</span></h3>
        </div>
        <div style='border-top: 1px solid #334155; margin-bottom: 20px;'></div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='color: #64748b; font-size: 0.7em; font-weight: bold; letter-spacing: 1.5px; margin-left: 5px;'>MAIN MENU</p>", unsafe_allow_html=True)
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"], label_visibility="collapsed")
    
    st.markdown("<div style='margin-top: 30px; border-top: 1px solid #334155; margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 EXPORT DATABASE", data=csv, file_name="Zoe_Database.csv", mime="text/csv")
    if st.button("🔓 SECURE LOGOUT"):
        st.rerun()

# --- 4. PAGES ---

if choice == "📊 Daily Report":
    st.title("📊 Portfolio Insights")
    if not df.empty:
        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Principal", f"{df['LOAN_AMOUNT'].sum():,.0f}")
        m2.metric("Total Collected", f"{df['AMOUNT_PAID'].sum():,.0f}")
        m3.metric("Current Risk", f"{df['OUTSTANDING_AMOUNT'].sum():,.0f}")

        # Registry with Styling
        def registry_style(row):
            try:
                due = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
                if datetime.date.today() > due and row['OUTSTANDING_AMOUNT'] > 0:
                    return ['background-color: #fee2e2; color: #991b1b; font-weight: bold'] * len(row)
                if row['STATUS'] == 'Cleared':
                    return ['background-color: #dcfce7; color: #166534'] * len(row)
            except: pass
            return [''] * len(row)

        st.subheader("📋 Loan Portfolio Registry")
        display_cols = ['SN', 'NAME', 'DATE_OF_ISSUE', 'EXPECTED_DUE_DATE', 'OUTSTANDING_AMOUNT', 'STATUS']
        st.table(df[display_cols].style.apply(registry_style, axis=1).format({"OUTSTANDING_AMOUNT": "{:,.0f}"}))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan / Excel Migration")
    with st.form("onboard"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME").upper(); nin = st.text_input("NIN")
            dis_date = st.date_input("DISBURSEMENT DATE", value=datetime.date.today())
        with c2:
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("RATE (%)", value=3)
            paid_already = st.number_input("EXISTING PAID AMOUNT", min_value=0)
            due_date = dis_date + datetime.timedelta(days=30)
        
        if st.form_submit_button("✅ Save & Migrate"):
            new_sn = str(len(df) + 1).zfill(5)
            total = amt + (amt * (rate/100))
            bal = total - paid_already
            new_row = pd.DataFrame([{'SN': new_sn, 'NAME': name, 'NIN': nin, 'DATE_OF_ISSUE': dis_date.strftime('%d-%b-%Y'), 'EXPECTED_DUE_DATE': due_date.strftime('%d-%b-%Y'), 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': paid_already, 'OUTSTANDING_AMOUNT': bal, 'STATUS': 'Active' if bal > 0 else 'Cleared'}])
            df = pd.concat([df, new_row], ignore_index=True); save_data(df); st.success("Success!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn = st.text_input("Enter SN").strip().zfill(5)
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Confirm"):
            idx = df[df['SN'] == sn].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt; df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                if df.at[idx[0], 'OUTSTANDING_AMOUNT'] <= 0: df.at[idx[0], 'STATUS'] = 'Cleared'
                save_data(df); st.success("Updated!"); st.rerun()

elif choice == "📄 Client Report":
    st.title("📄 Client Statement")
    if not df.empty:
        sel = st.selectbox("Select Client", df.apply(lambda x: f"{x['SN']} - {x['NAME']}", axis=1))
        c = df[df['SN'] == sel.split(" - ")[0]].iloc[0]
        st.markdown(f'<div class="report-card"><h3>{c["NAME"]}</h3><p>NIN: {c["NIN"]}<br>Due: {c["EXPECTED_DUE_DATE"]}</p></div>', unsafe_allow_html=True)
        st.metric("Balance", f"{c['OUTSTANDING_AMOUNT']:,.0f}")
