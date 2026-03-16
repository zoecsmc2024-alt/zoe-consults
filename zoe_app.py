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
    .report-card { background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOCAL DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def load_data():
    # List of all columns the app REQUIRES
    required_columns = ['SN','NAME','CONTACT','DATE_OF_ISSUE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS']
    
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        # Ensure SN stays as a string for matching
        if 'SN' in df.columns:
            df['SN'] = df['SN'].astype(str).str.zfill(5)
        
        # FIX: Check if any required columns are missing and add them if necessary
        for col in required_columns:
            if col not in df.columns:
                df[col] = "" # Adds the missing column as empty
        return df
    
    # If no file exists, create a fresh one with all headers
    return pd.DataFrame(columns=required_columns)

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
    if df.empty or len(df) == 0:
        st.info("The portfolio is currently empty. Go to Onboarding to add your first client.")
    else:
        st.table(df[['SN', 'NAME', 'DATE_OF_ISSUE', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']].style.format({
            "LOAN_AMOUNT": "{:,.0f}",
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        }))

elif choice == "👤 Onboarding":
    st.title("👤 New Loan Disbursement")
    with st.form("onboard_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME")
            contact = st.text_input("CONTACT NUMBER")
        with c2:
            amt = st.number_input("LOAN AMOUNT (UGX)", min_value=1000, step=50000)
            rate = st.number_input("MONTHLY INTEREST RATE (%)", value=3)
        
        if st.form_submit_button("✅ Save & Issue Loan"):
            new_sn = str(len(df) + 1).zfill(5)
            initial_total = amt + (amt * (rate/100))
            
            new_row = pd.DataFrame([{
                'SN': new_sn,
                'NAME': name.upper(),
                'CONTACT': contact,
                'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'),
                'LOAN_AMOUNT': amt,
                'INTEREST_RATE': rate,
                'AMOUNT_PAID': 0,
                'OUTSTANDING_AMOUNT': initial_total,
                'STATUS': 'Active'
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success(f"Loan Issued to {name.upper()}! SN: {new_sn}")
            st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Client Payment")
    with st.form("pay_form"):
        sn_search = st.text_input("Enter SN (e.g. 00001)").strip().zfill(5)
        p_amt = st.number_input("Payment Amount (UGX)", min_value=100, step=10000)
        if st.form_submit_button("Confirm Payment"):
            idx = df[df['SN'] == sn_search].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                save_data(df)
                st.success("Payment Recorded!"); st.rerun()
            else: st.error("SN not found.")

elif choice == "📄 Client Report":
    st.title("📄 Official Loan Statement")
    if df.empty or len(df) == 0:
        st.warning("No clients found. Please onboard a client first.")
    else:
        search_list = df.apply(lambda x: f"{x['SN']} - {x['NAME']}", axis=1).tolist()
        selected = st.selectbox("Select Client", search_list)
        sn_only = selected.split(" - ")[0]
        c = df[df['SN'] == sn_only].iloc[0]

        st.markdown(f"""
            <div class="report-card">
                <h2 style="text-align:center;">ZOE CONSULTS LIMITED</h2>
                <table style="width:100%">
                    <tr><td><b>Client:</b> {c['NAME']}</td><td style="text-align:right;"><b>SN:</b> {c['SN']}</td></tr>
                    <tr><td><b>Contact:</b> {c['CONTACT']}</td><td style="text-align:right;"><b>Date:</b> {c['DATE_OF_ISSUE']}</td></tr>
                </table>
            </div>
        """, unsafe_allow_html=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Principal", f"UGX {c['LOAN_AMOUNT']:,.0f}")
        m2.metric("Total Paid", f"UGX {c['AMOUNT_PAID']:,.0f}")
        m3.metric("Current Balance", f"UGX {c['OUTSTANDING_AMOUNT']:,.0f}")
