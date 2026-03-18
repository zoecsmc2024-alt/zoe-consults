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
    c_df = conn.read(worksheet="Collateral", ttl="600").dropna(how="all")
    # New Settings Sheet: Should have columns 'Property' and 'Value'
    try:
        s_df = conn.read(worksheet="Settings", ttl="600").dropna(how="all")
    except:
        # Fallback if sheet doesn't exist yet
        s_df = pd.DataFrame([["Company Name", "ZOE"], ["Tagline", "CONSULTS"], ["Logo Emoji", "🛡️"]], 
                            columns=["Property", "Value"])
    return b_df, p_df, c_df, s_df

df, pay_df, collateral_df, settings_df = get_all_data()

# Helper to get setting value
def get_setting(prop, default):
    try:
        return settings_df.loc[settings_df['Property'] == prop, 'Value'].values[0]
    except:
        return default
from streamlit_option_menu import option_menu # Add this to your imports at the top!
# Get dynamic values
brand_name = get_setting("Company Name", "ADMIN")
brand_tagline = get_setting("Tagline", "ZOE CONSULTS SMC LTD")
brand_logo_type = get_setting("Logo Type", "Emoji") # 'Emoji' or 'URL'
brand_logo_val = get_setting("Logo Value", "🛡️")

with st.sidebar:
    st.markdown("<div style='text-align: center; padding-bottom: 10px;'>", unsafe_allow_html=True)
    
    # --- SAFE LOGO LOGIC ---
    show_emoji_fallback = True
    
    # Check if we have a valid URL string that isn't empty or 'nan'
    if brand_logo_type == "URL" and isinstance(brand_logo_val, str) and len(brand_logo_val) > 5:
        try:
            # We use a container to catch errors if the URL is not a real image
            st.image(brand_logo_val, use_container_width=True)
            show_emoji_fallback = False # If it worked, don't show the emoji
        except Exception:
            show_emoji_fallback = True # If the link is broken, use emoji
            
    if show_emoji_fallback:
        # Professional fallback icon
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
                        width: 70px; height: 70px; border-radius: 18px; 
                        display: flex; align-items: center; justify-content: center; 
                        margin: 0 auto 15px auto; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <span style="font-size: 35px; color: white;">{brand_logo_val if brand_logo_type == "Emoji" else "🛡️"}</span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
            <h1 style="color: #0f172a; font-size: 1.5rem; font-weight: 800; margin: 0;">{brand_name}</h1>
            <p style="color: #64748b; font-size: 0.7rem; font-weight: 700; letter-spacing: 3px; margin: 0;">{brand_tagline}</p>
        </div>
        <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 10px 0 20px 0;">
    """, unsafe_allow_html=True)
    # ... rest of your option_menu ...

    # 2. THE OPTION MENU (Modern Styling)
    # Using 'option_menu' for a more mobile-responsive, centered feel
    page = option_menu(
        menu_title=None,
        options=["Overview", "Borrowers", "Repayments", "Calendar", "Collateral", "Ledger", "Settings"],
        icons=["grid-1x2", "people", "wallet2", "calendar-check", "safe2", "file-earmark-medical", "sliders"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#64748b", "font-size": "18px"}, 
            "nav-link": {
                "font-size": "14px", 
                "text-align": "left", 
                "margin": "5px 0px", 
                "color": "#475569",
                "font-family": "'Inter', sans-serif",
                "border-radius": "8px"
            },
            "nav-link-selected": {
                "background-color": "#1e3a8a", 
                "color": "white",
                "font-weight": "600"
            },
        }
    )

    # 3. SIDEBAR FOOTER & LOGOUT
    st.markdown("<div style='flex-grow: 1;'></div>", unsafe_allow_html=True) # Pushes logout to bottom
    st.write("---")
    
    # Modern Logout Button
    if st.button("🚪 Terminate Session", use_container_width=True):
        st.session_state.clear()
        st.success("Securely Logged Out")
        st.rerun()

    # App Version Info
    st.markdown("""
        <div style="text-align: center; color: #94a3b8; font-size: 0.7rem; padding-top: 10px;">
            v2.4.0 • Enterprise Edition<br>
            Secure Cloud Sync Active
        </div>
    """, unsafe_allow_html=True)
# --- 4. PAGE LOGIC (RESTORATION) ---

if page == "Overview":
    st.markdown('<div class="main-title">🛡️ Zoe Consults Executive Summary</div>', unsafe_allow_html=True)
    
    if df.empty:
        st.warning("🕵️ Your 'Borrowers' sheet appears to be empty.")
    else:
        # 1. CALCULATIONS
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        # Including Interest in the risk calculation
        df['INTEREST_AMT'] = (df['LOAN_AMOUNT'] * df['INTEREST_RATE']) / 100
        total_expected = total_p + df['INTEREST_AMT'].sum()
        risk = total_expected - total_c
        recovery_rate = (total_c / total_expected) * 100 if total_expected > 0 else 0

        # 2. PREMIUM KPI TILES (Custom HTML)
        st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                <div style="background: linear-gradient(135.47deg, #1E3A8A 0%, #3B82F6 100%); padding: 20px; border-radius: 15px; color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                    <p style="margin: 0; font-size: 0.8rem; opacity: 0.8; text-transform: uppercase; font-weight: 600;">Principal Issued</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem;">UGX {total_p:,.0f}</h2>
                </div>
                <div style="background: white; padding: 20px; border-radius: 15px; color: #1E293B; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                    <p style="margin: 0; font-size: 0.8rem; color: #64748B; text-transform: uppercase; font-weight: 600;">Total Collected</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem; color: #10B981;">UGX {total_c:,.0f}</h2>
                </div>
                <div style="background: white; padding: 20px; border-radius: 15px; color: #1E293B; border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                    <p style="margin: 0; font-size: 0.8rem; color: #64748B; text-transform: uppercase; font-weight: 600;">Outstanding Risk</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem; color: #EF4444;">UGX {risk:,.0f}</h2>
                </div>
                <div style="background: #F8FAFC; padding: 20px; border-radius: 15px; color: #1E293B; border: 1px dashed #CBD5E1;">
                    <p style="margin: 0; font-size: 0.8rem; color: #64748B; text-transform: uppercase; font-weight: 600;">Recovery Rate</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem; color: #1E3A8A;">{recovery_rate:.1f}%</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.write("---")
        
        # 3. ENHANCED RECOVERY CHART
        st.subheader("📊 Portfolio Performance by Client")
        
        # Prepare Data: Show Amount Paid vs Total Debt (Principal + Interest)
        df_chart = df.copy()
        df_chart['TOTAL_DEBT'] = df_chart['LOAN_AMOUNT'] + (df_chart['LOAN_AMOUNT'] * df_chart['INTEREST_RATE'] / 100)
        
        chart_data = df_chart[['CUSTOMER_NAME', 'TOTAL_DEBT', 'AMOUNT_PAID']].set_index('CUSTOMER_NAME')
        
        # Streamlit Bar Chart with specific colors
        st.bar_chart(
            chart_data, 
            color=["#CBD5E1", "#1E3A8A"], # Light gray for total, Deep Blue for paid
            height=400,
            use_container_width=True
        )
        
        st.markdown("""
            <div style="display: flex; gap: 20px; font-size: 0.8rem; color: #64748B; justify-content: center;">
                <div style="display: flex; align-items: center; gap: 5px;">
                    <div style="width: 12px; height: 12px; background: #CBD5E1; border-radius: 2px;"></div> Total Debt (Incl. Interest)
                </div>
                <div style="display: flex; align-items: center; gap: 5px;">
                    <div style="width: 12px; height: 12px; background: #1E3A8A; border-radius: 2px;"></div> Amount Recovered
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 4. RECENT ACTIVITY (Mini Ledger)
        st.write("")
        st.write("")
        st.subheader("🕒 Recent Payments")
        if not pay_df.empty:
            st.dataframe(
                pay_df.sort_values(by='DATE', ascending=False).head(5),
                column_config={
                    "AMOUNT_PAID": st.column_config.NumberColumn("Amount", format="UGX %,d"),
                    "DATE": "Date"
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No payments recorded yet.")

elif page == "Borrowers":
    st.markdown('<div class="main-title">👥 Active Loan Registry</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # --- 1. DATA PROCESSING ---
        display_df = df.copy()
        # Ensure numeric types for calculation
        display_df['LOAN_AMOUNT'] = pd.to_numeric(display_df['LOAN_AMOUNT'], errors='coerce')
        display_df['INTEREST_RATE'] = pd.to_numeric(display_df['INTEREST_RATE'], errors='coerce')
        display_df['AMOUNT_PAID'] = pd.to_numeric(display_df['AMOUNT_PAID'], errors='coerce')
        
        display_df['INTEREST_AMT'] = (display_df['LOAN_AMOUNT'] * display_df['INTEREST_RATE']) / 100
        display_df['TOTAL_EXPECTED'] = display_df['LOAN_AMOUNT'] + display_df['INTEREST_AMT']
        display_df['REAL_OUTSTANDING'] = display_df['TOTAL_EXPECTED'] - display_df['AMOUNT_PAID']
        
        display_df['ISSUED_DT'] = pd.to_datetime(display_df['DATE_ISSUED']).dt.date
        display_df['DUE_DT'] = (pd.to_datetime(display_df['DATE_ISSUED']) + pd.Timedelta(days=30)).dt.date
        
        def get_status(row):
            if row['REAL_OUTSTANDING'] <= 0: return "✅ SETTLED"
            if datetime.now().date() > row['DUE_DT']: return "🚩 OVERDUE"
            return "🔵 ACTIVE"
        display_df['Status'] = display_df.apply(get_status, axis=1)

        # --- 2. THE TABLE (WITH INTEREST RATE RESTORED) ---
        st.dataframe(
            display_df[['CUSTOMER_NAME', 'ISSUED_DT', 'LOAN_AMOUNT', 'INTEREST_RATE', 'INTEREST_AMT', 'AMOUNT_PAID', 'REAL_OUTSTANDING', 'Status']],
            column_config={
                "CUSTOMER_NAME": "Client Name",
                "ISSUED_DT": "Issued",
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                "INTEREST_RATE": st.column_config.NumberColumn("Rate (%)", format="%d%%"),
                "INTEREST_AMT": st.column_config.NumberColumn("Interest (UGX)", format="%,d"),
                "AMOUNT_PAID": st.column_config.ProgressColumn(
                    "Recovery Progress",
                    format="UGX %,d",
                    min_value=0,
                    max_value=int(display_df['TOTAL_EXPECTED'].max()),
                ),
                "REAL_OUTSTANDING": st.column_config.NumberColumn("Balance", format="UGX %,d"),
                "Status": "Status"
            },
            use_container_width=True, hide_index=True
        )

        # --- 3. RESTORED EDIT/DELETE CONTROLS ---
        st.write("---")
        with st.expander("🛠️ Manage Records (Edit/Delete)"):
            target_client = st.selectbox("Select Client to Manage:", options=df['CUSTOMER_NAME'].unique())
            client_row = df[df['CUSTOMER_NAME'] == target_client].iloc[0]

            col_edit, col_del = st.columns([2, 1])

            with col_edit:
                with st.form(f"edit_form_{target_client}"):
                    st.markdown(f"**Editing Profile:** {target_client}")
                    new_name = st.text_input("Correct Name", value=client_row['CUSTOMER_NAME'])
                    new_loan = st.number_input("Principal (UGX)", value=int(client_row['LOAN_AMOUNT']), step=50000)
                    new_rate = st.number_input("Interest Rate (%)", value=int(client_row['INTEREST_RATE']))
                    
                    if st.form_submit_button("💾 Save Changes", use_container_width=True):
                        df.loc[df['CUSTOMER_NAME'] == target_client, 'CUSTOMER_NAME'] = new_name
                        df.loc[df['CUSTOMER_NAME'] == new_name, 'LOAN_AMOUNT'] = new_loan
                        df.loc[df['CUSTOMER_NAME'] == new_name, 'INTEREST_RATE'] = new_rate
                        # Recalculate sheet balance
                        new_int = (new_loan * new_rate) / 100
                        df.loc[df['CUSTOMER_NAME'] == new_name, 'OUTSTANDING_AMOUNT'] = (new_loan + new_int) - client_row['AMOUNT_PAID']
                        
                        conn.update(worksheet="Borrowers", data=df)
                        st.success("Record updated!")
                        st.rerun()

            with col_del:
                st.markdown("**Danger Zone**")
                if st.button(f"🗑️ Delete {target_client}", use_container_width=True, type="primary"):
                    # Filtering out the deleted row
                    updated_df = df[df['CUSTOMER_NAME'] != target_client]
                    conn.update(worksheet="Borrowers", data=updated_df)
                    st.warning("Record deleted.")
                    st.rerun()
    else:
        st.info("No records found.")

    # --- 4. NEW REGISTRATION ---
    st.write("")
    with st.popover("➕ Register New Loan", use_container_width=True):
        with st.form("new_loan_final", clear_on_submit=True):
            f_name = st.text_input("Borrower Name")
            f_amt = st.number_input("Principal (UGX)", min_value=0, step=50000)
            f_rate = st.number_input("Interest Rate (%)", value=10)
            f_date = st.date_input("Date Issued", datetime.now())
            
            if st.form_submit_button("✅ Disburse & Sync"):
                if f_name and f_amt > 0:
                    new_id = int(df['SN'].max() + 1) if not df.empty else 1
                    # Ensure interest is included in the stored balance
                    starting_bal = f_amt + (f_amt * f_rate / 100)
                    new_row = pd.DataFrame([[new_id, f_name, f_amt, 0, starting_bal, f_rate, str(f_date)]], 
                                         columns=['SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED'])
                    conn.update(worksheet="Borrowers", data=pd.concat([df, new_row], ignore_index=True))
                    st.success("Loan Created!")
                    st.rerun()

elif page == "Repayments":
    st.markdown('<div class="main-title">💰 Payment Processing</div>', unsafe_allow_html=True)
    
    if not df.empty:
        with st.form("repayment_form_final"):
            p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount Paid", min_value=0)
            p_ref = st.text_input("Receipt Reference")
            
            if st.form_submit_button("🚀 Post Payment"):
                if p_amt > 0:
                    # Update Payments Sheet
                    new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], 
                                       columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                    conn.update(worksheet="Payments", data=pd.concat([pay_df, new_p], ignore_index=True))
                    
                    # Deduct from Borrowers Worksheet balance
                    df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                    df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amt
                    conn.update(worksheet="Borrowers", data=df)
                    st.success("Payment Received!")
                    st.rerun()

        st.write("---")
        st.subheader("📋 Recent History")
        st.dataframe(
            pay_df.iloc[::-1],
            column_config={
                "AMOUNT_PAID": st.column_config.NumberColumn("Amount", format="UGX %,d"),
                "DATE": "Date"
            },
            use_container_width=True, hide_index=True
        )

elif page == "Repayments":
    st.markdown('<div class="main-title">💰 Payment Processing</div>', unsafe_allow_html=True)
    
    if not df.empty:
        with st.form("repayment_form_final"):
            p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount Paid", min_value=0)
            p_ref = st.text_input("Receipt Reference")
            
            if st.form_submit_button("🚀 Post Payment"):
                # Update Logic
                new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                conn.update(worksheet="Payments", data=pd.concat([pay_df, new_p], ignore_index=True))
                
                # Deduct from Borrowers
                df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amt
                conn.update(worksheet="Borrowers", data=df)
                st.success("Payment Received!")
                st.rerun()

        st.write("---")
        st.subheader("📋 Recent History")
        st.dataframe(
            pay_df.iloc[::-1],
            column_config={"AMOUNT_PAID": st.column_config.NumberColumn("Amount", format="UGX %,d")},
            use_container_width=True, hide_index=True
        )
elif page == "Repayments":
    st.markdown('<div class="main-title">💰 Payment Processing Center</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. THE INPUT CARD
        st.markdown("""
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 30px;">
                <h4 style="margin: 0 0 15px 0; color: #1e3a8a;">➕ Record New Receipt</h4>
            </div>
        """, unsafe_allow_html=True)

        # Place the form inside a column to keep it centered and professional
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("cloud_pay_form", clear_on_submit=True):
                p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
                
                c_a, c_b = st.columns(2)
                with c_a:
                    p_amt = st.number_input("Amount Paid (UGX)", min_value=0, step=10000)
                with c_b:
                    p_ref = st.text_input("Receipt / Ref No.", placeholder="e.g. MPESA-123")
                
                st.write("") # Spacer
                if st.form_submit_button("🚀 Confirm & Post Payment", use_container_width=True):
                    if p_amt > 0:
                        # 1. Update Payments Sheet
                        new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], 
                                           columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                        updated_pay = pd.concat([pay_df, new_p], ignore_index=True)
                        conn.update(worksheet="Payments", data=updated_pay)
                        
                        # 2. Update Borrowers Balance
                        # We find the current balance and subtract the payment
                        current_bal = df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'].values[0]
                        df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                        df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] = current_bal - p_amt
                        
                        conn.update(worksheet="Borrowers", data=df)
                        st.success(f"Successfully posted UGX {p_amt:,.0f} for {p_name}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Please enter a valid amount.")

        with col2:
            # 2. MINI SUMMARY WIDGET
            st.markdown("""
                <div style="background-color: #eff6ff; padding: 20px; border-radius: 12px; border: 1px solid #bfdbfe;">
                    <h5 style="color: #1e40af; margin-top: 0;">System Tip</h5>
                    <p style="font-size: 0.85rem; color: #1e3a8a; line-height: 1.5;">
                        Recording a payment here automatically updates the <b>Ledger</b> and reduces the <b>Outstanding Risk</b> on the Executive Summary.
                    </p>
                </div>
            """, unsafe_allow_html=True)

        # 3. STYLED HISTORY TABLE
        st.write("---")
        st.subheader("📋 Recent Transaction History")
        
        if not pay_df.empty:
            # Sort by date newest first
            history_df = pay_df.copy()
            history_df['DATE'] = pd.to_datetime(history_df['DATE']).dt.date
            
            st.dataframe(
                history_df.iloc[::-1], # Newest on top
                column_config={
                    "DATE": st.column_config.DateColumn("Payment Date", format="DD/MM/YYYY"),
                    "CUSTOMER_NAME": "Borrower",
                    "AMOUNT_PAID": st.column_config.NumberColumn("Amount (UGX)", format="%,d"),
                    "REF": "Reference #"
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No payment history available yet.")
    else:
        st.info("Please register a borrower before recording payments.")
elif page == "Calendar":
    st.markdown('<div class="main-title">🗓️ Collection Calendar</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. Clean up dates
        df['DUE_DATE_DT'] = pd.to_datetime(df['DATE_ISSUED']) + pd.Timedelta(days=30)
        today = pd.Timestamp(datetime.now().date())
        this_week_end = today + pd.Timedelta(days=7)

        # 2. Setup Tabs
        tab1, tab2, tab3 = st.tabs(["🚨 Overdue", "📅 Due This Week", "✅ All Collections"])

        with tab1:
            # Overdue = Due date in past AND still has a balance
            overdue = df[(df['DUE_DATE_DT'].dt.date < today.date()) & (df['OUTSTANDING_AMOUNT'] > 0)]
            if not overdue.empty:
                st.error(f"⚠️ {len(overdue)} Loans are past due!")
                st.dataframe(overdue[['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT']], use_container_width=True, hide_index=True)
            else:
                st.success("No overdue loans!")

        with tab2:
            this_week = df[(df['DUE_DATE_DT'].dt.date >= today.date()) & (df['DUE_DATE_DT'].dt.date <= this_week_end.date())]
            st.info(f"Collections due within 7 days: {len(this_week)}")
            st.dataframe(this_week[['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT']], use_container_width=True, hide_index=True)

        with tab3:
            st.dataframe(df[['CUSTOMER_NAME', 'OUTSTANDING_AMOUNT', 'DATE_ISSUED']].sort_values('DATE_ISSUED'), use_container_width=True, hide_index=True)
    else:
        st.info("No borrower data found.")

elif page == "Collateral":
    st.markdown('<div class="main-title">🔐 Collateral Vault Control</div>', unsafe_allow_html=True)
    
    # --- 1. VAULT OVERVIEW STATS ---
    if not collateral_df.empty:
        held_assets = collateral_df[collateral_df['STATUS'].str.contains("HELD", na=False)]
        total_vault_value = held_assets['VALUE'].sum()
        
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; border-radius: 15px; color: white; margin-bottom: 25px; border: 1px solid #334155;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <p style="margin: 0; font-size: 0.8rem; opacity: 0.7; text-transform: uppercase; font-weight: 600; letter-spacing: 1px;">Total Vault Valuation</p>
                        <h1 style="margin: 5px 0; color: #f8fafc; font-size: 2.2rem;">UGX {total_vault_value:,.0f}</h1>
                    </div>
                    <div style="text-align: right;">
                        <span style="background: #10b981; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: bold;">{len(held_assets)} ASSETS SECURED</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # --- 2. REGISTRATION (SECURE ENTRY) ---
    with st.expander("📥 Register & Secure New Asset", expanded=False):
        with st.form("permanent_collateral"):
            borrower_list = df['CUSTOMER_NAME'].unique().tolist() if not df.empty else ["No Borrowers Found"]
            
            c1, c2 = st.columns(2)
            with c1:
                c_owner = st.selectbox("Assign to Borrower", options=borrower_list)
                c_type = st.selectbox("Asset Category", ["Logbook", "Land Title", "Electronics", "Household", "Other"])
            with c2:
                c_val = st.number_input("Estimated Market Value (UGX)", min_value=0, step=100000)
                c_desc = st.text_input("Serial Number / Plate Number / Description")
            
            if st.form_submit_button("🔒 Lock Asset to Vault", use_container_width=True):
                new_asset = pd.DataFrame([[c_owner, c_type, c_desc, c_val, "🔐 HELD"]], 
                                       columns=['NAME', 'ASSET_TYPE', 'DESCRIPTION', 'VALUE', 'STATUS'])
                updated_c = pd.concat([collateral_df, new_asset], ignore_index=True)
                conn.update(worksheet="Collateral", data=updated_c)
                st.success("Asset successfully encrypted and stored in vault.")
                st.rerun()

    # --- 3. THE VAULT TABLE ---
    st.write("---")
    st.subheader("📋 Assets Currently Held")
    
    if not collateral_df.empty:
        st.dataframe(
            collateral_df,
            column_config={
                "NAME": "Owner",
                "ASSET_TYPE": "Category",
                "DESCRIPTION": "Details",
                "VALUE": st.column_config.NumberColumn("Market Value", format="UGX %,d"),
                "STATUS": st.column_config.TextColumn("Vault Status")
            },
            use_container_width=True, hide_index=True
        )
        
        # --- 4. VAULT MAINTENANCE (Edit & Release) ---
        st.write("---")
        st.subheader("🛠️ Vault Maintenance")
        
        # We create two tabs: one for Editing, one for Releasing
        edit_tab, release_tab = st.tabs(["✏️ Edit Asset Details", "🔓 Release Asset"])

        with edit_tab:
            if not collateral_df.empty:
                # Select the asset to edit based on Description/Details
                asset_to_edit = st.selectbox(
                    "Select Asset to Modify:", 
                    options=collateral_df['DESCRIPTION'].unique(),
                    key="edit_selector"
                )
                
                # Get current values for the selected asset
                current_row = collateral_df[collateral_df['DESCRIPTION'] == asset_to_edit].iloc[0]
                
                with st.form("edit_asset_form"):
                    st.info(f"Modifying record for: {current_row['NAME']}")
                    
                    new_desc = st.text_input("Update Description", value=current_row['DESCRIPTION'])
                    new_val = st.number_input("Update Market Value (UGX)", value=int(current_row['VALUE']), step=100000)
                    new_type = st.selectbox("Update Category", 
                                          ["Logbook", "Land Title", "Electronics", "Household", "Other"],
                                          index=["Logbook", "Land Title", "Electronics", "Household", "Other"].index(current_row['ASSET_TYPE']))
                    
                    if st.form_submit_button("💾 Save Changes", use_container_width=True):
                        # Update the dataframe
                        idx = collateral_df[collateral_df['DESCRIPTION'] == asset_to_edit].index
                        collateral_df.loc[idx, 'DESCRIPTION'] = new_desc
                        collateral_df.loc[idx, 'VALUE'] = new_val
                        collateral_df.loc[idx, 'ASSET_TYPE'] = new_type
                        
                        # Sync to Google Sheets
                        conn.update(worksheet="Collateral", data=collateral_df)
                        st.success("Changes encrypted and saved!")
                        st.rerun()
            else:
                st.info("No assets available to edit.")

        with release_tab:
            active_assets = collateral_df[collateral_df['STATUS'] == "🔐 HELD"]
            if not active_assets.empty:
                target_asset = st.selectbox("Select Asset to Release:", options=active_assets['DESCRIPTION'].unique(), key="rel_selector")
                if st.button("Confirm Release to Client", use_container_width=True, type="primary"):
                    confirm_date = datetime.now().strftime('%Y-%m-%d')
                    collateral_df.loc[collateral_df['DESCRIPTION'] == target_asset, 'STATUS'] = f"🔓 RETURNED ({confirm_date})"
                    conn.update(worksheet="Collateral", data=collateral_df)
                    st.toast(f"Asset released!")
                    st.rerun()
            else:
                st.info("No 'HELD' assets found for release.")
elif page == "Ledger":
    st.markdown('<div class="main-title">📄 Client Statement of Account</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. Select Client
        target = st.selectbox("Select Client for Report", options=df['CUSTOMER_NAME'].unique())
        client_info = df[df['CUSTOMER_NAME'] == target].iloc[0]
        client_pay = pay_df[pay_df['CUSTOMER_NAME'] == target].sort_values(by='DATE', ascending=False)
        
        # 2. Financial Math
        int_amt = (client_info['LOAN_AMOUNT'] * client_info['INTEREST_RATE']) / 100
        total_due = client_info['LOAN_AMOUNT'] + int_amt
        bal = total_due - client_info['AMOUNT_PAID']

        # 3. PROFESSIONAL HEADER (Company Details)
        st.markdown(f"""
            <div style="background-color: #f8fafc; padding: 25px; border-radius: 15px; border: 1px solid #e2e8f0; margin-bottom: 25px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h2 style="color: #1e3a8a; margin: 0;">ZOE CONSULTS LTD</h2>
                        <p style="color: #64748b; font-size: 0.9rem; margin: 2px 0;">
                            📍 Plot 45, Kampala Road, Uganda<br>
                            📞 +256 700 000 000 | 📧 info@zoeconsults.com
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <h4 style="margin: 0; color: #1e3a8a;">OFFICIAL STATEMENT</h4>
                        <p style="color: #64748b; font-size: 0.8rem;">Date: {datetime.now().strftime('%d %b %Y')}</p>
                    </div>
                </div>
                <hr style="border: 0.5px solid #e2e8f0; margin: 15px 0;">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <p style="font-size: 0.8rem; color: #94a3b8; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Client Name</p>
                        <p style="font-weight: bold; font-size: 1.1rem; color: #1e293b;">{target}</p>
                    </div>
                    <div>
                        <p style="font-size: 0.8rem; color: #94a3b8; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Account Status</p>
                        <p style="font-weight: bold; color: {'#10b981' if bal <= 0 else '#ef4444'};">
                            {'✅ FULLY PAID' if bal <= 0 else '🚩 OUTSTANDING'}
                        </p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 4. COMPACT FINANCIAL SUMMARY
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Principal", f"UGX {client_info['LOAN_AMOUNT']:,.0f}")
        c2.metric("Interest ({0}%)".format(client_info['INTEREST_RATE']), f"UGX {int_amt:,.0f}")
        c3.metric("Total Paid", f"UGX {client_info['AMOUNT_PAID']:,.0f}")
        c4.metric("Balance", f"UGX {bal:,.0f}", delta_color="inverse")

        # 5. WHATSAPP BUTTON
        message = (
            f"Hello%20{target},%20this%20is%20Zoe%20Consults.%0A%0A"
            f"Your%20Statement:%0A"
            f"Principal:%20UGX%20{client_info['LOAN_AMOUNT']:,.0f}%0A"
            f"Interest:%20UGX%20{int_amt:,.0f}%0A"
            f"Total%20Paid:%20UGX%20{client_info['AMOUNT_PAID']:,.0f}%0A"
            f"Balance:%20UGX%20{bal:,.0f}"
        )
        wa_url = f"https://wa.me/?text={message}"
        
        st.markdown(f"""
            <a href="{wa_url}" target="_blank" style="text-decoration: none;">
                <div style="background-color: #25D366; color: white; padding: 8px 16px; border-radius: 8px; width: fit-content; font-weight: bold; display: flex; align-items: center; gap: 8px;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" width="18px"> Send Statement
                </div>
            </a>
        """, unsafe_allow_html=True)

        # 6. TRANSACTION HISTORY
        st.write("---")
        st.subheader("🔍 Transaction History")
        if not client_pay.empty:
            st.dataframe(
                client_pay[['DATE', 'AMOUNT_PAID', 'REF']], 
                column_config={
                    "DATE": "Payment Date",
                    "AMOUNT_PAID": st.column_config.NumberColumn("Amount Received", format="UGX %,d"),
                    "REF": "Receipt/Ref #"
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No payments recorded yet.")
    else:
        st.info("No borrowers found.")
    
elif page == "Settings":
    st.markdown('<div class="main-title">⚙️ System Configuration</div>', unsafe_allow_html=True)
    
    # Create the Tabs
    tab_sync, tab_branding = st.tabs(["🔄 Data Sync", "🎨 Branding & Identity"])
    
    with tab_sync:
        st.subheader("Maintenance")
        st.write("Force the app to pull the latest data from Google Sheets.")
        if st.button("🧹 Clear Cache & Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with tab_branding:
        st.subheader("Edit Company Profile")
        
        # This form must be indented inside the 'with tab_branding' block
        with st.form("branding_editor_v2"):
            # Get current values (using the helper function we defined earlier)
            curr_name = get_setting("Company Name", "ZOE")
            curr_tagline = get_setting("Tagline", "CONSULTS")
            curr_logo_type = get_setting("Logo Type", "Emoji")
            curr_logo_val = get_setting("Logo Value", "🛡️")

            new_name = st.text_input("Company Name", value=curr_name)
            new_tagline = st.text_input("Tagline", value=curr_tagline)
            
            logo_choice = st.radio("Logo Style", ["Emoji", "URL"], 
                                   index=0 if curr_logo_type == "Emoji" else 1,
                                   horizontal=True)
            
            new_logo_val = st.text_input("Logo Value (Emoji or Image URL)", 
                                         value=curr_logo_val,
                                         help="Direct link to image or a single emoji")

            if st.form_submit_button("💾 Save Branding Changes", use_container_width=True):
                # Prepare data for Google Sheets
                new_settings_data = pd.DataFrame([
                    ["Company Name", new_name],
                    ["Tagline", new_tagline],
                    ["Logo Type", logo_choice],
                    ["Logo Value", new_logo_val]
                ], columns=["Property", "Value"])
                
                # Sync back to the 'Settings' tab in your Google Sheet
                try:
                    conn.update(worksheet="Settings", data=new_settings_data)
                    st.success("✅ Identity updated! Refreshing app...")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: Make sure you created a tab named 'Settings' in your Google Sheet. {e}")
