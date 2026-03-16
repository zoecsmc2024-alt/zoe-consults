import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    th { background-color: #00acee !important; color: white !important; }
    .report-card { background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; color: black; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def load_data():
    # Expanded list of columns
    cols = ['SN','NAME','CONTACT','LOCATION','EMPLOYER','NEXT_OF_KIN','DATE_OF_ISSUE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS']
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

# --- 3. NAVIGATION ---
with st.sidebar:
    st.title("Zoe Consults")
    choice = st.radio("Navigation", ["📊 Daily Report", "👤 Onboarding", "💰 Payments", "📄 Client Report"])
    st.markdown("---")
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Database", data=csv, file_name="zoe_database.csv", mime="text/csv")

# --- 4. PAGES ---

if choice == "📊 Daily Report":
    st.title("📊 Loan Portfolio Registry")
    if df.empty:
        st.info("Portfolio is empty.")
    else:
        st.table(df[['SN', 'NAME', 'LOCATION', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']].style.format({"LOAN_AMOUNT": "{:,.0f}", "OUTSTANDING_AMOUNT": "{:,.0f}"}))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Disbursement")
    with st.form("onboard_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME").upper()
            loc = st.text_input("LOCATION / ADDRESS")
            emp = st.text_input("EMPLOYER / BUSINESS")
            nok = st.text_input("NEXT OF KIN & CONTACT")
        with c2:
            contact = st.text_input("CLIENT CONTACT")
            amt = st.number_input("LOAN AMOUNT (UGX)", min_value=1000, step=50000)
            rate = st.number_input("MONTHLY RATE (%)", value=3)
        
        if st.form_submit_button("✅ Save & Issue Loan"):
            new_sn = str(len(df) + 1).zfill(5)
            initial_total = amt + (amt * (rate/100))
            new_row = pd.DataFrame([{'SN': new_sn, 'NAME': name, 'CONTACT': contact, 'LOCATION': loc, 'EMPLOYER': emp, 'NEXT_OF_KIN': nok, 'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'), 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': initial_total, 'STATUS': 'Active'}])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success(f"Loan Issued to {name}!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn_search = st.text_input("Enter SN (e.g. 00001)").strip().zfill(5)
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Confirm"):
            idx = df[df['SN'] == sn_search].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                save_data(df); st.success("Updated!"); st.rerun()
            else: st.error("Not found.")

elif choice == "📄 Client Report":
    st.title("📄 Official Loan Statement")
    if not df.empty:
        search_list = df.apply(lambda x: f"{x['SN']} - {x['NAME']}", axis=1).tolist()
        selected = st.selectbox("Select Client", search_list)
        sn_only = selected.split(" - ")[0]
        c = df[df['SN'] == sn_only].iloc[0]

        # Professional Layout
        st.markdown(f"""
            <div class="report-card">
                <h2 style="text-align:center; color:#1e293b; margin-bottom:0;">ZOE CONSULTS LIMITED</h2>
                <p style="text-align:center; color:#64748b; margin-top:0;">Loan Reduction Statement</p>
                <hr>
                <table style="width:100%; font-size: 0.9em;">
                    <tr><td><b>Client:</b> {c['NAME']}</td><td style="text-align:right;"><b>SN:</b> {c['SN']}</td></tr>
                    <tr><td><b>Contact:</b> {c['CONTACT']}</td><td style="text-align:right;"><b>Issued:</b> {c['DATE_OF_ISSUE']}</td></tr>
                    <tr><td><b>Location:</b> {c['LOCATION']}</td><td style="text-align:right;"><b>Employer:</b> {c['EMPLOYER']}</td></tr>
                    <tr><td><b>Next of Kin:</b> {c['NEXT_OF_KIN']}</td><td style="text-align:right;"><b>Status:</b> {c['STATUS']}</td></tr>
                </table>
            </div>
        """, unsafe_allow_html=True)

        st.write("")
        m1, m2, m3 = st.columns(3)
        m1.metric("Principal", f"UGX {c['LOAN_AMOUNT']:,.0f}")
        m2.metric("Total Paid", f"UGX {c['AMOUNT_PAID']:,.0f}")
        m3.metric("Current Balance", f"UGX {c['OUTSTANDING_AMOUNT']:,.0f}")

        # Reducing Balance Ledger
        st.subheader("📉 Transaction Ledger")
        ledger = [
            {"Date": c['DATE_OF_ISSUE'], "Description": "Principal Disbursement", "Debit": c['LOAN_AMOUNT'], "Credit": 0, "Balance": c['LOAN_AMOUNT']},
            {"Date": "Month End", "Description": "Initial Interest Applied", "Debit": c['LOAN_AMOUNT']*(c['INTEREST_RATE']/100), "Credit": 0, "Balance": c['LOAN_AMOUNT']*(1 + c['INTEREST_RATE']/100)},
            {"Date": "Current", "Description": "Total Payments to Date", "Debit": 0, "Credit": c['AMOUNT_PAID'], "Balance": c['OUTSTANDING_AMOUNT']}
        ]
        st.table(pd.DataFrame(ledger).style.format({"Debit": "{:,.0f}", "Credit": "{:,.0f}", "Balance": "{:,.0f}"}))
