import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import base64
import urllib.parse
from datetime import datetime, timedelta  # Ensure ', timedelta' is added here!
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
with st.sidebar:
    # --- 1. CENTERED CIRCULAR LOGO ---
    # We use columns to perfectly center the Streamlit image widget
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True)
        except:
            st.markdown("🌐") # Fallback icon if logo.png isn't found

    # --- 2. CENTERED BRAND NAME ---
    st.markdown("""
        <div style="text-align: center; margin-top: 10px;">
            <h2 style="color: #1E3A8A; margin-bottom: 0; font-size: 1.4rem;">ZOE</h2>
            <p style="color: #64748B; font-size: 0.7rem; font-weight: bold; letter-spacing: 3px; margin-top: -5px;">CONSULTS</p>
        </div>
        <hr style="margin: 15px 0;">
    """, unsafe_allow_html=True)

    # --- 3. THE CENTER-ALIGN MAGIC (CSS) ---
    st.markdown("""
        <style>
            /* This forces the radio group and its labels to center */
            [data-testid="stSidebarNav"] {text-align: center;}
            [data-testid="stWidgetLabel"] {text-align: center; width: 100%;}
            div[role="radiogroup"] {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                width: 100%;
            }
            div[role="radiogroup"] > label {
                justify-content: center;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. NAVIGATION ---
    st.markdown("<p style='text-align: center; font-weight: bold; color: #1E3A8A;'>NAVIGATION</p>", unsafe_allow_html=True)
    
    page = st.radio("Menu Selection", 
                    ["Overview", "Borrowers", "Repayments", "Calendar", "Collateral", "Ledger", "Settings"],
                    label_visibility="collapsed")
    
    st.markdown("---")
    
    if st.button("🚪 Secure Logout", use_container_width=True):
        st.session_state.clear()
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
    st.markdown('<div class="main-title">🗓️ Collection & Due Date Calendar</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. Use the exact column name we found
        date_col = "DUE " if "DUE " in df.columns else "DUE"

        if date_col in df.columns:
            # 2. SETUP DATES (Crucial Fix here)
            # We convert everything to a Timestamp for a fair comparison
            today = pd.Timestamp(datetime.now().date())
            this_week_end = today + pd.Timedelta(days=7)
            
            # Convert the Google Sheet column to Timestamps, ignoring errors
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            # Filter out empty dates
            active_loans = df.dropna(subset=[date_col])

            # 3. THE URGENT TABS
            tab1, tab2, tab3 = st.tabs(["🚨 Overdue", "📅 Due This Week", "✅ All Collections"])

            with tab1:
                # We use ( ) around each condition for safety
                overdue = active_loans[(active_loans[date_col] < today) & (active_loans['OUTSTANDING_AMOUNT'] > 0)]
                if not overdue.empty:
                    st.error(f"⚠️ {len(overdue)} Loans are past due!")
                    # Convert back to simple date just for display in the table
                    display_overdue = overdue.copy()
                    display_overdue[date_col] = display_overdue[date_col].dt.date
                    st.dataframe(display_overdue[['CUSTOMER_NAME', date_col, 'OUTSTANDING_AMOUNT']], 
                                 column_config={"OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d")},
                                 use_container_width=True, hide_index=True)
                else:
                    st.success("No overdue loans!")

            with tab2:
                this_week = active_loans[(active_loans[date_col] >= today) & (active_loans[date_col] <= this_week_end)]
                if not this_week.empty:
                    display_week = this_week.copy()
                    display_week[date_col] = display_week[date_col].dt.date
                    st.info(f"You have {len(this_week)} collections due this week.")
                    st.dataframe(display_week[['CUSTOMER_NAME', date_col, 'OUTSTANDING_AMOUNT']], use_container_width=True, hide_index=True)
                else:
                    st.write("No collections due this week.")
            
            with tab3:
                all_display = active_loans.copy()
                all_display[date_col] = all_display[date_col].dt.date
                st.dataframe(all_display[['CUSTOMER_NAME', date_col, 'OUTSTANDING_AMOUNT']].sort_values(by=date_col), use_container_width=True, hide_index=True)
        else:
            st.warning("Could not find the 'DUE ' column.")
    else:
        st.info("No borrower data found.")
        
        # --- 1. SAFE DATA LOAD ---
        try:
            collateral_df = conn.read(worksheet="Collateral", ttl="600").dropna(how="all")
        except Exception as e:
            st.error("Waiting for Google Sheets connection to reset... please wait 30 seconds.")
            collateral_df = pd.DataFrame(columns=['NAME', 'ASSET_TYPE', 'DESCRIPTION', 'VALUE', 'STATUS'])

        # --- 2. GET BORROWER NAMES SAFELY ---
        if not df.empty:
            name_col = 'NAME' if 'NAME' in df.columns else 'CUSTOMER_NAME'
            borrower_list = df[name_col].unique().tolist()
        else:
            borrower_list = ["No Borrowers Found"]

        # --- 3. THE REGISTRATION FORM ---
        with st.expander("📥 Register & Save New Asset", expanded=True):
            with st.form("permanent_collateral"):
                c_owner = st.selectbox("Assign to Borrower", options=borrower_list)
                c_type = st.selectbox("Asset Category", ["Logbook", "Land Title", "Electronics", "Other"])
                c_desc = st.text_area("Detailed Description (Serial Nos, Plate Nos)")
                c_val = st.number_input("Estimated Market Value (UGX)", min_value=0)
                submitted = st.form_submit_button("🔒 Secure Asset to Cloud", use_container_width=True)
                
                if submitted:
                    new_asset = pd.DataFrame([[c_owner, c_type, c_desc, c_val, "🔐 HELD"]], 
                                           columns=['NAME', 'ASSET_TYPE', 'DESCRIPTION', 'VALUE', 'STATUS'])
                    updated_collateral = pd.concat([collateral_df, new_asset], ignore_index=True)
                    conn.update(worksheet="Collateral", data=updated_collateral)
                    st.success("Asset Locked!")
                    st.rerun()

        # --- 4. THE VAULT VIEW (Now correctly inside the Collateral room) ---
        st.write("---")
        st.subheader("📋 Assets Currently Held")
        if not collateral_df.empty:
            st.dataframe(
                collateral_df,
                column_config={
                    "VALUE": st.column_config.NumberColumn("Market Value", format="UGX %,d"),
                    "STATUS": "Vault Status"
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("The vault is currently empty.")

        # --- 5. ASSET RELEASE CONTROL (Now correctly inside the Collateral room) ---
        st.subheader("🔓 Asset Release Control")
        held_assets = collateral_df[collateral_df['STATUS'] == "🔐 HELD"]
        if not held_assets.empty:
            with st.popover("Select Asset to Dismiss"):
                target_asset = st.selectbox("Item to return:", options=held_assets['DESCRIPTION'].unique(), key="dismiss_selector")
                if st.button("✅ Confirm Return to Client", use_container_width=True):
                    collateral_df.loc[collateral_df['DESCRIPTION'] == target_asset, 'STATUS'] = f"🔓 RETURNED ({datetime.now().date()})"
                    conn.update(worksheet="Collateral", data=collateral_df)
                    st.balloons()
                    st.rerun()

elif page == "Ledger":
    st.markdown('<div class="main-title">📄 Client Statement of Account</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. Select Client
        target = st.selectbox("Select Client for Report", options=df['CUSTOMER_NAME'].unique())
        client_info = df[df['CUSTOMER_NAME'] == target].iloc[0]
        client_pay = pay_df[pay_df['CUSTOMER_NAME'] == target].sort_values(by='DATE', ascending=False)
        
        # 2. Math Calculations
        int_amt = (client_info['LOAN_AMOUNT'] * client_info['INTEREST_RATE']) / 100
        total_due = client_info['LOAN_AMOUNT'] + int_amt
        bal = total_due - client_info['AMOUNT_PAID']

        # 3. Financial Metrics (The 3 Columns)
        st.subheader(f"Financial Status: {target}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Original Principal", f"UGX {client_info['LOAN_AMOUNT']:,.0f}")
        c2.metric("Total Paid", f"UGX {client_info['AMOUNT_PAID']:,.0f}")
        c3.metric("Outstanding Balance", f"UGX {bal:,.0f}", delta="Reduces as they pay", delta_color="inverse")
        
        st.write("---")
       # --- STYLED WHATSAPP BUTTON ---
        st.write("---")
        
        # 1. Prepare the Message (Same as before)
        message = (
            f"Hello%20{target},%20this%20is%20Zoe%20Consults.%0A%0A"
            f"Your%20Loan%20Statement%20Update:%0A"
            f"•%20Principal:%20UGX%20{client_info['LOAN_AMOUNT']:,.0f}%0A"
            f"•%20Total%20Paid:%20UGX%20{client_info['AMOUNT_PAID']:,.0f}%0A"
            f"•%20Current%20Balance:%20UGX%20{bal:,.0f}%0A%0A"
            f"Please%20reach%20out%20if%20you%20have%20any%20questions."
        )
        wa_url = f"https://wa.me/?text={message}"

        # 2. The Green, Smaller Button using HTML/CSS
        st.markdown(f"""
            <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                <div style="
                    background-color: #25D366;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 25px;
                    text-align: center;
                    font-weight: bold;
                    width: fit-content;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
                ">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="20px">
                    Send to WhatsApp
                </div>
            </a>
        """, unsafe_allow_html=True)
        st.write("") # Just a little spacing at the bottom
        # 4. THE RETURNED TABLE (Detailed Transactions)
        st.write("🔍 **Transaction History**")
        if not client_pay.empty:
            st.dataframe(
                client_pay[['DATE', 'AMOUNT_PAID', 'REF']], # We hide CUSTOMER_NAME here to save space
                column_config={
                    "DATE": "Payment Date",
                    "AMOUNT_PAID": st.column_config.NumberColumn("Amount Received", format="UGX %,d"),
                    "REF": "Receipt/Ref #"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(f"No payments recorded for {target} yet.")
            
    else:
        st.info("No borrowers found. Please add data in the Borrowers tab.")
    
elif page == "Settings":
    st.title("⚙️ Settings")
    st.write("Settings logic goes here.")
