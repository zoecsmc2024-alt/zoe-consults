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
    st.title("📊 Portfolio Insights")
    
    if df.empty:
        st.info("Portfolio is empty. Onboard your first client to see analytics.")
    else:
        # 1. TOP SUMMARY METRICS (Styled like your reference image)
        t_principal = df['LOAN_AMOUNT'].sum()
        t_collected = df['AMOUNT_PAID'].sum()
        t_outstanding = df['OUTSTANDING_AMOUNT'].sum()
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""<div style="background-color: #00acc1; padding: 20px; border-radius: 10px; color: white;">
                <p style="margin:0; font-size: 0.8em; opacity: 0.8;">TOTAL DISBURSED</p>
                <h2 style="margin:0;">UGX {t_principal:,.0f}</h2>
            </div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div style="background-color: #1e293b; padding: 20px; border-radius: 10px; color: white;">
                <p style="margin:0; font-size: 0.8em; opacity: 0.8;">TOTAL COLLECTED</p>
                <h2 style="margin:0;">UGX {t_collected:,.0f}</h2>
            </div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div style="background-color: #f8fafc; padding: 20px; border-radius: 10px; color: #1e293b; border: 1px solid #e2e8f0;">
                <p style="margin:0; font-size: 0.8em; color: gray;">OUTSTANDING BALANCE</p>
                <h2 style="margin:0; color: #00acc1;">UGX {t_outstanding:,.0f}</h2>
            </div>""", unsafe_allow_html=True)

        st.write("")

        # 2. COLLECTION TREND CHART
        st.subheader("📈 Business Growth")
        df_sorted = df.copy()
        df_sorted['DATE_OF_ISSUE'] = pd.to_datetime(df_sorted['DATE_OF_ISSUE'])
        df_sorted = df_sorted.sort_values('DATE_OF_ISSUE')
        df_sorted['Cumulative'] = df_sorted['AMOUNT_PAID'].cumsum()
        
        fig = px.area(df_sorted, x='DATE_OF_ISSUE', y='Cumulative', 
                      title="Cumulative Collections (UGX)",
                      color_discrete_sequence=['#00acc1'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # 3. PREMIUM REGISTRY TABLE
        st.subheader("📋 Loan Registry")
        
        # Risk Highlighting Logic
        def highlight_risky(row):
            try:
                due = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
                if datetime.date.today() > due and row['OUTSTANDING_AMOUNT'] > 0:
                    return ['background-color: #ffebee; color: #c62828; font-weight: bold'] * len(row)
            except: pass
            return [''] * len(row)

        # Styling the dataframe
        styled_registry = df[['SN', 'NAME', 'NIN', 'EXPECTED_DUE_DATE', 'OUTSTANDING_AMOUNT', 'STATUS']].style.apply(highlight_risky, axis=1).format({
            "OUTSTANDING_AMOUNT": "{:,.0f}"
        })
        
        st.dataframe(styled_registry, use_container_width=True)

        # 4. QUICK EDIT ACTION (The "Pencil" section)
        with st.expander("✏️ Quick Modify Client"):
            edit_sn = st.selectbox("Select Serial Number:", ["Select..."] + df['SN'].tolist())
            if edit_sn != "Select...":
                idx = df[df['SN'] == edit_sn].index[0]
                with st.form("quick_edit"):
                    st.write(f"Editing **{df.at[idx, 'NAME']}**")
                    new_stat = st.selectbox("Update Status", ["Active", "Risky", "Cleared", "Dormant"], index=["Active", "Risky", "Cleared", "Dormant"].index(df.at[idx, 'STATUS']))
                    if st.form_submit_button("Update Status"):
                        df.at[idx, 'STATUS'] = new_stat
                        save_data(df)
                        st.success("Status Updated!"); st.rerun()
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
    # 1. TOP PROFILE HEADER (Inspired by your image)
    if not df.empty:
        client_options = df.apply(lambda x: f"{str(x['SN']).zfill(5)} - {x['NAME']}", axis=1).tolist()
        selected_client = st.selectbox("Search Borrower", client_options)
        c = df[df['SN'].astype(str).str.zfill(5) == selected_client.split(" - ")[0]].iloc[0]

        st.markdown(f"""
            <div style="background-color: white; padding: 20px; border-radius: 10px; border-top: 5px solid #00acc1; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h2 style="margin:0; color:#1e293b;">{c['NAME']}</h2>
                        <p style="color:#00acc1; font-weight:bold; margin:0;">CL-{c['SN']}</p>
                        <p style="font-size:0.8em; color:gray;">Issued: {c['DATE_OF_ISSUE']}</p>
                    </div>
                    <div style="text-align: right; font-size:0.9em;">
                        <p><b>Address:</b> {c['LOCATION']}</p>
                        <p><b>NIN:</b> {c['NIN']}</p>
                        <p><b>Employer:</b> {c['EMPLOYER']}</p>
                    </div>
                </div>
                <div style="margin-top:15px;">
                    <span style="background-color:#00acc1; color:white; padding:5px 15px; border-radius:5px; font-size:0.8em;">Add Loan</span>
                    <span style="background-color:#1e293b; color:white; padding:5px 15px; border-radius:5px; font-size:0.8em; margin-left:10px;">View All Loans</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.write("")

        # 2. MAIN LOAN SUMMARY BAR (Teal Theme)
        st.markdown("""
            <style>
            .loan-header { background-color: #e0f7fa; color: #00838f; padding: 10px; font-weight: bold; border-bottom: 2px solid #00acc1; display: flex; justify-content: space-between; }
            .loan-row { background-color: white; padding: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #eee; font-size: 0.9em; }
            </style>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="loan-header">
                <span>Loan#</span><span>Principal</span><span>Interest</span><span>Due</span><span>Paid</span><span>Balance</span><span>Status</span>
            </div>
            <div class="loan-row">
                <span>LN-{c['SN']}</span>
                <span>{float(c['LOAN_AMOUNT']):,.0f}</span>
                <span>{c['INTEREST_RATE']}%</span>
                <span>{float(c['OUTSTANDING_AMOUNT']) + float(c['AMOUNT_PAID']):,.0f}</span>
                <span>{float(c['AMOUNT_PAID']):,.0f}</span>
                <span style="color:#00838f; font-weight:bold;">{float(c['OUTSTANDING_AMOUNT']):,.0f}</span>
                <span style="background-color:#00acc1; color:white; padding:2px 8px; border-radius:4px; font-size:0.8em;">{c['STATUS']}</span>
            </div>
        """, unsafe_allow_html=True)

        # 3. THE TABBED NAVIGATION (Just like your image!)
        st.write("")
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Repayments", "📝 Loan Terms", "📅 Schedule", "📎 Files"])

        with tab1:
            st.subheader("Repayment History")
            # Creating the ledger table to look like the image
            ledger_df = pd.DataFrame([
                {"Date": c['DATE_OF_ISSUE'], "Description": "Loan Released", "Principal": c['LOAN_AMOUNT'], "Interest": 0, "Total": c['LOAN_AMOUNT']},
                {"Date": "To Date", "Description": "Collections Received", "Principal": 0, "Interest": 0, "Total": f"-{c['AMOUNT_PAID']}"}
            ])
            st.table(ledger_df)
            st.button("➕ Add Repayment")

        with tab2:
            st.info(f"Monthly Interest Rate: {c['INTEREST_RATE']}% | Next of Kin: {c['NEXT_OF_KIN']}")

        with tab3:
            st.write(f"Final Maturity Date: **{c['EXPECTED_DUE_DATE']}**")
