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
    
    # --- PRO FEATURE 1: PENALTY ENFORCEMENT ---
    st.subheader("⚖️ Enforcement")
    penalty_rate = st.number_input("Overdue Penalty (%)", value=5)
    if st.button("⚠️ Apply Penalty to Red Rows", use_container_width=True):
        today = datetime.date.today()
        penalized_count = 0
        for idx, row in df.iterrows():
            due = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
            if today > due and row['OUTSTANDING_AMOUNT'] > 0:
                penalty_charge = row['OUTSTANDING_AMOUNT'] * (penalty_rate / 100)
                df.at[idx, 'OUTSTANDING_AMOUNT'] += penalty_charge
                penalized_count += 1
        save_data(df)
        st.success(f"Applied {penalty_rate}% penalty to {penalized_count} clients!")
        st.rerun()

    st.markdown("---")
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 DOWNLOAD DATABASE", data=csv, file_name="zoe_database.csv", mime="text/csv", use_container_width=True)

    if st.button("🔴 LOGOUT", key="logout", use_container_width=True):
        st.rerun()

    st.markdown("""<style>.stDownloadButton button { background-color: #00acee !important; color: white !important; font-weight: bold !important; } .stButton button { background-color: #ef4444 !important; color: white !important; font-weight: bold !important; }</style>""", unsafe_allow_html=True)

# --- 4. PAGES ---

if choice == "📊 Daily Report":
    st.title("📊 Portfolio Insights")
    if not df.empty:
        # --- PRO FEATURE 2: PERFORMANCE CHART ---
        st.subheader("📈 Collection Trend")
        # Ensure dates are proper for the chart
        df['DATE_OF_ISSUE'] = pd.to_datetime(df['DATE_OF_ISSUE'], errors='coerce')
        df_sorted = df.dropna(subset=['DATE_OF_ISSUE']).sort_values('DATE_OF_ISSUE')
        
        if not df_sorted.empty:
            df_sorted['Cumulative_Collected'] = df_sorted['AMOUNT_PAID'].cumsum()
            fig = px.line(df_sorted, x='DATE_OF_ISSUE', y='Cumulative_Collected', 
                          title="Business Liquidity Growth",
                          markers=True, line_shape="spline", color_discrete_sequence=["#10b981"])
            st.plotly_chart(fig, use_container_width=True)

        # --- THE FIX FOR THE TABLE ERROR ---
        def highlight_risky(row):
            try:
                # Convert string dates to actual date objects for comparison
                due = pd.to_datetime(row['EXPECTED_DUE_DATE']).date()
                out = float(row['OUTSTANDING_AMOUNT'])
                if datetime.date.today() > due and out > 0:
                    return ['background-color: #fee2e2; color: #991b1b'] * len(row)
            except:
                pass
            return [''] * len(row)

        st.subheader("📋 Registry")
        # Ensure numeric columns are actually numeric before formatting
        df['OUTSTANDING_AMOUNT'] = pd.to_numeric(df['OUTSTANDING_AMOUNT'], errors='coerce').fillna(0)
        
        # We use st.dataframe instead of st.table for better error handling and scrolling
        st.dataframe(
            df[['SN', 'NAME', 'EXPECTED_DUE_DATE', 'OUTSTANDING_AMOUNT', 'STATUS']].style.apply(highlight_risky, axis=1).format({
                "OUTSTANDING_AMOUNT": "{:,.0f}"
            }),
            use_container_width=True
        )
elif choice == "👤 Onboarding":
    st.title("👤 Issue New Loan")
    # ... (Keep existing onboarding logic)
    with st.form("onboard"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("FULL NAME").upper(); nin = st.text_input("NIN")
            loc = st.text_input("LOCATION"); emp = st.text_input("EMPLOYER")
        with c2:
            amt = st.number_input("LOAN AMOUNT", min_value=1000)
            rate = st.number_input("MONTHLY RATE (%)", value=3)
            dur = st.number_input("DURATION (MONTHS)", min_value=1, value=1)
            due = datetime.date.today() + datetime.timedelta(days=30*dur)
            st.info(f"Due Date: {due.strftime('%d-%b-%Y')}")
        
        if st.form_submit_button("✅ Save"):
            new_sn = str(len(df) + 1).zfill(5)
            new_row = pd.DataFrame([{'SN': new_sn, 'NAME': name, 'NIN': nin, 'LOCATION': loc, 'EMPLOYER': emp, 'DATE_OF_ISSUE': datetime.date.today().strftime('%d-%b-%Y'), 'EXPECTED_DUE_DATE': due.strftime('%d-%b-%Y'), 'LOAN_AMOUNT': amt, 'INTEREST_RATE': rate, 'AMOUNT_PAID': 0, 'OUTSTANDING_AMOUNT': amt + (amt*(rate/100)), 'STATUS': 'Active'}])
            df = pd.concat([df, new_row], ignore_index=True); save_data(df); st.success("Saved!"); st.rerun()

elif choice == "💰 Payments":
    st.title("💰 Post Payment")
    with st.form("pay"):
        sn = st.text_input("Enter SN").strip().zfill(5)
        p_amt = st.number_input("Amount (UGX)", min_value=100)
        if st.form_submit_button("Confirm"):
            idx = df[df['SN'] == sn].index
            if not idx.empty:
                df.at[idx[0], 'AMOUNT_PAID'] += p_amt
                df.at[idx[0], 'OUTSTANDING_AMOUNT'] -= p_amt
                if df.at[idx[0], 'OUTSTANDING_AMOUNT'] <= 0: df.at[idx[0], 'STATUS'] = 'Cleared'
                save_data(df); st.success("Updated!"); st.rerun()
            else: st.error("Not found.")

elif choice == "📄 Client Report":
    st.title("📄 Client Statement")
    if not df.empty:
        search_list = df.apply(lambda x: f"{x['SN']} - {x['NAME']}", axis=1).tolist()
        sel = st.selectbox("Select Client", search_list)
        c = df[df['SN'] == sel.split(" - ")[0]].iloc[0]
        st.markdown(f'<div class="report-card"><h2 style="text-align:center;">ZOE CONSULTS</h2><hr><p><b>Client:</b> {c["NAME"]}<br><b>NIN:</b> {c["NIN"]}<br><b>Due:</b> {c["EXPECTED_DUE_DATE"]}</p></div>', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Principal", f"{c['LOAN_AMOUNT']:,.0f}")
        m2.metric("Paid", f"{c['AMOUNT_PAID']:,.0f}")
        m3.metric("Balance", f"{c['OUTSTANDING_AMOUNT']:,.0f}")
