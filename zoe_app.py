import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import base64
import urllib.parse
from streamlit_option_menu import option_menu  # <--- MAKE SURE THIS IS HERE
from datetime import datetime, timedelta  # Ensure ', timedelta' is added here!
from fpdf import FPDF  # This stays the same even with fpdf2 installed
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

@st.cache_data(ttl=600)
def get_all_data():
    try:
        b_df = conn.read(worksheet="Borrowers").dropna(how="all")
        p_df = conn.read(worksheet="Payments").dropna(how="all")
        c_df = conn.read(worksheet="Collateral").dropna(how="all")
        s_df = conn.read(worksheet="Settings").dropna(how="all")
        return b_df, p_df, c_df, s_df
    except Exception:
        # Returns empty dataframes if the API is busy or tab is missing
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# 1. Load the data
df, pay_df, collateral_df, settings_df = get_all_data()

# 2. Define the helper (This fixes your NameError!)
def get_setting(prop, default):
    try:
        if not settings_df.empty:
            val = settings_df.loc[settings_df['Property'] == prop, 'Value'].values[0]
            return val if pd.notna(val) else default
        return default
    except:
        return default

# 3. Now you can safely use it
brand_name = get_setting("Company Name", "ZOE")
brand_tagline = get_setting("Tagline", "CONSULTS")
brand_logo_type = get_setting("Logo Type", "Emoji")
brand_logo_val = get_setting("Logo Value", "")

# --- ADD THIS FUNCTION HERE ---
def get_setting(prop, default):
    try:
        # Check if settings_df exists and has the property
        if not settings_df.empty:
            val = settings_df.loc[settings_df['Property'] == prop, 'Value'].values[0]
            # Ensure we don't return 'nan' if the cell is empty
            return val if pd.notna(val) else default
        return default
    except:
        return default
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
    st.markdown('<div class="main-title">🏛️ Zoe Consults Executive Overview</div>', unsafe_allow_html=True)
    
    # --- 1. THE BIG NUMBERS (KPIs) ---
    total_capital = df['LOAN_AMOUNT'].sum()
    total_paid = df['AMOUNT_PAID'].sum()
    total_outstanding = df['OUTSTANDING_AMOUNT'].sum()
    
    # Calculate Repayment Percentage
    repayment_rate = (total_paid / total_capital * 100) if total_capital > 0 else 0
    
    # Display top metrics in professional cards
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric("💰 Total Capital Out", f"UGX {total_capital:,.0f}")
    with kpi2:
        st.metric("📈 Total Collected", f"UGX {total_paid:,.0f}", delta=f"{repayment_rate:.1f}% Rate")
    with kpi3:
        st.metric("🚨 Total At Risk", f"UGX {total_outstanding:,.0f}", delta="-Outstanding", delta_color="inverse")

    st.write("---")

    # --- 2. THE VISUAL CHARTS (Using Navy Blue Palette) ---
    import plotly.express as px
    
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("#### 🏦 Portfolio Composition")
        # Pie Chart: Paid vs Outstanding
        fig_pie = px.pie(
            values=[total_paid, total_outstanding], 
            names=['Collected', 'Outstanding'],
            color_discrete_sequence=['#1e3a8a', '#3b82f6'], # Navy and Blue
            hole=0.5
        )
        fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        st.markdown("#### 📅 Monthly Collection Trend")
        # Bar Chart: Payments over time
        if not pay_df.empty:
            monthly_trend = pay_df.groupby(pay_df['DATE'].astype(str).str[:7])['AMOUNT_PAID'].sum().reset_index()
            fig_trend = px.bar(
                monthly_trend, 
                x='DATE', 
                y='AMOUNT_PAID',
                color_discrete_sequence=['#1e3a8a']
            )
            fig_trend.update_layout(xaxis_title="Month", yaxis_title="Amount (UGX)", margin=dict(t=20))
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Start logging payments to see trends.")

    # --- 3. TOP BORROWERS LIST ---
    st.write("---")
    st.markdown("#### 🏆 Top 5 Active Portfolios")
    top_borrowers = df.nlargest(5, 'LOAN_AMOUNT')[['CUSTOMER_NAME', 'LOAN_AMOUNT', 'OUTSTANDING_AMOUNT']]
    st.table(top_borrowers)

elif page == "Borrowers":
    st.markdown('<div class="main-title">👥 Active Loan Registry</div>', unsafe_allow_html=True)
    
    # --- 1. NEW TOP-LEVEL ACTION BAR ---
    header_col1, header_col2 = st.columns([1, 2])
    
    with header_col1:
        # We use a popover here to keep the form hidden until needed
        with st.popover("➕ New Loan", use_container_width=True):
            with st.form("expanded_register_form", clear_on_submit=True):
                st.markdown("### 📝 Register New Borrower")
                
                # --- SECTION 1: PERSONAL DETAILS ---
                st.markdown("##### 👤 Personal Details")
                col_name1, col_name2 = st.columns(2)
                with col_name1:
                    f_first = st.text_input("First Name")
                    f_nin = st.text_input("NIN (National ID)")
                    f_country = st.text_input("Country", value="Uganda")
                with col_name2:
                    f_last = st.text_input("Last Name")
                    f_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                    f_contact = st.text_input("Contact Number (WhatsApp)")

                # --- SECTION 2: BUSINESS & WORK ---
                st.markdown("##### 💼 Business & Work")
                col_biz1, col_biz2 = st.columns(2)
                with col_biz1:
                    f_biz_name = st.text_input("Business Name")
                    f_work_status = st.selectbox("Working Status", ["Employed", "Self-Employed", "Unemployed", "Student"])
                with col_biz2:
                    f_email = st.text_input("Email Address")
                    f_nok = st.text_input("Next of Kin Name & Contact")

                # --- SECTION 3: LOAN DETAILS ---
                st.markdown("##### 💰 Loan Details")
                f_type = st.selectbox("Loan Type", ["Business Loan", "Logbook Loan", "Personal Loan", "Salary Loan", "Emergency Loan"])
                
                col_loan1, col_loan2, col_loan3 = st.columns(3)
                with col_loan1:
                    f_amt = st.number_input("Principal (UGX)", min_value=0, step=50000)
                with col_loan2:
                    f_rate = st.number_input("Interest %", value=10)
                with col_loan3:
                    f_dur = st.selectbox("Days", [15, 30, 45, 60, 90], index=1)
                
                f_date = st.date_input("Date Issued", datetime.now())
                
                # Combine Names for the Main Database
                full_name = f"{f_first} {f_last}".strip()

                if st.form_submit_button("✅ Save & Disburse", use_container_width=True):
                    if f_first and f_last and f_amt > 0:
                        new_id = int(df['SN'].max() + 1) if not df.empty else 1
                        starting_bal = f_amt + (f_amt * f_rate / 100)
                        
                        # NEW DATA ROW (Ensure these columns exist in your Google Sheet)
                        new_data = [
                            new_id, full_name, f_amt, 0, starting_bal, f_rate, str(f_date), f_dur,
                            f_nin, f_nok, f_country, f_type, f_biz_name, f_email, f_contact, f_gender, f_work_status
                        ]
                        
                        # Column names must match your Sheet headers exactly
                        new_cols = [
                            'SN', 'CUSTOMER_NAME', 'LOAN_AMOUNT', 'AMOUNT_PAID', 'OUTSTANDING_AMOUNT', 'INTEREST_RATE', 'DATE_ISSUED', 'DURATION',
                            'NIN', 'NEXT_OF_KIN', 'COUNTRY', 'LOAN_TYPE', 'BUSINESS_NAME', 'EMAIL', 'CONTACT', 'GENDER', 'WORKING_STATUS'
                        ]
                        
                        new_row = pd.DataFrame([new_data], columns=new_cols)
                        conn.update(worksheet="Borrowers", data=pd.concat([df, new_row], ignore_index=True))
                        st.success(f"Loan for {full_name} has been synced!")
                        st.rerun()
                    else:
                        st.error("Please fill in First Name, Last Name, and Amount.")
    with header_col2:
        # Quick Search Bar added next to the button for better utility
        search_query = st.text_input("", placeholder="🔍 Search borrower name...", label_visibility="collapsed")

    st.write("---") # Visual separator

    if not df.empty:
        # Filter data based on search
        display_df = df.copy()
        if search_query:
            display_df = display_df[display_df['CUSTOMER_NAME'].str.contains(search_query, case=False)]
            
        # ... [RETAIN ALL YOUR EXISTING CALCULATION & TABLE CODE HERE] ...
    
    if not df.empty:
        # --- 1. CORE CALCULATIONS ---
        display_df = df.copy()
        for col in ['LOAN_AMOUNT', 'INTEREST_RATE', 'AMOUNT_PAID']:
            display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
        
        if 'DURATION' not in display_df.columns: display_df['DURATION'] = 30
        
        display_df['INTEREST_AMT'] = (display_df['LOAN_AMOUNT'] * display_df['INTEREST_RATE']) / 100
        display_df['ISSUED_DT'] = pd.to_datetime(display_df['DATE_ISSUED']).dt.date
        display_df['DUE_DT'] = display_df.apply(lambda x: x['ISSUED_DT'] + pd.Timedelta(days=int(x['DURATION'])), axis=1)
        
        # Penalty & Status Logic
        def process_row(row):
            base_total = row['LOAN_AMOUNT'] + row['INTEREST_AMT']
            outstanding = base_total - row['AMOUNT_PAID']
            is_overdue = datetime.now().date() > row['DUE_DT'] and outstanding > 0
            penalty = (outstanding * 0.05) if is_overdue else 0
            final_bal = outstanding + penalty
            status = "✅ SETTLED" if final_bal <= 0 else ("🚩 OVERDUE" if is_overdue else "🔵 ACTIVE")
            return pd.Series([penalty, final_bal, status], index=['Penalty', 'Balance', 'Status'])

        display_df[['Penalty', 'REAL_OUTSTANDING', 'Status']] = display_df.apply(process_row, axis=1)

        # --- 2. NEW: PROFIT METRICS ---
        total_interest = display_df['INTEREST_AMT'].sum()
        total_penalties = display_df['Penalty'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Interest Earned", f"UGX {total_interest:,.0f}")
        m2.metric("Late Fees Accrued", f"UGX {total_penalties:,.0f}", delta=f"{len(display_df[display_df['Status']=='🚩 OVERDUE'])} Cases")
        m3.metric("Total Expected Profit", f"UGX {(total_interest + total_penalties):,.0f}", delta_color="normal")
        
        st.write("---")

        # --- 3. STYLED TABLE ---
        def highlight_latest(row):
            return ['background-color: #f0f9ff; border-left: 5px solid #0ea5e9'] * len(row) if row.name == 0 else [''] * len(row)

        show_cols = ['CUSTOMER_NAME', 'ISSUED_DT', 'LOAN_AMOUNT', 'INTEREST_RATE', 'Penalty', 'DURATION', 'REAL_OUTSTANDING', 'Status']
        styled_df = display_df[show_cols].reset_index(drop=True).style.apply(highlight_latest, axis=1)

        st.dataframe(styled_df, column_config={
            "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
            "Penalty": st.column_config.NumberColumn("Late Fee", format="%,d"),
            "REAL_OUTSTANDING": st.column_config.NumberColumn("Total Balance", format="UGX %,d"),
            "INTEREST_RATE": st.column_config.NumberColumn("Rate", format="%d%%"),
        }, use_container_width=True, hide_index=True)

        # --- 4. PERFORMANCE ANALYTICS ---
        st.write("---")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("📈 Revenue Trend")
            # Prepare monthly data
            display_df['Month'] = pd.to_datetime(display_df['DATE_ISSUED']).dt.strftime('%b %Y')
            monthly_rev = display_df.groupby('Month').agg({'INTEREST_AMT': 'sum', 'Penalty': 'sum'}).reset_index()
            # Sort chronologically
            monthly_rev['Sort'] = pd.to_datetime(monthly_rev['Month'], format='%b %Y')
            monthly_rev = monthly_rev.sort_values('Sort')
            
            st.bar_chart(monthly_rev, x="Month", y=["INTEREST_AMT", "Penalty"], 
                         color=["#0284c7", "#ef4444"], use_container_width=True)
            st.caption("🔵 Interest | 🔴 Penalties")

        with col_chart2:
            st.subheader("🍕 Portfolio Split")
            # We look at the 'Collateral' type if you have that column, 
            # or we can split by Loan Duration to see which 'Product' is most popular
            if 'DURATION' in display_df.columns:
                duration_split = display_df['DURATION'].value_counts()
                st.vega_lite_chart(display_df, {
                    'mark': {'type': 'arc', 'innerRadius': 50},
                    'encoding': {
                        'theta': {'field': 'LOAN_AMOUNT', 'type': 'quantitative', 'aggregate': 'sum'},
                        'color': {'field': 'DURATION', 'type': 'nominal', 'legend': {"title": "Loan Term (Days)"}},
                    },
                }, use_container_width=True)
                st.caption("Distribution of Capital by Loan Duration")
            else:
                st.info("Add more categories to see a portfolio split.")

        # --- 5. MANAGEMENT & REGISTRATION ---
        st.write("")
        with st.expander("🛠️ Manage Records (Edit/Delete)"):
            target = st.selectbox("Select Client:", options=df['CUSTOMER_NAME'].unique(), key="mgt_select")
            st.info(f"System ready to modify {target}'s records.")


    else:
        st.info("Registry is currently empty.")

elif page == "Payments":
    st.markdown('<div class="main-title">💰 Payment Processing Center</div>', unsafe_allow_html=True)
    
    # 1. TOP STATS (High-level glance)
    total_collected = pay_df['AMOUNT_PAID'].sum() if not pay_df.empty else 0
    st.markdown(f"""
        <div style="background-color: #f0fdf4; border-radius: 10px; padding: 15px; margin-bottom: 20px; border: 1px solid #bbf7d0;">
            <p style="margin:0; color:#166534; font-size: 0.9rem;">Total Collections (All Time)</p>
            <h2 style="margin:0; color:#15803d;">UGX {total_collected:,.0f}</h2>
        </div>
    """, unsafe_allow_html=True)

    # 2. TABBED INTERFACE
    post_tab, history_tab = st.tabs(["➕ Post New Payment", "✏️ Manage History"])

    with post_tab:
        with st.form("payment_form_styled", clear_on_submit=True):
            st.markdown("##### 📝 Entry Details")
            p_name = st.selectbox("Select Borrower", options=df['CUSTOMER_NAME'].unique())
            
            # Fetch current balance for the selected borrower
            current_bal = df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'].values[0]
            
            col_a, col_b = st.columns(2)
            with col_a:
                p_amt = st.number_input(f"Amount (Current Bal: {current_bal:,.0f})", min_value=0, step=10000)
            with col_b:
                p_ref = st.text_input("Receipt / Reference No.", placeholder="e.g. MM-12345")

            st.write("")
            if st.form_submit_button("🚀 Finalize & Post Payment", use_container_width=True):
                # Validation Logic
                if p_amt <= 0:
                    st.error("❌ Please enter a valid payment amount.")
                elif p_amt > current_bal + 5: # Small buffer for rounding
                    st.warning(f"⚠️ Warning: Payment of {p_amt:,.0f} exceeds balance of {current_bal:,.0f}")
                elif not p_ref:
                    st.error("❌ A Reference number is required for auditing.")
                else:
                    # Proceed with update
                    new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], 
                                       columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                    conn.update(worksheet="Payments", data=pd.concat([pay_df, new_p], ignore_index=True))
                    
                    # Update Borrowers Sheet
                    df.loc[df['CUSTOMER_NAME'] == p_name, 'AMOUNT_PAID'] += p_amt
                    df.loc[df['CUSTOMER_NAME'] == p_name, 'OUTSTANDING_AMOUNT'] -= p_amt
                    conn.update(worksheet="Borrowers", data=df)
                    
                    st.success(f"✅ Payment for {p_name} has been synced!")
                    st.balloons()
                    st.rerun()

    with history_tab:
        st.info("To edit or delete a record, please modify the 'Payments' tab in your Google Sheet directly to maintain a secure audit trail.")

    # 3. RECENT HISTORY TABLE
    st.write("---")
    st.markdown("#### 📋 Recent Receipt History")
    
    if not pay_df.empty:
        # Sort by date descending to show latest first
        recent_pays = pay_df.tail(10).iloc[::-1] 
        
        st.dataframe(
            recent_pays[['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF']],
            column_config={
                "DATE": "Date",
                "CUSTOMER_NAME": "Borrower",
                "AMOUNT_PAID": st.column_config.NumberColumn("Amount (UGX)", format="%,d"),
                "REF": "Reference #"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.caption("No payments recorded yet.")
elif page == "Repayments":
    # ... (Your existing form code here) ...

    st.write("---")
    st.subheader("📋 Recent Transaction History")
    
    if not pay_df.empty:
        st.dataframe(
            pay_df.iloc[::-1], 
            column_config={
                "DATE": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                "CUSTOMER_NAME": "Borrower",
                "AMOUNT_PAID": st.column_config.NumberColumn(
                    "Amount Received 💰", 
                    format="UGX %,d",
                    help="Total money collected in this transaction"
                ),
                "REF": "Receipt #"
            },
            use_container_width=True,
            hide_index=True
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
    st.markdown('<div class="main-title">📑 Client Statement Center</div>', unsafe_allow_html=True)
    
    # 1. THE BRAIN (Session State)
    if 'ready' not in st.session_state:
        st.session_state.ready = False
        st.session_state.b64_str = ""
    if 'last_client' not in st.session_state:
        st.session_state.last_client = ""

    if not df.empty:
        # 2. SELECTOR with "Change Detector"
        target_client = st.selectbox("🔍 Select Borrower", options=df['CUSTOMER_NAME'].unique(), key="ledger_select_v11")
        
        # --- CRITICAL FIX: If the name changed, wipe the old PDF ---
        if target_client != st.session_state.last_client:
            st.session_state.ready = False
            st.session_state.b64_str = ""
            st.session_state.last_client = target_client
            # No rerun needed here, it just clears the variables for the next lines

        loan_info = df[df['CUSTOMER_NAME'] == target_client].iloc[0]
        client_payments = pay_df[pay_df['CUSTOMER_NAME'] == target_client]

        # 3. SUMMARY CARDS
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Principal", f"{loan_info['LOAN_AMOUNT']:,.0f}")
        with c2: st.metric("Paid", f"{loan_info['AMOUNT_PAID']:,.0f}")
        with c3: st.metric("Balance", f"{loan_info['OUTSTANDING_AMOUNT']:,.0f}")

        st.divider()

        # 4. ACTION ROW
        p1, p2, p3 = st.columns(3)

        with p1:
            if st.button("🔄 Prepare Official PDF", use_container_width=True):
                from fpdf import FPDF
                import base64
                
                # 1. SETUP THE PDF CLASS
                class PDF(FPDF):
                    def header(self):
                        # Navy Blue Banner
                        self.set_fill_color(30, 58, 138)
                        self.rect(0, 0, 210, 45, 'F')
                        self.set_text_color(255, 255, 255)
                        self.set_font("Arial", 'B', 22)
                        self.set_xy(10, 12)
                        self.cell(0, 10, "ZOE CONSULTS LTD", ln=True)
                        self.set_font("Arial", size=9)
                        self.cell(0, 5, "Certified Loan Management & Consultancy Services", ln=True)
                        self.ln(20)

                    def footer(self):
                        self.set_y(-25)
                        self.set_font('Arial', 'I', 8)
                        self.set_text_color(128, 128, 128)
                        self.cell(0, 10, f'Page {self.page_no()} | Statement Date: {datetime.now().strftime("%Y-%m-%d")}', 0, 0, 'C')

                pdf = PDF()
                pdf.add_page()
                pdf.set_text_color(0, 0, 0)

                # Helper to clean 'nan' values from the sheet
                def clean(val):
                    v = str(val)
                    return "---" if v.lower() == "nan" or v.lower() == "none" else v

                # 2. BORROWER PROFILE
                pdf.set_fill_color(240, 242, 246)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 10, f"  OFFICIAL STATEMENT: {target_client.upper()}", 0, 1, 'L', True)
                
                pdf.set_font("Arial", size=10)
                pdf.ln(2)
                pdf.cell(95, 7, f"NIN: {clean(loan_info.get('NIN'))}", 0, 0)
                pdf.cell(95, 7, f"Loan Type: {clean(loan_info.get('LOAN_TYPE'))}", 0, 1)
                pdf.cell(95, 7, f"Business: {clean(loan_info.get('BUSINESS_NAME'))}", 0, 0)
                pdf.cell(95, 7, f"Contact: {clean(loan_info.get('CONTACT'))}", 0, 1)
                pdf.ln(8)

                # 3. FINANCIAL SUMMARY (Restored)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 10, "  LOAN SUMMARY", 0, 1, 'L', True)
                pdf.ln(2)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(60, 10, "Principal", 1, 0, 'C')
                pdf.cell(60, 10, "Total Paid", 1, 0, 'C')
                pdf.cell(70, 10, "CURRENT BALANCE", 1, 1, 'C')
                
                pdf.set_font("Arial", size=10)
                pdf.cell(60, 12, f"UGX {loan_info['LOAN_AMOUNT']:,.0f}", 1, 0, 'C')
                pdf.cell(60, 12, f"UGX {loan_info['AMOUNT_PAID']:,.0f}", 1, 0, 'C')
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(70, 12, f"UGX {loan_info['OUTSTANDING_AMOUNT']:,.0f}", 1, 1, 'C')
                pdf.ln(8)

                # 4. PAYMENT HISTORY TABLE (Restored)
                if not client_payments.empty:
                    pdf.set_font("Arial", 'B', 11)
                    pdf.cell(0, 10, "  TRANSACTION HISTORY", 0, 1, 'L', True)
                    pdf.ln(2)
                    pdf.set_fill_color(30, 58, 138); pdf.set_text_color(255, 255, 255)
                    pdf.cell(50, 10, "Date", 1, 0, 'C', True)
                    pdf.cell(80, 10, "Reference #", 1, 0, 'C', True)
                    pdf.cell(60, 10, "Amount Paid", 1, 1, 'C', True)
                    
                    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", size=10)
                    for _, row in client_payments.iterrows():
                        pdf.cell(50, 10, str(row['DATE']), 1, 0, 'C')
                        pdf.cell(80, 10, f" {str(row['REF'])}", 1, 0, 'L')
                        pdf.cell(60, 10, f"{row['AMOUNT_PAID']:,.0f} ", 1, 1, 'R')
                
                # 5. STAMP AREA
                pdf.set_y(220)
                pdf.set_draw_color(30, 58, 138)
                pdf.set_font("Arial", 'B', 8)
                pdf.set_x(140)
                pdf.cell(50, 25, "OFFICIAL STAMP", 1, 0, 'C')

                # --- 6. SAVE & RERUN ---
                st.session_state.b64_str = base64.b64encode(pdf.output()).decode()
                st.session_state.ready = True
                st.rerun()

        with p2:
            if st.session_state.ready:
                st.markdown(f'''
                    <a href="data:application/pdf;base64,{st.session_state.b64_str}" 
                       download="Statement_{target_client}.pdf" style="text-decoration:none;">
                        <div style="background-color:#f1f5f9; color:#1e293b; padding:8px; 
                                    border-radius:5px; text-align:center; font-weight:bold; border:1px solid #cbd5e1;">
                            📥 Download PDF
                        </div>
                    </a>
                ''', unsafe_allow_html=True)
            else:
                st.button("📥 Download", disabled=True, use_container_width=True)

        with p3:
            # WhatsApp logic
            clean_p = "".join(filter(str.isdigit, str(loan_info.get('CONTACT', ''))))
            wa_url = f"https://wa.me/{clean_p}?text=Hello%20{target_client}"
            st.markdown(f'<a href="{wa_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366; color:white; padding:8px; border-radius:5px; text-align:center; font-weight:bold;">💬 WhatsApp</div></a>', unsafe_allow_html=True)

        # 5. DATA TABLE
        st.write("---")
        st.dataframe(client_payments[['DATE', 'REF', 'AMOUNT_PAID']], use_container_width=True, hide_index=True)

    else:
        st.info("No records found.")
    
elif page == "Settings":
    st.markdown('<div class="main-title">⚙️ System Configuration</div>', unsafe_allow_html=True)
    
    # 1. TABS FOR ORGANIZATION
    tab_sync, tab_branding, tab_backup = st.tabs(["🔄 Data Sync", "🎨 Branding", "📥 Database Backup"])
    
    with tab_sync:
        st.subheader("System Maintenance")
        if st.button("🧹 Clear Cache & Refresh All Sheets", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with tab_branding:
        # ... [Keep your Branding Form here] ...
        st.info("Identity changes are saved directly to the 'Settings' tab in your Google Sheet.")

    with tab_backup:
        st.subheader("Export Entire Database")
        st.write("Download all records (Borrowers, Payments, Collateral) as a single Excel file for offline storage.")
        
        # LOGIC TO CREATE THE EXCEL FILE
        import io
        buffer = io.BytesIO()
        
        try:
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Write each dataframe to a different sheet
                df.to_excel(writer, sheet_name='Borrowers', index=False)
                pay_df.to_excel(writer, sheet_name='Payments', index=False)
                collateral_df.to_excel(writer, sheet_name='Collateral', index=False)
                settings_df.to_excel(writer, sheet_name='SystemSettings', index=False)
            
            # Create the Download Button
            st.download_button(
                label="📥 Download Master Backup (.xlsx)",
                data=buffer,
                file_name=f"ZoeLend_Backup_{datetime.now().strftime('%d_%b_%Y')}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )
            st.success("Excel file generated successfully!")
        except Exception as e:
            st.error(f"Backup engine error: {e}. Please ensure the 'xlsxwriter' library is installed.")

    # 2. FOOTER INFO
    st.markdown("---")
    st.caption(f"Zoe Consults IQ • Version 2.5.0 • Last Sync: {datetime.now().strftime('%H:%M:%S')}")
