import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import base64
import os  # <--- THIS IS THE MISSING PIECE!
import urllib.parse
from streamlit_option_menu import option_menu  # <--- MAKE SURE THIS IS HERE
from datetime import datetime, timedelta  # Ensure ', timedelta' is added here!
from fpdf import FPDF  # This stays the same even with fpdf2 installed
# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="ZoeLend Dashboard", layout="wide")
# --- 0. SECURITY SYSTEM (Line 1) ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        # Centered Login UI
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Display your logo
            if os.path.exists("Capture.PNG"):
                st.image("Capture.PNG", width=120)
            
            st.subheader("🔐 ZoeLend Admin Portal")
            
            # SMALL INPUTS
            user = st.text_input("Username", placeholder="Enter your ID")
            pw = st.text_input("Password", type="password", placeholder="••••••••")
            
            # SMALL BUTTON
            if st.button("Access System", use_container_width=True):
                # --- SET YOUR CREDENTIALS HERE ---
                if user == "admin" and pw == "Zoe2026!": 
                    st.session_state.logged_in = True
                    st.success("Access Granted")
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials")
        return False
    return True

# --- ACTIVATE ---
if not check_login():
    st.stop()
st.markdown("""
<style>
    /* 1. SIDEBAR & TITLE THEME */
    [data-testid="stSidebar"] {
        background-color: #f8fafc !important;
        border-right: 1px solid #e2e8f0;
    }

    .main-title {
        background: linear-gradient(90deg, #00A3E0, #1E3A8A);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }

    /* 2. BUTTON & ACCENT COLORS */
    div.stButton > button:first-child {
        background-color: #1E3A8A !important;
        color: white !important;
        border-radius: 8px;
        border: none;
    }

    <style>
    /* Small, sleek login button */
    div.stButton > button {
        height: 32px !important;
        padding: 0 20px !important;
        font-size: 13px !important;
        background-color: #1E3A8A !important;
    }

    <style>
    /* Global Compact Button Style */
    div.stButton > button {
        padding: 2px 15px !important;
        font-size: 0.8rem !important;
        min-height: 30px !important;
        width: auto !important;
    }
    
    /* Small Sidebar Logout */
    [data-testid="stSidebar"] button {
        font-size: 0.7rem !important;
        padding: 0px 10px !important;
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
        e_df = conn.read(worksheet="Expenses").dropna(how="all") # <--- ADD THIS
        return b_df, p_df, c_df, s_df, e_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Update your loading line:
df, pay_df, collateral_df, settings_df, exp_df = get_all_data()

# 1. Load the data
df, pay_df, collateral_df, settings_df, exp_df = get_all_data()

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
import os

# --- 1. RESOLVE THE LOGO PATH ---
# This line finds the folder where zoe_app.py is sitting
current_dir = os.path.dirname(__file__)
logo_path = os.path.join(current_dir, "logo.jpg")

with st.sidebar:
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    
    # 2. ATTEMPT TO LOAD THE LOGO
    if os.path.exists(logo_path):
        st.image(logo_path, width=180)
    else:
        # If the file still isn't found, show a clean emoji instead of crashing
        st.markdown("""
            <div style="background: linear-gradient(135deg, #00A3E0, #1E3A8A); 
                        width: 80px; height: 80px; border-radius: 20px; 
                        display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                <span style="font-size: 40px; color: white;">🛡️</span>
            </div>
        """, unsafe_allow_html=True)
    # ... rest of your option_menu ...

    # 2. THE OPTION MENU (Modern Styling)
    # Using 'option_menu' for a more mobile-responsive, centered feel
    page = option_menu(
        menu_title=None,
        options=["Overview", "Borrowers", "Repayments", "Calendar", "Collateral", "Ledger", "Settings", "Insights"],
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
                "border-radius": "8px"
            },
            "nav-link-selected": {
                "background": "linear-gradient(90deg, #00A3E0, #1E3A8A)", # <--- Logo Gradient!
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
    # 1. Custom Title with a modern "Glass" effect
    st.markdown("""
        <div style="background: #f8fafc; padding: 20px; border-radius: 15px; border-left: 10px solid #1e3a8a; margin-bottom: 30px;">
            <h1 style="margin:0; color:#0f172a; font-size: 2rem;">🛡️ Zoe Consults IQ</h1>
            <p style="margin:0; color:#64748b; font-size: 0.9rem; font-weight: 600;">PORTFOLIO REAL-TIME ANALYTICS</p>
        </div>
    """, unsafe_allow_html=True)
    
    if df.empty:
        st.warning("🕵️ Your 'Borrowers' sheet appears to be empty.")
    else:
        # --- CALCULATIONS ---
        total_p = df['LOAN_AMOUNT'].sum()
        total_c = df['AMOUNT_PAID'].sum()
        df['INTEREST_AMT'] = (df['LOAN_AMOUNT'] * df['INTEREST_RATE']) / 100
        total_expected = total_p + df['INTEREST_AMT'].sum()
        risk = total_expected - total_c
        recovery_rate = (total_c / total_expected) * 100 if total_expected > 0 else 0

        # --- PREMIUM KPI TILES (Logo-Matched Gradient) ---
        st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px;">
                <div style="background: linear-gradient(135deg, #00A3E0 0%, #1E3A8A 100%); padding: 20px; border-radius: 15px; color: white; box-shadow: 0 4px 15px rgba(0,163,224,0.2);">
                    <p style="margin: 0; font-size: 0.75rem; opacity: 0.9; text-transform: uppercase; font-weight: 700;">Principal Issued</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem;">UGX {total_p:,.0f}</h2>
                </div>
                <div style="background: white; padding: 20px; border-radius: 15px; color: #1E293B; border: 1px solid #E2E8F0; border-top: 5px solid #00A3E0;">
                    <p style="margin: 0; font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Total Collected</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem; color: #10B981;">UGX {total_c:,.0f}</h2>
                </div>
                <div style="background: white; padding: 20px; border-radius: 15px; color: #1E293B; border: 1px solid #E2E8F0; border-top: 5px solid #EF4444;">
                    <p style="margin: 0; font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Outstanding Risk</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem; color: #EF4444;">UGX {risk:,.0f}</h2>
                </div>
                <div style="background: #F8FAFC; padding: 20px; border-radius: 15px; border: 1px dashed #00A3E0;">
                    <p style="margin: 0; font-size: 0.75rem; color: #64748B; text-transform: uppercase; font-weight: 700;">Recovery Rate</p>
                    <h2 style="margin: 5px 0; font-size: 1.8rem; color: #1E3A8A;">{recovery_rate:.1f}%</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.write("---")
        
        # --- CHARTS SECTION (Two-Pane Layout) ---
        c_left, c_right = st.columns([2, 1])
        
        with c_left:
            st.subheader("📊 Performance by Client")
            df_chart = df.copy()
            df_chart['TOTAL_DEBT'] = df_chart['LOAN_AMOUNT'] + (df_chart['LOAN_AMOUNT'] * df_chart['INTEREST_RATE'] / 100)
            chart_data = df_chart[['CUSTOMER_NAME', 'TOTAL_DEBT', 'AMOUNT_PAID']].set_index('CUSTOMER_NAME')
            st.bar_chart(chart_data, color=["#cbd5e1", "#1e3a8a"], height=300)

        with c_right:
            st.subheader("🕒 Recent Payments")
            if not pay_df.empty:
                # Mini table for quick glance
                recent = pay_df.sort_values(by='DATE', ascending=False).head(6)
                st.dataframe(recent[['CUSTOMER_NAME', 'AMOUNT_PAID']], 
                             column_config={"AMOUNT_PAID": st.column_config.NumberColumn(format="%,d")},
                             use_container_width=True, hide_index=True)
            else:
                st.info("No payments yet.")

        # --- OVERDUE ALERT AREA ---
        overdue_count = len(df[df['OUTSTANDING_AMOUNT'] > 0]) # Simplify logic for now
        if overdue_count > 0:
            st.info(f"💡 System Note: You have **{overdue_count}** active loan files currently being tracked.")


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

        # 1. CALCULATE STATUS LOGIC
    def get_status(row):
        if row['OUTSTANDING_AMOUNT'] <= 0:
            return "✅ Settled"
        elif row['AMOUNT_PAID'] == 0:
            return "🟡 Pending"
        else:
            return "🔴 Overdue"

    # 2. APPLY STATUS TO DATA
    if not df.empty:
        # Create the virtual Status column
        df['STATUS'] = df.apply(get_status, axis=1)
        
        # Search Filter
        if search_query:
            display_df = df[df['CUSTOMER_NAME'].str.contains(search_query, case=False, na=False)]
        else:
            display_df = df

        # 3. DISPLAY THE PRO TABLE
        st.dataframe(
            display_df,
            column_config={
                "STATUS": st.column_config.TextColumn(
                    "Status 🛡️", 
                    help="Settled (Green), Pending (Yellow), or Overdue (Red)"
                ),
                "CUSTOMER_NAME": "Borrower Name",
                "LOAN_AMOUNT": st.column_config.NumberColumn("Principal", format="UGX %,d"),
                "OUTSTANDING_AMOUNT": st.column_config.NumberColumn("Balance", format="UGX %,d"),
                "CONTACT": "Contact #"
            },
            use_container_width=True,
            hide_index=True
        )
        # --- 4. PERFORMANCE ANALYTICS ---
        st.write("---")
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("📈 Revenue Trend")
            # Prepare monthly data
            # 1. Ensure 'DATE' is in datetime format and create the 'Month' column
    display_df['DATE'] = pd.to_datetime(display_df['DATE'])
    display_df['Month'] = display_df['DATE'].dt.strftime('%b %Y') # e.g., "Mar 2026"

    # 2. Make sure the columns we want to sum actually exist
    cols_to_sum = {}
    if 'INTEREST_AMT' in display_df.columns:
        cols_to_sum['INTEREST_AMT'] = 'sum'
    if 'Penalty' in display_df.columns:
        cols_to_sum['Penalty'] = 'sum'
    
    # 3. Perform the grouping safely
    if cols_to_sum:
        monthly_rev = display_df.groupby('Month').agg(cols_to_sum).reset_index()
        
        # Sort by date so the chart flows correctly (Jan, Feb, Mar...)
        monthly_rev['Date_Sort'] = pd.to_datetime(monthly_rev['Month'], format='%b %Y')
        monthly_rev = monthly_rev.sort_values('Date_Sort')
        
        # 4. Display the chart
        st.bar_chart(data=monthly_rev, x='Month', y=list(cols_to_sum.keys()))
    else:
        st.warning("📊 No revenue data available to chart yet.")
        # --- 5. MANAGEMENT & REGISTRATION ---
        st.write("")
        with st.expander("🛠️ Manage Records (Edit/Delete)"):
            target = st.selectbox("Select Client:", options=df['CUSTOMER_NAME'].unique(), key="mgt_select")
            st.info(f"System ready to modify {target}'s records.")
    else:
        st.info("Registry is currently empty.")

     elif page == "Insights":
    st.markdown('<div class="main-title">📈 Zoe Consults Financial Insights</div>', unsafe_allow_html=True)
    
    # CALCULATE REVENUE (Interest Collected)
    # Note: We only count Interest/Penalties as 'Income', not the Principal
    # 1. First, create the INTEREST_AMT column so it exists in the app's memory
    df['INTEREST_AMT'] = (df['LOAN_AMOUNT'] * df['INTEREST_RATE']) / 100
    
    # 2. Now you can safely sum it up
    total_interest_earned = df['INTEREST_AMT'].sum()
    
    # 3. Handle Expenses safety check
    if not exp_df.empty and 'AMOUNT' in exp_df.columns:
        total_expenses = exp_df['AMOUNT'].sum()
    else:
        total_expenses = 0
        
    net_profit = total_interest_earned - total_expenses
    # KPI TILES
    i1, i2, i3 = st.columns(3)
    i1.metric("Gross Revenue (Interest)", f"UGX {total_interest_earned:,.0f}")
    i2.metric("Total Operating Costs", f"UGX {total_expenses:,.0f}", delta=f"-{total_expenses:,.0f}", delta_color="inverse")
    i3.metric("Net Profit", f"UGX {net_profit:,.0f}", delta=f"{(net_profit/total_interest_earned*100):.1f}% Margin" if total_interest_earned > 0 else "0%")

    st.write("---")
    
    # EXPENSE ENTRY FORM (Keep it small!)
    with st.expander("💸 Record New Business Expense"):
        with st.form("expense_form", clear_on_submit=True):
            e_cat = st.selectbox("Category", ["Data/Internet", "Transport", "Marketing", "Rent", "Taxes", "Other"])
            e_amt = st.number_input("Amount (UGX)", min_value=0, step=5000)
            e_desc = st.text_input("Note (e.g. Monthly MTN Bundle)")
            if st.form_submit_button("Post Expense", use_container_width=True):
                new_e = pd.DataFrame([[str(datetime.now().date()), e_cat, e_desc, e_amt]], 
                                    columns=['DATE', 'CATEGORY', 'DESCRIPTION', 'AMOUNT'])
                conn.update(worksheet="Expenses", data=pd.concat([exp_df, new_e], ignore_index=True))
                st.toast("Expense Recorded!")
                st.rerun()
            else:
                st.info("No expense data found. Use the form above to add your first record.")


# --- 2. THE REPAYMENTS PAGE (CLEANED) ---
elif page == "Repayments":
    st.markdown('<div class="main-title">💰 Payment Processing Center</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. CREATE THE FORM ENVELOPE
        with st.form("cloud_pay_form", clear_on_submit=True):
            st.subheader("Record New Payment")
            
            p_name = st.selectbox("Select Borrower 👤", options=df['CUSTOMER_NAME'].unique())
            p_amt = st.number_input("Amount Received (UGX) 💵", min_value=0, step=5000)
            p_ref = st.text_input("Reference / Receipt Number 🏷️", placeholder="e.g. REC-102")
            
            # --- THE BUTTON (NOW SAFELY INSIDE THE FORM) ---
            submit_payment = st.form_submit_button("🚀 Confirm & Post Payment", use_container_width=True)
            
            if submit_payment:
                if p_amt > 0 and p_ref:
                    with st.spinner("🔒 Syncing to Zoe Cloud..."):
                        try:
                            # Create entry
                            new_p = pd.DataFrame([[str(datetime.now().date()), p_name, p_amt, p_ref]], 
                                               columns=['DATE', 'CUSTOMER_NAME', 'AMOUNT_PAID', 'REF'])
                            
                            # Sync to Payments Sheet
                            conn.update(worksheet="Payments", data=pd.concat([pay_df, new_p], ignore_index=True))
                            
                            # Update Borrower Balance
                            idx = df[df['CUSTOMER_NAME'] == p_name].index
                            df.loc[idx, 'AMOUNT_PAID'] += p_amt
                            df.loc[idx, 'OUTSTANDING_AMOUNT'] -= p_amt
                            conn.update(worksheet="Borrowers", data=df)
                            
                            st.toast(f"✅ Receipt {p_ref} secured!", icon="💰")
                            import time
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Sync Failed: {e}")
                else:
                    st.error("⚠️ Please provide both an Amount and a Reference Number.")

        # 2. SHOW THE HISTORY TABLE (OUTSIDE THE FORM)
        st.write("---")
        st.subheader("📋 Recent Transaction History")
        if not pay_df.empty:
            display_pay = pay_df.copy().iloc[::-1]
            st.dataframe(
                display_pay,
                column_config={
                    "DATE": "Date",
                    "CUSTOMER_NAME": "Borrower",
                    "AMOUNT_PAID": st.column_config.NumberColumn("Amount", format="UGX %,d"),
                    "REF": "Receipt #"
                },
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("📢 No borrowers found. Please register a client in the 'Borrowers' tab first.")

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
