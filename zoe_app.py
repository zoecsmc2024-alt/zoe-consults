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
    th { background-color: #00acee !important; color: white !important; }
    .report-card { background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; color: black; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "zoe_database.csv"

def load_data():
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
    st.title("📊 Loan Portfolio Dashboard")
    
    if df.empty:
        st.info("Portfolio is empty.")
    else:
        # --- CALCULATE TOTALS ---
        total_principal = df['LOAN_AMOUNT'].sum()
        # Interest is Amount to be paid minus Principal
        # In our current logic: Interest = (Principal * Rate/100)
        total_interest = (df['LOAN_AMOUNT'] * (df['INTEREST_RATE'] / 100)).sum()
        total_collected = df['AMOUNT_PAID'].sum()
        total_outstanding = df['OUTSTANDING_AMOUNT'].sum()

        # --- TOP METRICS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Disbursed", f"UGX {total_principal:,.0f}")
        m2.metric("Total Interest Earned", f"UGX {total_interest:,.0f}")
        m3.metric("Total Collected", f"UGX {total_collected:,.0f}", delta=f"{total_collected:,.0f}")

        # --- FINANCIAL CHART ---
        st.subheader("💰 Portfolio Composition")
        
        # Data for the pie chart
        summary_data = {
            "Category": ["Principal (Capital)", "Interest (Profit)", "Amount Paid (Liquidity)"],
            "Amount": [total_principal, total_interest, total_collected]
        }
        summary_df = pd.DataFrame(summary_data)
        
        fig = px.pie(summary_df, values='Amount', names='Category', hole=0.5, 
                     color_discrete_sequence=['#00acee', '#ff9900', '#10b981'],
                     title="Capital vs Profit vs Collection")
        
        st.plotly_chart(fig, use_container_width=True)

        # --- REGISTRY TABLE ---
        st.subheader("📋 Detailed Registry")
        st.table(df[['SN', 'NAME', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT', 'STATUS']].style.format({
            "LOAN_AMOUNT": "{:,.0f}", 
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        }))

        # --- RESTORED EDIT TOOL (The "Pencil" Action) ---
        st.markdown("---")
        with st.expander("✏️ Edit Client Details"):
            edit_sn = st.selectbox("Select SN to modify:", ["Select..."] + df['SN'].tolist())
            if edit_sn != "Select...":
                idx = df[df['SN'] == edit_sn].index[0]
                with st.form("edit_client_form"):
                    st.write(f"Editing: **{df.at[idx, 'NAME']}**")
                    new_name = st.text_input("Name", value=df.at[idx, 'NAME'])
                    new_loc = st.text_input("Location", value=df.at[idx, 'LOCATION'])
                    new_emp = st.text_input("Employer", value=df.at[idx, 'EMPLOYER'])
                    new_nok = st.text_input("Next of Kin", value=df.at[idx, 'NEXT_OF_KIN'])
                    new_stat = st.selectbox("Status", ["Active", "Risky", "Dormant"], 
                                           index=["Active", "Risky", "Dormant"].index(df.at[idx, 'STATUS']))
                    
                    if st.form_submit_button("💾 Update Record"):
                        df.at[idx, 'NAME'] = new_name.upper()
                        df.at[idx, 'LOCATION'] = new_loc
                        df.at[idx, 'EMPLOYER'] = new_emp
                        df.at[idx, 'NEXT_OF_KIN'] = new_nok
                        df.at[idx, 'STATUS'] = new_stat
                        save_data(df)
                        st.success("Record updated successfully!")
                        st.rerun()

elif choice == "👤 Onboarding":
    # ... (Keep your onboarding code here) ...
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
    # ... (Keep your payments code here) ...
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
        # Client Selector
        search_list = df.apply(lambda x: f"{x['SN']} - {x['NAME']}", axis=1).tolist()
        selected = st.selectbox("Select Client to View Ledger", search_list)
        sn_only = selected.split(" - ")[0]
        c = df[df['SN'] == sn_only].iloc[0]

        # 1. THE PROFESSIONAL STATEMENT HEADER
        st.markdown(f"""
            <div class="report-card">
                <h2 style="text-align:center; color:#1e293b; margin-bottom:0;">ZOE CONSULTS LIMITED</h2>
                <p style="text-align:center; color:#64748b; margin-top:0;">Official Loan Statement</p>
                <hr style="border: 0.5px solid #eee;">
                <table style="width:100%; font-size: 0.9em; border-collapse: collapse;">
                    <tr>
                        <td style="padding:5px;"><b>Client:</b> {c['NAME']}</td>
                        <td style="padding:5px; text-align:right;"><b>SN:</b> {c['SN']}</td>
                    </tr>
                    <tr>
                        <td style="padding:5px;"><b>Location:</b> {c['LOCATION']}</td>
                        <td style="padding:5px; text-align:right;"><b>Employer:</b> {c['EMPLOYER']}</td>
                    </tr>
                    <tr>
                        <td style="padding:5px;"><b>Next of Kin:</b> {c['NEXT_OF_KIN']}</td>
                        <td style="padding:5px; text-align:right;"><b>Issued:</b> {c['DATE_OF_ISSUE']}</td>
                    </tr>
                </table>
            </div>
        """, unsafe_allow_html=True)

        # 2. THE BIG NUMBERS
        st.write("")
        m1, m2, m3 = st.columns(3)
        m1.metric("Original Principal", f"UGX {c['LOAN_AMOUNT']:,.0f}")
        m2.metric("Total Paid", f"UGX {c['AMOUNT_PAID']:,.0f}", delta=f"{c['AMOUNT_PAID']}", delta_color="normal")
        m3.metric("Current Balance", f"UGX {c['OUTSTANDING_AMOUNT']:,.0f}", delta_color="inverse")

        # 3. THE REDUCING BALANCE LEDGER (The missing piece!)
        st.markdown("---")
        st.subheader("📉 Reducing Balance Ledger")
        
        # We calculate the interest amount for the row
        interest_val = float(c['LOAN_AMOUNT']) * (float(c['INTEREST_RATE']) / 100)
        
        ledger_data = [
            {
                "Date": c['DATE_OF_ISSUE'], 
                "Description": "Principal Disbursement", 
                "Debit (+Int)": f"{float(c['LOAN_AMOUNT']):,.0f}", 
                "Credit (Pay)": "0", 
                "Balance": f"{float(c['LOAN_AMOUNT']):,.0f}"
            },
            {
                "Date": "Month End", 
                "Description": f"Interest Charged ({c['INTEREST_RATE']}%)", 
                "Debit (+Int)": f"{interest_val:,.0f}", 
                "Credit (Pay)": "0", 
                "Balance": f"{(float(c['LOAN_AMOUNT']) + interest_val):,.0f}"
            },
            {
                "Date": "To Date", 
                "Description": "Total Payments Received", 
                "Debit (+Int)": "0", 
                "Credit (Pay)": f"{float(c['AMOUNT_PAID']):,.0f}", 
                "Balance": f"{float(c['OUTSTANDING_AMOUNT']):,.0f}"
            }
        ]
        
        st.table(pd.DataFrame(ledger_data))
        
        st.caption("Disclaimer: This is a system-generated statement. Interest is applied to the reducing balance monthly.")

    else:
        st.warning("No client data found. Please add a client first.")
