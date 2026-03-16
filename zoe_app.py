import streamlit as st
import pandas as pd
import datetime
import os

# --- 1. APP CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ", page_icon="🏦", layout="wide")

# Custom CSS for a "Banking" look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    [data-testid="stSidebar"] { background-color: #1e293b; color: white; }
    </style>
    """, unsafe_allow_html=True)

FILE_NAME = 'zoe_consults_loans.csv'

# --- 2. LOGIC (Keeping your perfect engine) ---
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
    return pd.DataFrame(columns=['Customer_ID', 'Name', 'Principal_UGX', 'Annual_Rate', 'Start_Date', 'Last_Payment_Date', 'Status'])

def save_data(df):
    df.to_csv(FILE_NAME, index=False)

def calculate_live_balance(row):
    if row['Status'] == 'Paid Off': return 0.0
    today = datetime.datetime.now()
    months_diff = (today.year - row['Start_Date'].year) * 12 + (today.month - row['Start_Date'].month)
    balance = row['Principal_UGX'] * (1 + (row['Annual_Rate'] / 12)) ** max(0, months_diff)
    return round(balance, 0)

# --- 3. LOGIN GATE ---
if "password_correct" not in st.session_state:
    st.title("🏦 ZoeLend IQ")
    st.subheader("Professional Loan Management for Zoe Consults")
    with st.container():
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Access Dashboard"):
            if u == "admin" and p == "zoe2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Access Denied.")
    st.stop()

# --- 4. MAIN APP ---
df = load_data()
if not df.empty:
    df['Status'] = df.apply(lambda r: 'Dormant' if (datetime.datetime.now() - pd.to_datetime(r['Last_Payment_Date'])).days > 60 else r['Status'], axis=1)
    df['Current_Balance'] = df.apply(calculate_live_balance, axis=1)

# SIDEBAR BEAUTIFICATION
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135706.png", width=100)
    st.title("Zoe Consults")
    st.markdown("---")
    choice = st.radio("Menu", ["📊 Daily Report", "👤 New Customer", "💰 Record Payment", "✉️ Letters", "⚙️ Help"])
    st.markdown("---")
    st.caption("Version 2.0 | Kampala, Uganda")

if choice == "📊 Daily Report":
    st.title("📊 Financial Portfolio Overview")
    
    if df.empty:
        st.info("Your portfolio is currently empty.")
    else:
        # VISUAL METRICS
        c1, c2, c3 = st.columns(3)
        total_p = df['Principal_UGX'].sum()
        total_b = df['Current_Balance'].sum()
        growth = ((total_b - total_p) / total_p * 100) if total_p > 0 else 0
        
        c1.metric("Total Principal", f"UGX {total_p:,.0f}")
        c2.metric("Portfolio Value", f"UGX {total_b:,.0f}", f"{growth:.1f}% interest")
        c3.metric("Active Loans", len(df[df['Status'] == 'Active']))

        st.markdown("---")
        search = st.text_input("🔍 Quick Search Registry", placeholder="Enter customer name...")
        display_df = df[df['Name'].str.contains(search, case=False)] if search else df
        
        # PRO TABLE CONFIGURATION
        st.dataframe(
            display_df,
            column_config={
                "Principal_UGX": st.column_config.NumberColumn("Principal", format="UGX %d"),
                "Current_Balance": st.column_config.NumberColumn("Live Balance", format="UGX %d"),
                "Annual_Rate": st.column_config.NumberColumn("Rate", format="%.1f%%"),
                "Status": st.column_config.SelectboxColumn("Status", options=["Active", "Dormant", "Paid Off"])
            },
            hide_index=True,
            use_container_width=True
        )
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Export Master Ledger", data=csv, file_name="Zoe_Consults_Master.csv", mime="text/csv")

elif choice == "👤 New Customer":
    st.title("👤 Customer Onboarding")
    with st.expander("Click to open Registration Form", expanded=True):
        with st.form("reg_form", clear_on_submit=True):
            n = st.text_input("Full Name")
            a = st.number_input("Loan Amount (UGX)", min_value=1000, step=50000)
            r = st.slider("Annual Interest Rate (%)", 0, 300, 25) / 100
            if st.form_submit_button("✅ Register & Issue Loan"):
                new_id = (df['Customer_ID'].max() + 1) if not df.empty else 101
                now = datetime.datetime.now()
                new_row = pd.DataFrame([{'Customer_ID': new_id, 'Name': n, 'Principal_UGX': a, 'Annual_Rate': r, 'Start_Date': now, 'Last_Payment_Date': now, 'Status': 'Active'}])
                save_data(pd.concat([df, new_row], ignore_index=True))
                st.success(f"Loan issued for {n}!")

elif choice == "💰 Record Payment":
    st.title("💰 Payment Gateway")
    col1, col2 = st.columns(2)
    with col1:
        cid = st.number_input("Customer ID", min_value=101)
        p_amt = st.number_input("Amount Received (UGX)", min_value=1000, step=10000)
        if st.button("🚀 Confirm Payment"):
            idx = df[df['Customer_ID'] == cid].index
            if not idx.empty:
                df.at[idx[0], 'Principal_UGX'] -= p_amt
                df.at[idx[0], 'Last_Payment_Date'] = datetime.datetime.now()
                save_data(df)
                st.success("Payment confirmed and balance updated!")
                st.rerun()
            else: st.error("ID not found.")

elif choice == "✉️ Letters":
    st.title("✉️ Smart Letter Generator")
    if not df.empty:
        name = st.selectbox("Select Customer", df['Name'].unique())
        row = df[df['Name'] == name].iloc[0]
        st.info(f"Generating letter for {name} (ID: {row['Customer_ID']})")
        letter = f"""
        ZOE CONSULTS
        Kampala, Uganda
        --------------------------
        LOAN SUMMARY
        Customer: {row['Name']}
        Current Balance: UGX {row['Current_Balance']:,.0f}
        Interest Rate: {row['Annual_Rate']*100}% p.a.
        --------------------------
        Please note that interest compounds monthly.
        """
        st.text_area("Agreement Preview", letter, height=250)
