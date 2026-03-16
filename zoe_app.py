import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .report-card { background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; color: black; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def load_data():
    # Added 'EXPECTED_DUE_DATE' to track risk
    cols = ['SN','NAME','NIN','CONTACT','LOCATION','EMPLOYER','NEXT_OF_KIN','DATE_OF_ISSUE','EXPECTED_DUE_DATE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS']
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        for c in cols:
            if c not in df.columns: df[c] = ""
        df['SN'] = df['SN'].astype(str).str.zfill(5)
        return df
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(DB_FILE, index=False)

df = load_data()

# --- 3. NAVIGATION & BRANDING ---
with st.sidebar:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=150)
    else:
        st.title("🏦 Zoe Consults")
    
    st.markdown("---")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 DOWNLOAD DATABASE (CSV)", data=csv, file_name="zoe_database.csv", mime="text/csv", use_container_width=True)

    st.write("")
    if st.button("🔴 CLICK HERE TO LOGOUT", key="logout", use_container_width=True):
        st.rerun()

    st.markdown("""<style>.stDownloadButton button { background-color: #00acee !important; color: white !important; font-weight: bold !important; } .stButton button { background-color: #ef4444 !important; color: white !important; font-weight: bold !important; }</style>""", unsafe_allow_html=True)

# --- 4. PAGES ---

if choice == "📊 Daily Report":
    st.title("📊 Loan Portfolio & Risk Analysis")
    if not df.empty:
        # RISK LOGIC: Highlight row if Date > Due Date AND Balance > 0
        def highlight_risky(row):
            try:
                due_date = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
                today = datetime.date.today()
                if today > due_date and row['OUTSTANDING_AMOUNT'] > 0:
                    return ['background-color: #fee2e2; color: #991b1b'] * len(row) # Light red background
                return [''] * len(row)
            except:
                return [''] * len(row)

        st.subheader("📋 Registry (Red = Overdue)")
        styled_df = df[['SN', 'NAME', 'EXPECTED_DUE_DATE', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']].style.apply(highlight_risky, axis=1).format({
            "LOAN_AMOUNT": "{:,.0f}", 
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        })
        st.table(styled_df)

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Disbursement")
    with st.form("onboard"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME").upper()
            nin = st.text_input("NIN")
            loc = st.text_input("LOCATION")
            emp = st.text_input("EMPLOYER")
        with c2:
            amt = st.number_input("LOAN AMOUNT (UGX)", min_value=1000)
            rate = st.number_input("MONTHLY RATE (%)", value=3)
            # New: Set the expected due date
            months = st.number_input("DURATION (MONTHS)", min_value=1, value=1)
            due_date = datetime.date.today() + datetime.timedelta(days=30*months)
            st.info(f"Automatically calculated Due Date: {due_date.strftime('%d-%b-%Y')}")
        
        if st.form_submit_button("✅ Save & Issue"):
            new_sn = str(len(df) + 1).zfill(5)
            initial_total = amt + (amt * (rate/100))
            new_row = pd.DataFrame([{
                'SN': new_sn, 'NAME': name, 'NIN': nin, 'LOCATION': loc, 'EMPLOYER': emp,
                'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'),
                'EXPECTED_DUE_DATE': due_date.strftime('%d-%b-%Y'),
                'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 
                'OUTSTANDING_AMOUNT': initial_total, 'STATUS': 'Active'
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("Loan Issued!"); st.rerun()

elif choice == "💰 Payments":
    # (Existing payments logic remains here)
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn_search = st.text_input("Enter SN").strip().zfill(5)
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Confirm"):
            idx = df[df['SN'] == sn_search].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                # If paid off, change status
                if df.at[idx[0], 'OUTSTANDING_AMOUNT'] <= 0:
                    df.at[idx[0], 'STATUS'] = 'Cleared'
                save_data(df); st.success("Updated!"); st.rerun()
            else: st.error("Not found.")

elif choice == "📄 Client Report":
    # (Existing report logic remains here)
    st.title("📄 Official Loan Statement")
    if not df.empty:
        search_list = df.apply(lambda x: f"{x['SN']} - {x['NAME']}", axis=1).tolist()
        selected = st.selectbox("Select Client", search_list)
        sn_only = selected.split(" - ")[0]
        c = df[df['SN'] == sn_only].iloc[0]

        st.markdown(f"""
            <div class="report-card">
                <h2 style="text-align:center;">ZOE CONSULTS LIMITED</h2>
                <hr>
                <table style="width:100%">
                    <tr><td><b>Client:</b> {c['NAME']}</td><td style="text-align:right;"><b>SN:</b> {c['SN']}</td></tr>
                    <tr><td><b>NIN:</b> {c['NIN']}</td><td style="text-align:right;"><b>Due Date:</b> {c['EXPECTED_DUE_DATE']}</td></tr>
                </table>
            </div>
        """, unsafe_allow_html=True)
        # Metrics & Ledger
        st.write("")
        m1, m2, m3 = st.columns(3)
        m1.metric("Principal", f"UGX {c['LOAN_AMOUNT']:,.0f}")
        m2.metric("Paid", f"UGX {c['AMOUNT_PAID']:,.0f}")
        m3.metric("Balance", f"UGX {c['OUTSTANDING_AMOUNT']:,.0f}")
