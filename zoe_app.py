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

def get_all_data():
    b_df = conn.read(worksheet="Borrowers", ttl="600").dropna(how="all")
    p_df = conn.read(worksheet="Payments", ttl="600").dropna(how="all")
    # Add this line here so it's loaded globally!
    c_df = conn.read(worksheet="Collateral", ttl="600").dropna(how="all")
    return b_df, p_df, c_df

df, pay_df, collateral_df = get_all_data()
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
            # These 4 lines are indented to be INSIDE the form
            c_owner = st.selectbox("Assign to Borrower", options=borrower_list)
            c_type = st.selectbox("Asset Category", ["Logbook", "Land Title", "Electronics", "Other"])
            c_desc = st.text_area("Detailed Description (Serial Nos, Plate Nos)")
            c_val = st.number_input("Estimated Market Value (UGX)", min_value=0)
            
            # This button is also indented to be the "Seal" of the form
            submitted = st.form_submit_button("🔒 Secure Asset to Cloud", use_container_width=True)
            
            if submitted:
                # This logic is indented even further to be inside the 'if'
                new_asset = pd.DataFrame([[c_owner, c_type, c_desc, c_val, "🔐 HELD"]], 
                                       columns=['NAME', 'ASSET_TYPE', 'DESCRIPTION', 'VALUE', 'STATUS'])
                updated_collateral = pd.concat([collateral_df, new_asset], ignore_index=True)
                conn.update(worksheet="Collateral", data=updated_collateral)
                st.success("Asset Locked!")
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
    st.markdown('<div class="main-title">📄 Client Statement of Account</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. SELECT CLIENT (The Trigger for the Report)
        name_options = df['NAME'].unique() if 'NAME' in df.columns else df['CUSTOMER_NAME'].unique()
        target = st.selectbox("Select Client for Report", options=name_options)
        
        # Pull specific client data
        client_info = df[df['CUSTOMER_NAME'] == target].iloc[0]
        client_payments = pay_df[pay_df['CUSTOMER_NAME'] == target].sort_values(by='DATE', ascending=False)
        
        # Calculate Finance Specifics (Same 2.8% Logic)
        interest_amt = (client_info['LOAN_AMOUNT'] * client_info['INTEREST_RATE']) / 100
        total_due = client_info['LOAN_AMOUNT'] + interest_amt
        balance = total_due - client_info['AMOUNT_PAID']

        # --- 📝 THE OFFICIAL HEADER BOX ---
        st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 25px; border-radius: 15px; border: 1px solid #e2e8f0; color: #1e293b; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="color: #0f172a; margin: 0;">Zoe Consults</h2>
                    <span style="background: {'#dcfce7' if balance <= 0 else '#fee2e2'}; color: {'#166534' if balance <= 0 else '#991b1b'}; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 0.8rem;">
                        {'✅ CLEARED' if balance <= 0 else '🚩 ACTIVE DEBT'}
                    </span>
                </div>
                <p style="color: #64748b; margin-top: 5px;">Official Statement | Date: {datetime.now().strftime('%d %B %Y')}</p>
                <hr style="border: 0.5px solid #cbd5e1; margin: 15px 0;">
                <p style="margin: 0; color: #94a3b8; font-size: 0.8rem;">PREPARED FOR</p>
                <p style="font-weight: bold; font-size: 1.2rem; margin: 0;">{target}</p>
            </div>
        """, unsafe_allow_html=True)

        # 2. THE SUMMARY TILES
        c1, c2, c3 = st.columns(3)
        c1.metric("Principal + Interest", f"UGX {total_due:,.0f}")
        c2.metric("Total Paid to Date", f"UGX {client_info['AMOUNT_PAID']:,.0f}")
        c3.metric("CURRENT BALANCE", f"UGX {balance:,.0f}")

        # 3. THE BREAKDOWN TABS
        st.write("---")
        t1, t2 = st.tabs(["💰 Payment History", "📑 Security Assets"])
        
        with t1:
            if not client_payments.empty:
                st.dataframe(
                    client_payments[['DATE', 'AMOUNT_PAID', 'REF']],
                    column_config={
                        "AMOUNT_PAID": st.column_config.NumberColumn("Amount (UGX)", format="UGX %,d"),
                        "DATE": "Date Received",
                        "REF": "Receipt #"
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("No payments recorded yet.")

        with t2:
            try:
                # We filter the global collateral_df we loaded at the top
                client_assets = collateral_df[collateral_df['NAME'] == target]
                if not client_assets.empty:
                    st.dataframe(client_assets[['ASSET_TYPE', 'DESCRIPTION', 'STATUS']], use_container_width=True, hide_index=True)
                else:
                    st.info("No security assets registered for this client.")
            except:
                st.error("Could not load collateral data for this report.")

    else:
        st.warning("⚠️ No borrower data found. Please add a borrower first.")
elif page == "Settings":
    st.title("⚙️ Settings")
    st.write("Settings logic goes here.")
