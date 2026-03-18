import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import base64
import urllib.parse

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend IQ Pro", layout="wide")

st.markdown("""
<style>
    /* 1. THE ULTIMATE TOP RESET */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        margin-top: 0rem !important;
    }

    /* 2. REMOVE THE HEADER GAP */
    header {
        visibility: hidden;
        height: 0% !important;
    }

    /* 3. THE MAIN VIEWPORT */
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
    }

    /* 4. FIX TITLE POSITION */
    .main-title {
        color: #0f172a !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        margin-top: -20px !important;
        margin-bottom: 20px !important;
        letter-spacing: -1px;
    }
</style>
""", unsafe_allow_html=True)
# --- 2. DATA CONNECTION (WITH CACHING TO PREVENT QUOTA ERRORS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # We change ttl from "0" to 600 (10 minutes)
    # This stores the data in the app's memory so it doesn't keep pestering Google
    df = conn.read(worksheet="Borrowers", ttl=600).dropna(how="all")
    pay_df = conn.read(worksheet="Payments", ttl=600).dropna(how="all")
    return df, pay_df

df, pay_df = get_data()
# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown('<div style="margin-top: -30px;"></div>', unsafe_allow_html=True)
    
    # Logo Logic
    if 'custom_logo_b64' in st.session_state and st.session_state['custom_logo_b64']:
        st.markdown(f'<img src="data:image/png;base64,{st.session_state["custom_logo_b64"]}">', unsafe_allow_html=True)
    else:
        st.markdown('<div style="width:80px;height:80px;border-radius:50%;background-color:#1e293b;border:2px solid #00a8b5;margin:0 auto;display:flex;align-items:center;justify-content:center;font-size:30px;">💰</div>', unsafe_allow_html=True)
    
    st.markdown(f'<p class="admin-text"><b>Admin:</b> Evans Ahuura</p>', unsafe_allow_html=True)
    
    # WE USE SIMPLE NAMES HERE TO AVOID SYNTAX ERRORS
    menu_options = ["Overview", "Borrowers", "Repayments", "Calendar", "Collateral", "Ledger", "Settings"]
    page = st.radio("Menu", menu_options)
    
    st.write("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["password_correct"] = False
        st.rerun()

# --- 4. PAGE LOGIC (RESTORATION) ---

if page == "Overview":
    st.markdown('<div class="main-title">🛡️ Zoe Consults Executive Summary</div>', unsafe_allow_html=True)
    
    # DEBUG: This will show you if the app sees any data at all
    if df.empty:
        st.warning("🕵️ Your 'Borrowers' sheet appears to be empty. Please add a loan in the Borrowers tab.")
    else:
        # 📊 1. CALCULATE TOTALS
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        risk = total_p - total_c
        
        # 💎 2. PREMIUM TILES
        c1, c2, c3 = st.columns(3)
        c1.metric("Principal Issued", f"UGX {total_p:,.0f}")
        c2.metric("Total Collected", f"UGX {total_c:,.0f}")
        c3.metric("Outstanding Risk", f"UGX {risk:,.0f}")
            
        st.write("---")
        
        # 📈 3. THE RECOVERY CHART (Forced Mapping)
        st.subheader("Recovery Progress by Client")
        
        # We explicitly tell the chart which columns to use
        chart_data = df[['CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID']].set_index('CUSTOMER_NAME')
        st.bar_chart(chart_data, color=["#0ea5e9", "#10b981"])

elif page == "Borrowers":
    st.markdown('<div class="main-title">👥 Active Loan Registry</div>', unsafe_allow_html=True)
    
    if not df.empty:
        display_df = df.copy()
        
        # 1. THE MATH: Calculate the Interest Amount
        # Interest = (Principle * Rate) / 100
        display_df['INTEREST_AMT'] = (display_df['LOAN_AMOUNT'] * display_df['INTEREST_RATE']) / 100
        
        # 2. THE TOTAL DEBT: Principle + Interest - Amount Paid
        display_df['REAL_OUTSTANDING'] = (display_df['LOAN_AMOUNT'] + display_df['INTEREST_AMT']) - display_df['AMOUNT_PAID']
        
        # 3. DATE LOGIC
        display_df['ISSUED DATE'] = pd.to_datetime(display_df['DATE_ISSUED']).dt.date
        display_df['DUE DATE'] = (pd.to_datetime(display_df['DATE_ISSUED']) + pd.Timedelta(days=30)).dt.date
        
        # 4. RENAME FOR DISPLAY
        display_df = display_df.rename(columns={
            'CUSTOMER_NAME': 'NAME',
            'LOAN_AMOUNT': 'PRINCIPLE',
            'INTEREST_RATE': 'RATE %'
        })

        # 5. STATUS LOGIC (Using the new 'REAL_OUTSTANDING' balance)
        def get_status(row):
            if row['REAL_OUTSTANDING'] <= 0:
                return "✅ PAID"
            elif datetime.now().date() > row['DUE DATE']:
                return "🚩 OVERDUE"
            return "🔵 ACTIVE"
        
        display_df['Status'] = display_df.apply(get_status, axis=1)

        # 6. UPDATED TABLE COLUMNS
        cols_to_show = ['NAME', 'ISSUED DATE', 'PRINCIPLE', 'INTEREST_AMT', 'REAL_OUTSTANDING', 'DUE DATE', 'Status']
        
        st.dataframe(
            display_df[cols_to_show],
            column_config={
                "PRINCIPLE": st.column_config.NumberColumn(format="UGX %,d"),
                "INTEREST_AMT": st.column_config.NumberColumn("Interest Charged", format="UGX %,d"),
                "REAL_OUTSTANDING": st.column_config.NumberColumn("Outstanding Amount", format="UGX %,d"),
                "ISSUED DATE": st.column_config.DateColumn(),
                "DUE DATE": st.column_config.DateColumn(),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No records found.")

    # 4. NEW LOAN FORM (Updated to match these columns)
    with st.popover("➕ Register New Borrower"):
        with st.form("new_loan_v2"):
            st.markdown("### 📝 Enter Details")
            c_name = st.text_input("Full Name")
            c_amt = st.number_input("Principal (UGX)", min_value=0, step=50000)
            c_rate = st.number_input("Interest Rate (%)", value=10)
            c_date = st.date_input("Issuance Date", datetime.now())
            
            if st.form_submit_button("✅ Disburse & Sync", use_container_width=True):
                new_id = int(df['SN'].max() + 1) if not df.empty else 1
                # Save using the sheet's original header names
                new_row = pd.DataFrame([[new_id, c_name, c_amt, 0, c_amt, c_rate, str(c_date)]], 
                                     columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED'])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Borrowers", data=updated_df)
                st.success(f"Loan for {c_name} has been synced to Google Sheets!")
                st.rerun()

elif page == "Repayments":
    st.title("💰 Record a Payment")
    if not df.empty:
        with st.form("cloud_pay_form"):
            p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount Paid", min_value=0)
            p_ref = st.text_input("Receipt / Ref No.")
            if st.form_submit_button("Submit Payment"):
                # 1. Update Payments Sheet
                new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                updated_pay = pd.concat([pay_df, new_p], ignore_index=True)
                conn.update(worksheet="Payments", data=updated_pay)
                
                # 2. Update Borrowers Balance
                df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amt
                conn.update(worksheet="Borrowers", data=df)
                st.success("Payment Synced!")
                st.rerun()
    st.write("---")
    st.subheader("Recent Payment History")
    st.dataframe(pay_df.iloc[::-1], use_container_width=True)
elif page == "Calendar":
    st.title("📅 Due Dates")
    st.write("Calendar logic goes here.")

elif page == "Collateral":
    st.markdown('<div class="main-title">📑 Permanent Security Vault</div>', unsafe_allow_html=True)
    
    # --- 1. SAFE DATA LOAD ---
    try:
        collateral_df = conn.read(worksheet="Collateral", ttl="600").dropna(how="all")
    except Exception as e:
        st.error("Waiting for Google Sheets connection to reset... please wait 30 seconds.")
        collateral_df = pd.DataFrame(columns=['NAME', 'ASSET_TYPE', 'DESCRIPTION', 'VALUE', 'STATUS'])

    # --- 2. GET BORROWER NAMES SAFELY ---
    if not df.empty:
        # Determine which column name you are using (NAME or CUSTOMER_NAME)
        name_col = 'NAME' if 'NAME' in df.columns else 'CUSTOMER_NAME'
        borrower_list = df[name_col].unique().tolist()
    else:
        borrower_list = ["No Borrowers Found"]

    # --- 3. THE FORM (Now Unlocked) ---
    with st.expander("📥 Register & Save New Asset", expanded=True):
        with st.form("permanent_collateral"):
            # This dropdown will now at least show "No Borrowers Found" instead of being locked
            c_owner = st.selectbox("Assign to Borrower", options=borrower_list)
            
            c_type = st.selectbox("Asset Category", ["Logbook", "Land Title", "Electronics", "Other"])
            c_desc = st.text_area("Detailed Description (Serial Nos, Plate Nos)")
            c_val = st.number_input("Estimated Market Value (UGX)", min_value=0)
            
            # --- RECOVERY BUTTON ---
if st.button("🔄 Sync with Google Sheets Now"):
    st.cache_data.clear() # This kills the "empty memory"
    st.rerun()

# --- THE VAULT VIEW ---
st.write("---")
st.subheader("📋 Assets Currently Held")

# Make sure we check if the data exists before trying to show it
if not collateral_df.empty:
    # Filter for only held assets if you want
    st.dataframe(
        collateral_df,
        column_config={
            "VALUE": st.column_config.NumberColumn("Market Value", format="UGX %,d"),
            "STATUS": "Vault Status"
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("The vault data is still loading or empty. Click 'Sync' above if you have assets in your Google Sheet.")
    new_asset = pd.DataFrame([[c_owner, c_type, c_desc, c_val, "🔐 HELD"]], 
                                columns=['NAME', 'ASSET_TYPE', 'DESCRIPTION', 'VALUE', 'STATUS'])
                    updated_collateral = pd.concat([collateral_df, new_asset], ignore_index=True)
                    conn.update(worksheet="Collateral", data=updated_collateral)
                    st.success("Asset Locked!")
                    st.rerun()
    
    # --- 3. THE "RELEASE ASSET" ACTION ---
st.subheader("🔓 Asset Release Control")
held_assets = collateral_df[collateral_df['STATUS'] == "🔐 HELD"]

if not held_assets.empty:
    with st.popover("Select Asset to Dismiss"):
        st.write("Confirm which item you are returning to the client:")
        
        # We use a unique key to prevent any "Duplicate Widget" errors
        target_asset = st.selectbox(
            "Which item are you returning?", 
            options=held_assets['DESCRIPTION'].unique(),
            key="dismiss_selector"
        )
        
        # CHANGE: We use st.button instead of st.form_submit_button
        if st.button("✅ Confirm Return to Client", use_container_width=True):
            # 1. Update the status in our local copy
            collateral_df.loc[collateral_df['DESCRIPTION'] == target_asset, 'STATUS'] = f"🔓 RETURNED ({datetime.now().date()})"
            
            # 2. Push the update to Google Sheets
            conn.update(worksheet="Collateral", data=collateral_df)
            
            # 3. Success feedback
            st.balloons()
            st.success(f"Asset '{target_asset}' has been dismissed!")
            st.rerun()
    st.info("No assets are currently being held in the vault.")
    
elif page == "Ledger":
    st.title("📄 Client Ledger")
    st.write("Ledger logic goes here.")

elif page == "Settings":
    st.title("⚙️ Settings")
    st.write("Settings logic goes here.")
