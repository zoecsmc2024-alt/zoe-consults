import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 1. SETTINGS & THEMING ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

# This CSS fixes the table headers and the report card look
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
    cols = ['SN','NAME','NIN','CONTACT','LOCATION','EMPLOYER','NEXT_OF_KIN','DATE_OF_ISSUE','EXPECTED_DUE_DATE','LOAN_AMOUNT','INTEREST_RATE','AMOUNT_PAID','OUTSTANDING_AMOUNT','STATUS']
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        for c in cols:
            if c not in df.columns: df[c] = ""
        df['SN'] = df['SN'].astype(str).str.zfill(5)
        # Ensure numbers are numeric
        df['OUTSTANDING_AMOUNT'] = pd.to_numeric(df['OUTSTANDING_AMOUNT'], errors='coerce').fillna(0)
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
    
    # ENFORCEMENT SECTION
    st.subheader("⚖️ Enforcement")
    penalty_rate = st.number_input("Overdue Penalty (%)", value=5, key="penalty_box")
    if st.button("⚠️ Apply Penalty to Red Rows", use_container_width=True):
        today = datetime.date.today()
        count = 0
        for idx, row in df.iterrows():
            due = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
            if today > due and row['OUTSTANDING_AMOUNT'] > 0:
                df.at[idx, 'OUTSTANDING_AMOUNT'] += (row['OUTSTANDING_AMOUNT'] * (penalty_rate / 100))
                count += 1
        save_data(df); st.success(f"Penalized {count} clients!"); st.rerun()

    st.markdown("---")
    # THE "IRONCLAD" BUTTONS
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 DOWNLOAD DATABASE (CSV)", data=csv, file_name="zoe_database.csv", mime="text/csv", use_container_width=True)
    
    if st.button("🔴 CLICK HERE TO LOGOUT", key="logout_btn", use_container_width=True):
        st.rerun()

    st.markdown("""<style>
        .stDownloadButton button { background-color: #00acee !important; color: white !important; font-weight: bold !important; }
        .stButton button { background-color: #ef4444 !important; color: white !important; font-weight: bold !important; }
    </style>""", unsafe_allow_html=True)

# --- 4. PAGES ---

if choice == "📊 Daily Report":
    st.title("📊 Portfolio Dashboard")
    if not df.empty:
        # Chart
        df_sorted = df.copy()
        df_sorted['DATE_OF_ISSUE'] = pd.to_datetime(df_sorted['DATE_OF_ISSUE'])
        df_sorted = df_sorted.sort_values('DATE_OF_ISSUE')
        df_sorted['Cumulative'] = df_sorted['AMOUNT_PAID'].cumsum()
        st.plotly_chart(px.line(df_sorted, x='DATE_OF_ISSUE', y='Cumulative', title="Collection Growth", markers=True), use_container_width=True)

        # Risk Logic
        def highlight_risky(row):
            try:
                due = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
                if datetime.date.today() > due and row['OUTSTANDING_AMOUNT'] > 0:
                    return ['background-color: #fee2e2; color: #991b1b'] * len(row)
            except: pass
            return [''] * len(row)

        st.subheader("📋 Registry")
        st.dataframe(df[['SN', 'NAME', 'NIN', 'EXPECTED_DUE_DATE', 'OUTSTANDING_AMOUNT', 'STATUS']].style.apply(highlight_risky, axis=1).format({"OUTSTANDING_AMOUNT": "{:,.0f}"}), use_container_width=True)

        # THE PENCIL EDIT TOOL
        with st.expander("✏️ Edit Client Details"):
            edit_sn = st.selectbox("Select SN to modify:", ["Select..."] + df['SN'].tolist())
            if edit_sn != "Select...":
                idx = df[df['SN'] == edit_sn].index[0]
                with st.form("edit_form"):
                    u_name = st.text_input("Name", value=df.at[idx, 'NAME'])
                    u_nin = st.text_input("NIN", value=df.at[idx, 'NIN'])
                    u_loc = st.text_input("Location", value=df.at[idx, 'LOCATION'])
                    u_stat = st.selectbox("Status", ["Active", "Risky", "Dormant", "Cleared"], index=["Active", "Risky", "Dormant", "Cleared"].index(df.at[idx, 'STATUS']))
                    if st.form_submit_button("💾 Update Record"):
                        df.at[idx, 'NAME'] = u_name.upper(); df.at[idx, 'NIN'] = u_nin; df.at[idx, 'LOCATION'] = u_loc; df.at[idx, 'STATUS'] = u_stat
                        save_data(df); st.success("Updated!"); st.rerun()

elif choice == "👤 Onboarding":
    st.title("👤 New Loan")
    with st.form("onboard"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME").upper(); nin = st.text_input("NIN")
            loc = st.text_input("LOCATION"); emp = st.text_input("EMPLOYER")
        with c2:
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("RATE (%)", value=3); dur = st.number_input("MONTHS", min_value=1, value=1)
            due = datetime.date.today() + datetime.timedelta(days=30*dur)
        if st.form_submit_button("✅ Save"):
            new_sn = str(len(df) + 1).zfill(5)
            new_row = pd.DataFrame([{'SN': new_sn, 'NAME': name, 'NIN': nin, 'LOCATION': loc, 'EMPLOYER': emp, 'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'), 'EXPECTED_DUE_DATE': due.strftime('%d-%b-%Y'), 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': amt+(amt*(rate/100)), 'STATUS': 'Active'}])
            df = pd.concat([df, new_row], ignore_index=True); save_data(df); st.success("Done!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn = st.text_input("Enter SN").strip().zfill(5)
        p_amt = st.number_input("Amount", min_value=100)
        if st.form_submit_button("Confirm"):
            idx = df[df['SN'] == sn].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt; df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                if df.at[idx[0], 'OUTSTANDING_AMOUNT'] <= 0: df.at[idx[0], 'STATUS'] = 'Cleared'
                save_data(df); st.success("Paid!"); st.rerun()
            else: st.error("Not found.")

elif choice == "📄 Client Report":
    st.title("📄 Official Statement")
    if not df.empty:
        sel = st.selectbox("Select Client", df.apply(lambda x: f"{x['SN']} - {x['NAME']}", axis=1))
        c = df[df['SN'] == sel.split(" - ")[0]].iloc[0]
        st.markdown(f'<div class="report-card"><h2 style="text-align:center;">ZOE CONSULTS</h2><hr><b>Client:</b> {c["NAME"]}<br><b>NIN:</b> {c["NIN"]}<br><b>Due:</b> {c["EXPECTED_DUE_DATE"]}</div>', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Principal", f"{c['LOAN_AMOUNT']:,.0f}"); m2.metric("Paid", f"{c['AMOUNT_PAID']:,.0f}"); m3.metric("Balance", f"{c['OUTSTANDING_AMOUNT']:,.0f}")
        
        # RESTORED LEDGER
        st.subheader("📉 Transaction Ledger")
        int_amt = float(c['LOAN_AMOUNT']) * (float(c['INTEREST_RATE'])/100)
        ledger = [
            {"Date": c['DATE_OF_ISSUE'], "Description": "Disbursement", "Debit": c['LOAN_AMOUNT'], "Credit": 0, "Balance": c['LOAN_AMOUNT']},
            {"Date": "Month End", "Description": "Interest", "Debit": int_amt, "Credit": 0, "Balance": float(c['LOAN_AMOUNT'])+int_amt},
            {"Date": "Current", "Description": "Payments", "Debit": 0, "Credit": c['AMOUNT_PAID'], "Balance": c['OUTSTANDING_AMOUNT']}
        ]
        st.table(pd.DataFrame(ledger).style.format({"Debit": "{:,.0f}", "Credit": "{:,.0f}", "Balance": "{:,.0f}"}))
